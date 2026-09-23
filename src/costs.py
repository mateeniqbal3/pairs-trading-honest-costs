"""Transaction cost model: half bid-ask spread, slippage, commission, short borrow.

Parameter values are fixed in DECISIONS.md ADR-004 and the mechanics in ADR-011.
Costs are charged against an execution log and a record of short exposure; they
never influence which trades happen, so gross and net describe identical trades.
Dividends on the short leg are not a cost here: gross P&L already pays them
through dividend-adjusted prices (ADR-010), and charging them again would
double-count.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import pandas as pd

from src import config

BPS = 1e-4
TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class CostModel:
    half_spread_bps: float = config.HALF_SPREAD_BPS
    slippage_bps: float = config.SLIPPAGE_BPS
    commission_per_share: float = config.COMMISSION_PER_SHARE
    commission_min: float = config.COMMISSION_MIN
    borrow_rate_annual: float = config.BORROW_RATE_ANNUAL

    def scaled(self, multiplier: float) -> CostModel:
        """Every component, including the commission minimum, times ``multiplier``."""
        if multiplier < 0:
            raise ValueError("multiplier must be non-negative")
        return CostModel(**{f.name: getattr(self, f.name) * multiplier for f in fields(self)})


def order_costs(executions: pd.DataFrame, model: CostModel) -> pd.DataFrame:
    """Per-execution costs: spread and slippage on notional, commission per order."""
    out = executions.copy()
    out["spread_cost"] = out["notional"] * model.half_spread_bps * BPS
    out["slippage_cost"] = out["notional"] * model.slippage_bps * BPS
    per_share = out["shares"].abs() * model.commission_per_share
    out["commission"] = per_share.clip(lower=model.commission_min)
    out["order_cost"] = out["spread_cost"] + out["slippage_cost"] + out["commission"]
    return out


def borrow_costs(short_value: pd.Series, model: CostModel) -> pd.Series:
    """Borrow charged each day on the short value held overnight from the previous close."""
    prior = short_value.shift(1, fill_value=0.0)
    return (prior * model.borrow_rate_annual / TRADING_DAYS_PER_YEAR).rename("borrow_cost")


@dataclass(frozen=True)
class NetResult:
    daily_pnl: pd.Series
    trade_pnl: pd.Series  # net P&L per trade_id
    breakdown: dict[str, float]  # total cost by component


def apply_costs(
    gross_daily_pnl: pd.Series,
    gross_trade_pnl: pd.Series,
    trades: pd.DataFrame,
    executions: pd.DataFrame,
    short_value: pd.Series,
    model: CostModel,
) -> NetResult:
    """Subtract costs from gross P&L, per day and per trade. Trades are not altered."""
    orders = order_costs(executions, model)
    borrow = borrow_costs(short_value, model)

    daily_orders = orders.groupby("date")["order_cost"].sum().reindex(
        gross_daily_pnl.index, fill_value=0.0
    )
    net_daily = gross_daily_pnl - daily_orders - borrow

    dates = gross_daily_pnl.index
    trade_costs = orders.groupby("trade_id")["order_cost"].sum()
    net_trade = {}
    for tr in trades.itertuples(index=False):
        i0, i1 = dates.get_loc(tr.entry_date), dates.get_loc(tr.exit_date)
        trade_borrow = borrow.iloc[i0 + 1 : i1 + 1].sum()  # nights held: after entry, up to exit
        net_trade[tr.trade_id] = (
            gross_trade_pnl[tr.trade_id] - trade_costs.get(tr.trade_id, 0.0) - trade_borrow
        )

    breakdown = {
        "spread": float(orders["spread_cost"].sum()),
        "slippage": float(orders["slippage_cost"].sum()),
        "commission": float(orders["commission"].sum()),
        "borrow": float(borrow.sum()),
    }
    breakdown["total"] = sum(breakdown.values())
    return NetResult(
        daily_pnl=net_daily.rename("pnl"),
        trade_pnl=pd.Series(net_trade, name="pnl"),
        breakdown=breakdown,
    )
