"""Phase 5: net-of-costs result, charged on the frozen gross trade log.

Usage:  python scripts/run_backtest_net.py

Reads the 20 trades in docs/results_gross.json (hash-checked against the value
frozen in DECISIONS.md ADR-010). No signal or trade-generation code is called.
Rebuilds gross accounts from the trade log, verifies they match every frozen
gross number, then applies the ADR-004 cost model (mechanics in ADR-011) at the
pre-registered multipliers. Writes docs/results_net.json, docs/results_net.md,
and docs/results.md.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.backtest import compute_metrics, rebuild_from_trades  # noqa: E402
from src.costs import CostModel, apply_costs  # noqa: E402
from src.data import align_prices, file_sha256, load_raw, slice_period  # noqa: E402

FROZEN_GROSS_SHA256 = "1acbfd35e8c899173a6e4cb355942cc5485bf01d5ac5d0bfc419d429746df853"
DOCS = config.PROJECT_ROOT / "docs"
GROSS_JSON = DOCS / "results_gross.json"


def load_frozen_gross() -> dict:
    digest = hashlib.sha256(GROSS_JSON.read_bytes()).hexdigest()
    if digest != FROZEN_GROSS_SHA256:
        raise RuntimeError(f"results_gross.json hash {digest} != frozen {FROZEN_GROSS_SHA256}")
    return json.loads(GROSS_JSON.read_text(encoding="utf-8"))


def check_matches_frozen(rebuilt, trades, gross, metrics) -> None:
    frozen_pnl = trades.set_index("trade_id")["pnl"]
    diff = (rebuilt.trade_pnl.sort_index() - frozen_pnl.sort_index()).abs().max()
    if diff > 1e-6:
        raise RuntimeError(f"rebuilt trade P&L differs from frozen by {diff}")
    for key, frozen in gross["metrics"].items():
        if key in metrics and not math.isclose(metrics[key], frozen, rel_tol=1e-9, abs_tol=1e-9):
            raise RuntimeError(f"rebuilt gross {key} = {metrics[key]} != frozen {frozen}")


def money(v: float) -> str:
    return f"-${-v:,.2f}" if v < 0 else f"+${v:,.2f}"


def main() -> None:
    gross = load_frozen_gross()
    sha = file_sha256(config.RAW_PRICES_PATH)
    if sha != gross["raw_file_sha256"]:
        raise RuntimeError("raw price file does not match the snapshot used for the gross run")
    y, x = gross["pair"]["y"], gross["pair"]["x"]
    capital = gross["parameters"]["capital"]
    start, end = gross["parameters"]["trading_period"]

    trades = pd.DataFrame(gross["trades"])
    for col in ("entry_date", "exit_date"):
        trades[col] = pd.to_datetime(trades[col])

    raw = load_raw(config.RAW_PRICES_PATH)
    adj_full, _ = align_prices(raw["Adj Close"], config.UNIVERSE)
    adj = slice_period(adj_full, start, end)
    close = slice_period(raw["Close"].loc[adj_full.index, list(config.UNIVERSE)], start, end)

    rebuilt = rebuild_from_trades(trades, adj, close, y, x)
    held_days = float((rebuilt.short_value > 0).mean())

    def metrics_for(daily_pnl, trade_pnl):
        t = trades.assign(pnl=trades["trade_id"].map(trade_pnl))
        m = compute_metrics(daily_pnl, t, rebuilt.executions, capital)
        m["time_in_market"] = held_days
        m["forced_closes"] = int(trades["forced_close"].sum())
        return m

    gross_metrics = metrics_for(rebuilt.daily_pnl, rebuilt.trade_pnl)
    check_matches_frozen(rebuilt, trades, gross, gross_metrics)

    base = CostModel()
    runs = {}
    for mult in config.COST_MULTIPLIERS:
        net = apply_costs(rebuilt.daily_pnl, rebuilt.trade_pnl, trades, rebuilt.executions,
                          rebuilt.short_value, base.scaled(mult))
        runs[mult] = {"metrics": metrics_for(net.daily_pnl, net.trade_pnl),
                      "breakdown": net.breakdown, "trade_pnl": net.trade_pnl}
    zero = runs[0.0]["metrics"]
    if any(not math.isclose(zero[k], gross_metrics[k], rel_tol=1e-12, abs_tol=1e-12)
           for k in gross_metrics if isinstance(gross_metrics[k], float)
           and not math.isnan(gross_metrics[k])):
        raise RuntimeError("0x cost run does not reproduce the frozen gross result")

    head = runs[1.0]
    g, n, b = gross_metrics, head["metrics"], head["breakdown"]
    n_trades = int(g["n_trades"])
    traded_notional = float(rebuilt.executions["notional"].sum())
    breakeven = g["total_pnl"] / b["total"] if b["total"] > 0 else float("inf")
    per_trade = {k: v / n_trades for k, v in b.items()}

    payload = {
        "description": "Net-of-costs result on the frozen gross trade log (ADR-010, ADR-011).",
        "gross_results_sha256": FROZEN_GROSS_SHA256,
        "raw_file_sha256": sha,
        "cost_model": vars(base),
        "gross_metrics": gross_metrics,
        "net_metrics": n,
        "cost_breakdown": b,
        "dividends_within_gross": rebuilt.dividends,
        "traded_notional": traded_notional,
        "breakeven_cost_multiplier": breakeven,
        "sensitivity": {str(k): {"metrics": v["metrics"], "total_cost": v["breakdown"]["total"]}
                        for k, v in runs.items()},
        "trades": [{"trade_id": int(t.trade_id), "gross_pnl": float(t.pnl),
                    "net_pnl": float(head["trade_pnl"][t.trade_id])}
                   for t in trades.itertuples()],
    }
    net_json = DOCS / "results_net.json"
    net_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    net_sha = hashlib.sha256(net_json.read_bytes()).hexdigest()

    def row(label, key, fmt):
        return f"| {label} | {fmt(g[key])} | {fmt(n[key])} |"

    pct = "{:.2%}".format
    main_table = "\n".join([
        "| Metric | Gross of costs | Net of costs |",
        "|---|---:|---:|",
        row("Total P&L", "total_pnl", money),
        row("Total return (on $100,000)", "total_return", pct),
        row("Annualized return", "annualized_return", pct),
        row("Annualized volatility", "annualized_volatility", pct),
        row("Sharpe ratio", "sharpe_ratio", "{:.2f}".format),
        row("Max drawdown", "max_drawdown", pct),
        row("Win rate", "win_rate", "{:.1%}".format),
        row("Average P&L per trade", "avg_trade_pnl", money),
        row("Number of trades", "n_trades", "{:d}".format),
    ])
    sens = "\n".join(
        f"| {k:g}× | ${v['breakdown']['total']:,.2f} | {money(v['metrics']['total_pnl'])} | "
        f"{v['metrics']['total_return']:.2%} | {v['metrics']['sharpe_ratio']:.2f} | "
        f"{v['metrics']['max_drawdown']:.2%} | {v['metrics']['win_rate']:.1%} |"
        for k, v in runs.items()
    )
    trade_rows = "\n".join(
        f"| {t.trade_id} | {t.entry_date.date()} | {t.exit_date.date()} | {money(t.pnl)} | "
        f"{money(head['trade_pnl'][t.trade_id] - t.pnl)} | {money(head['trade_pnl'][t.trade_id])} |"
        for t in trades.itertuples()
    )
    mechanism = f"""Each round trip trades about ${traded_notional / n_trades:,.0f} of notional
(entry and exit, both legs), so the 5 bps of half-spread plus slippage costs about
${(per_trade["spread"] + per_trade["slippage"]):,.2f} per trade. Commissions add
${per_trade["commission"]:,.2f} and short borrow ${per_trade["borrow"]:,.2f}, for an
average of **${per_trade["total"]:,.2f} per trade**. That compares with an average
gross P&L of **{money(g["avg_trade_pnl"])} per trade**, which is
{g["avg_trade_pnl"] / (traded_notional / n_trades) * 1e4:.1f} bps of the notional each
trade turns over. Over {n_trades} trades ({g["turnover_per_year"]:.1f}× capital traded
per year), costs total ${b["total"]:,.2f}, equal to
**{b["total"] / g["total_pnl"]:.0%} of the gross P&L**. Net P&L would reach zero at
**{breakeven:.2f}× the base-case costs**."""

    note = """> EOG/FANG was the best of 28 searched pairs and does not survive Holm
> correction (p = 0.142); cointegration is not detected in the trading period
> (Engle-Granger p = 0.223). See DECISIONS.md ADR-008."""

    (DOCS / "results_net.md").write_text(f"""# Net-of-Costs Results — {y}/{x}, 2021–2025

> Generated by `scripts/run_backtest_net.py`. Do not edit by hand. Costs are charged
> on the **same 20 trades** frozen in `results_gross.json` (SHA-256
> `{FROZEN_GROSS_SHA256}`); no trades were regenerated. Rebuilt gross numbers were
> checked against the frozen values before costs were applied.
> `results_net.json` SHA-256: `{net_sha}`.

{note}

## Gross vs. net (base-case costs, ADR-004)

{main_table}

## Cost breakdown (base case)

| Component | Assumption | Total | Per trade |
|---|---|---:|---:|
| Half bid-ask spread | 2 bps of traded notional | ${b["spread"]:,.2f} | ${per_trade["spread"]:,.2f} |
| Slippage | 3 bps of traded notional | ${b["slippage"]:,.2f} | ${per_trade["slippage"]:,.2f} |
| Commission | $0.005/share, $1 minimum per order | ${b["commission"]:,.2f} | ${per_trade["commission"]:,.2f} |
| Short borrow | 0.30%/year on short market value | ${b["borrow"]:,.2f} | ${per_trade["borrow"]:,.2f} |
| **Total** | | **${b["total"]:,.2f}** | **${per_trade["total"]:,.2f}** |

Traded notional over the period: ${traded_notional:,.0f}. Regulatory fees are not
modeled (ADR-004).

**Dividends (already inside gross P&L, not charged again):** gross P&L uses
dividend-adjusted closes, so dividends are already included: {money(rebuilt.dividends["short_leg"])}
paid on short legs and {money(rebuilt.dividends["long_leg"])} received on long legs.

## Why the numbers differ

{mechanism}

## Cost sensitivity (pre-registered multipliers)

| Cost multiplier | Total costs | Net P&L | Net return | Sharpe | Max drawdown | Win rate |
|---:|---:|---:|---:|---:|---:|---:|
{sens}

0× reproduces the frozen gross result exactly. 1× is the headline net figure.

## Per-trade gross vs. net (base case)

| # | Entry | Exit | Gross P&L | Costs | Net P&L |
|---:|---|---|---:|---:|---:|
{trade_rows}
""", encoding="utf-8")

    (DOCS / "results.md").write_text(f"""# Results — Gross vs. Net of Costs

> Generated by `scripts/run_backtest_net.py`. Gross column: frozen before any cost
> code existed (DECISIONS.md ADR-010). Net column: the same 20 trades with the
> pre-registered cost model (ADR-004, ADR-011). Details: [`results_gross.md`](results_gross.md),
> [`results_net.md`](results_net.md).

{note}

EOG/FANG, trading period {start} to {end}, $100,000 gross notional per trade.

{main_table}

## Why the numbers differ (specific mechanism)

{mechanism}
""", encoding="utf-8")

    print((DOCS / "results_net.md").read_text(encoding="utf-8"))
    print(f"results_net.json SHA-256: {net_sha}")


if __name__ == "__main__":
    main()
