"""Generate the figures used in paper/writeup.md and the README.

Reads only the committed, hash-verified result files
(docs/results_gross.json and docs/results_net.json). It does not download
data, rerun the backtest, or change any result.

Usage (from the repository root):
    python paper/make_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

gross = json.loads((ROOT / "docs" / "results_gross.json").read_text())
net = json.loads((ROOT / "docs" / "results_net.json").read_text())

GROSS_C, NET_C, COST_C = "#4C72B0", "#C44E52", "#8C8C8C"
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    }
)

n_trades = gross["metrics"]["n_trades"]
avg_gross = gross["metrics"]["avg_trade_pnl"]
cb = net["cost_breakdown"]
per_trade = {k: cb[k] / n_trades for k in ("spread", "slippage", "commission", "borrow")}
avg_cost = cb["total"] / n_trades
breakeven = net["breakeven_cost_multiplier"]
mults = sorted(net["sensitivity"], key=float)
sens_x = [float(m) for m in mults]
sens_y = [net["sensitivity"][m]["metrics"]["total_pnl"] for m in mults]


def per_trade_economics(ax):
    labels = {
        "spread": "Half-spread (2 bps)",
        "slippage": "Slippage (3 bps)",
        "commission": "Commission",
        "borrow": "Short borrow",
    }
    shades = ["#6E6E6E", "#9A9A9A", "#BDBDBD", "#D9D9D9"]
    ax.bar(0, avg_gross, color=GROSS_C, width=0.6)
    ax.text(0, avg_gross + 4, f"${avg_gross:,.0f}", ha="center", va="bottom", fontweight="bold")
    bottom = 0.0
    for (key, value), shade in zip(per_trade.items(), shades):
        ax.bar(1, value, bottom=bottom, color=shade, width=0.6, edgecolor="white", label=labels[key])
        bottom += value
    ax.text(1, avg_cost + 4, f"${avg_cost:,.0f}", ha="center", va="bottom", fontweight="bold")
    ax.set_xticks([0, 1], ["Average gross\ngain per trade", "Average cost\nper trade"])
    ax.set_ylabel("US dollars per round trip")
    ax.set_ylim(0, avg_gross * 1.25)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.set_title(f"Costs take {cb['total'] / gross['metrics']['total_pnl']:.0%} of the gross P&L")
    ax.grid(axis="x", visible=False)


def sensitivity(ax):
    colors = [NET_C if y < 0 else GROSS_C for y in sens_y]
    ax.bar(sens_x, sens_y, width=0.35, color=colors)
    for x, y in zip(sens_x, sens_y):
        ax.text(x, y + (120 if y >= 0 else -120), f"{y:+,.0f}", ha="center",
                va="bottom" if y >= 0 else "top", fontsize=8)
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(breakeven, color=COST_C, ls="--", lw=1)
    ax.text(breakeven + 0.06, max(sens_y) * 0.85, f"break-even\n{breakeven:.2f}x", color="#555555", fontsize=8)
    ax.set_xticks(sens_x, [f"{x:g}x" for x in sens_x])
    ax.set_xlabel("Multiple of pre-registered base-case costs (0x = gross)")
    ax.set_ylabel("Net P&L on $100,000, 2021-2025 (USD)")
    ax.set_ylim(min(sens_y) * 1.25, max(sens_y) * 1.25)
    ax.set_title("Net P&L versus cost assumption")
    ax.grid(axis="x", visible=False)


def cumulative(ax):
    trades = pd.DataFrame(gross["trades"])[["trade_id", "exit_date", "pnl"]]
    trades = trades.merge(pd.DataFrame(net["trades"]), on="trade_id")
    trades["exit_date"] = pd.to_datetime(trades["exit_date"])
    start = pd.Timestamp("2021-01-04")
    x = [start, *trades["exit_date"]]
    ax.step(x, [0, *trades["gross_pnl"].cumsum()], where="post", color=GROSS_C, lw=1.8, label="Gross of costs")
    ax.step(x, [0, *trades["net_pnl"].cumsum()], where="post", color=NET_C, lw=1.8, label="Net of costs (1x)")
    end = trades["exit_date"].iloc[-1]
    for series, color in (("gross_pnl", GROSS_C), ("net_pnl", NET_C)):
        final = trades[series].sum()
        ax.plot(end, final, "o", color=color, ms=5)
        ax.annotate(f"{final:+,.0f}", (end, final), xytext=(6, 0), textcoords="offset points",
                    va="center", color=color, fontsize=9, fontweight="bold")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Cumulative realized P&L (USD)")
    ax.set_title("EOG/FANG, cumulative P&L by trade exit date, 2021-2025")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(frameon=False, loc="upper left")


# Figure 1: per-trade economics (the mechanism).
fig, ax = plt.subplots(figsize=(5.2, 3.8))
per_trade_economics(ax)
fig.savefig(OUT / "fig1_per_trade_economics.png")
plt.close(fig)

# Figure 2: cost sensitivity.
fig, ax = plt.subplots(figsize=(5.8, 3.8))
sensitivity(ax)
fig.savefig(OUT / "fig2_cost_sensitivity.png")
plt.close(fig)

# Figure 3: cumulative realized P&L, gross vs net.
fig, ax = plt.subplots(figsize=(6.5, 3.6))
cumulative(ax)
fig.savefig(OUT / "fig3_cumulative_pnl.png")
plt.close(fig)

# README hero: figures 1 and 2 side by side.
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
per_trade_economics(axes[0])
sensitivity(axes[1])
fig.suptitle(
    "Pairs trading EOG/FANG, 2021-2025: a small gross edge, mostly consumed by realistic costs",
    fontweight="bold",
)
fig.tight_layout()
fig.savefig(OUT / "readme_hero.png")
plt.close(fig)

print(f"Wrote figures to {OUT.relative_to(ROOT)}")
