"""Gross backtest: turns target positions into executions, trades, and daily P&L.

Accounting rules are fixed in DECISIONS.md ADR-006 and ADR-010. This module
contains no cost logic: the execution log it produces is the single source of
truth for trades, and costs (src/costs.py, Phase 5) are charged against that
same log, so gross and net results always describe identical trades
(ARCHITECTURE.md section 3).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BacktestResult:
    daily: pd.DataFrame  # per day: executed position, P&L, equity, leg values
    trades: pd.DataFrame  # one row per round trip
    executions: pd.DataFrame  # one row per leg per order (entries and exits)


@dataclass
class _OpenTrade:
    trade_id: int
    direction: int
    entry_date: pd.Timestamp
    entry_index: int
    shares: dict[str, int]  # signed: + long, - short
    invested: dict[str, float]  # shares * unadjusted close at entry (signed)
    adj_entry: dict[str, float]
    pnl: float = 0.0


def executed_positions(target: pd.Series) -> pd.Series:
    """Position held after the close of each day: yesterday's target (ADR-006).

    The final day is forced flat, so an open trade is closed at the last close
    and no new trade is opened on it (ADR-010).
    """
    held = target.shift(1).fillna(0).astype(int)
    if len(held):
        held.iloc[-1] = 0
    return held.rename("position")


def _leg_values(trade: _OpenTrade, adj_row: pd.Series) -> dict[str, float]:
    return {t: trade.invested[t] * adj_row[t] / trade.adj_entry[t] for t in trade.invested}


def run_backtest(
    target: pd.Series,
    adj_close: pd.DataFrame,
    close: pd.DataFrame,
    y: str,
    x: str,
    beta: float,
    capital: float = 100_000.0,
) -> BacktestResult:
    """Run the gross backtest.

    ``target`` is the target position decided at each close (+1 long spread =
    long y / short x, -1 the reverse, 0 flat). ``adj_close`` drives P&L;
    ``close`` (unadjusted) sets share counts and execution notional.
    """
    dates = target.index
    for frame, name in ((adj_close, "adj_close"), (close, "close")):
        if not frame.index.equals(dates):
            raise ValueError(f"{name} index must match target index")
        if frame[[y, x]].isna().any().any():
            raise ValueError(f"{name} contains NaN")
    if not set(np.unique(target)) <= {-1, 0, 1}:
        raise ValueError("target positions must be -1, 0, or +1")
    if beta == 0:
        raise ValueError("beta must be non-zero")

    weight_y = 1.0 / (1.0 + abs(beta))
    weight_x = abs(beta) / (1.0 + abs(beta))
    x_side = -int(np.sign(beta))  # with beta > 0, the x leg is opposite to the y leg

    held = executed_positions(target)
    unforced = target.shift(1).fillna(0).astype(int)  # what the signal alone would hold
    daily_rows, trades, executions = [], [], []
    open_trade: _OpenTrade | None = None
    next_id = 1

    def execute(date, trade_id, kind, shares_by_ticker):
        for ticker, shares in shares_by_ticker.items():
            price = float(close.at[date, ticker])
            executions.append({
                "date": date, "trade_id": trade_id, "kind": kind, "ticker": ticker,
                "shares": shares, "price": price, "notional": abs(shares) * price,
            })

    for i, date in enumerate(dates):
        adj_row = adj_close.loc[date]
        pnl = 0.0
        if open_trade is not None and i > 0:
            prev = _leg_values(open_trade, adj_close.iloc[i - 1])
            now = _leg_values(open_trade, adj_row)
            pnl = sum(now[t] - prev[t] for t in now)
            open_trade.pnl += pnl

        wanted = int(held.iloc[i])
        current = open_trade.direction if open_trade is not None else 0
        if wanted != current:
            if open_trade is not None:  # exit at today's close
                execute(date, open_trade.trade_id, "exit",
                        {t: -s for t, s in open_trade.shares.items()})
                trades.append({
                    "trade_id": open_trade.trade_id,
                    "direction": open_trade.direction,
                    "entry_date": open_trade.entry_date,
                    "exit_date": date,
                    "holding_days": i - open_trade.entry_index,
                    f"shares_{y}": open_trade.shares[y],
                    f"shares_{x}": open_trade.shares[x],
                    "entry_notional": sum(abs(v) for v in open_trade.invested.values()),
                    "pnl": open_trade.pnl,
                    # closed only because the trading period ended (ADR-010)
                    "forced_close": i == len(dates) - 1 and int(unforced.iloc[i]) != 0,
                })
                open_trade = None
            if wanted != 0:  # enter at today's close
                shares = {
                    y: wanted * math.floor(capital * weight_y / close.at[date, y]),
                    x: wanted * x_side * math.floor(capital * weight_x / close.at[date, x]),
                }
                if 0 in shares.values():
                    raise ValueError(f"capital too small to buy one share on {date.date()}")
                open_trade = _OpenTrade(
                    trade_id=next_id, direction=wanted, entry_date=date, entry_index=i,
                    shares=shares,
                    invested={t: s * float(close.at[date, t]) for t, s in shares.items()},
                    adj_entry={t: float(adj_row[t]) for t in shares},
                )
                execute(date, next_id, "entry", shares)
                next_id += 1

        values = _leg_values(open_trade, adj_row) if open_trade is not None else {}
        daily_rows.append({
            "date": date,
            "position": open_trade.direction if open_trade is not None else 0,
            "pnl": pnl,
            "long_value": sum(v for v in values.values() if v > 0),
            "short_value": -sum(v for v in values.values() if v < 0),
        })

    daily = pd.DataFrame(daily_rows).set_index("date")
    daily["return"] = daily["pnl"] / capital
    daily["equity"] = capital + daily["pnl"].cumsum()
    trade_cols = ["trade_id", "direction", "entry_date", "exit_date", "holding_days",
                  f"shares_{y}", f"shares_{x}", "entry_notional", "pnl", "forced_close"]
    exec_cols = ["date", "trade_id", "kind", "ticker", "shares", "price", "notional"]
    return BacktestResult(
        daily=daily,
        trades=pd.DataFrame(trades, columns=trade_cols),
        executions=pd.DataFrame(executions, columns=exec_cols),
    )


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough fall as a (negative) fraction of the running peak."""
    peak = equity.cummax()
    return float(((equity - peak) / peak).min())


def compute_metrics(
    daily_pnl: pd.Series, trades: pd.DataFrame, executions: pd.DataFrame,
    capital: float = 100_000.0,
) -> dict[str, float]:
    """Performance metrics as defined in ADR-010.

    Takes P&L and trade P&L explicitly so the same function serves the gross
    and (in Phase 5) the net run.
    """
    returns = daily_pnl / capital
    n_days = len(returns)
    years = n_days / TRADING_DAYS_PER_YEAR
    std = returns.std(ddof=1)
    equity = capital + daily_pnl.cumsum()
    n_trades = len(trades)
    return {
        "total_pnl": float(daily_pnl.sum()),
        "total_return": float(daily_pnl.sum() / capital),
        "annualized_return": float(returns.mean() * TRADING_DAYS_PER_YEAR),
        "annualized_volatility": float(std * math.sqrt(TRADING_DAYS_PER_YEAR)),
        "sharpe_ratio": float(returns.mean() / std * math.sqrt(TRADING_DAYS_PER_YEAR))
        if std > 0 else float("nan"),
        "max_drawdown": max_drawdown(equity),
        "n_trades": n_trades,
        "win_rate": float((trades["pnl"] > 0).mean()) if n_trades else float("nan"),
        "avg_trade_pnl": float(trades["pnl"].mean()) if n_trades else float("nan"),
        "avg_holding_days": float(trades["holding_days"].mean()) if n_trades else float("nan"),
        "turnover_per_year": float(executions["notional"].sum() / capital / years),
        "n_days": n_days,
    }


@dataclass(frozen=True)
class RebuiltAccounts:
    daily_pnl: pd.Series  # gross P&L per day, same formula as run_backtest
    trade_pnl: pd.Series  # gross P&L per trade_id
    executions: pd.DataFrame  # same columns as BacktestResult.executions
    short_value: pd.Series  # unadjusted market value of short legs held overnight after each close
    dividends: dict[str, float]  # dividend component of gross P&L: {"long_leg": +, "short_leg": -}


def rebuild_from_trades(
    trades: pd.DataFrame, adj_close: pd.DataFrame, close: pd.DataFrame, y: str, x: str
) -> RebuiltAccounts:
    """Recompute accounts from a recorded trade list, without any trading logic.

    Used by the net-of-costs run so that costs are charged on exactly the trades
    that were frozen in the gross run (ADR-010, ADR-011). Uses the same leg-value
    formula as ``run_backtest``: ``shares * Close_entry * AdjClose_t / AdjClose_entry``.
    """
    dates = adj_close.index
    daily = np.zeros(len(dates))
    short_value = np.zeros(len(dates))
    trade_pnl, executions = {}, []
    dividends = {"long_leg": 0.0, "short_leg": 0.0}

    for tr in trades.itertuples(index=False):
        i0, i1 = dates.get_loc(tr.entry_date), dates.get_loc(tr.exit_date)
        if i1 <= i0:
            raise ValueError(f"trade {tr.trade_id} exits before it enters")
        pnl = 0.0
        for ticker in (y, x):
            shares = int(getattr(tr, f"shares_{ticker}"))
            entry_close = float(close.at[tr.entry_date, ticker])
            invested = shares * entry_close
            adj = adj_close[ticker].to_numpy()[i0 : i1 + 1]
            value = invested * adj / adj[0]
            leg_daily = np.diff(value)
            daily[i0 + 1 : i1 + 1] += leg_daily
            pnl += leg_daily.sum()

            price_only = shares * (float(close.at[tr.exit_date, ticker]) - entry_close)
            leg = "long_leg" if shares > 0 else "short_leg"
            dividends[leg] += leg_daily.sum() - price_only
            if shares < 0:
                short_value[i0:i1] += -shares * close[ticker].to_numpy()[i0:i1]

            for date, kind, qty in ((tr.entry_date, "entry", shares), (tr.exit_date, "exit", -shares)):
                price = float(close.at[date, ticker])
                executions.append({
                    "date": date, "trade_id": tr.trade_id, "kind": kind, "ticker": ticker,
                    "shares": qty, "price": price, "notional": abs(qty) * price,
                })
        trade_pnl[tr.trade_id] = pnl

    exec_cols = ["date", "trade_id", "kind", "ticker", "shares", "price", "notional"]
    execs = pd.DataFrame(executions, columns=exec_cols).sort_values(
        ["date", "trade_id", "kind"], kind="mergesort", ignore_index=True
    )
    return RebuiltAccounts(
        daily_pnl=pd.Series(daily, index=dates, name="pnl"),
        trade_pnl=pd.Series(trade_pnl, name="pnl"),
        executions=execs,
        short_value=pd.Series(short_value, index=dates, name="short_value"),
        dividends=dividends,
    )
