# Pairs Trading with Honest Cost Modeling

[![CI](https://github.com/mateeniqbal3/pairs-trading-honest-costs/actions/workflows/ci.yml/badge.svg)](https://github.com/mateeniqbal3/pairs-trading-honest-costs/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Research question:** How does incorporating realistic transaction
> costs affect the observed performance of a pairs-trading strategy? This
> project backtests a single pair selected by a cointegration test, reports gross and
> net-of-cost performance side by side from the same trades, and explains
> the mechanism behind any difference.

**Finding:** Gross of costs, EOG/FANG earned +$3,253 (+3.25% over five years,
Sharpe 0.08). Net of the pre-registered costs it earned +$715 (+0.72%,
Sharpe 0.02). Costs of $2,538 took 78% of the gross P&L. The mechanism is
that each round trip turns over about $202,000 of notional (entry and
exit, both legs). At 5 bps per side for half-spread plus slippage, that
alone costs about $101 per trade; with commissions ($9) and short borrow
($17), the total is $127 per trade, against an average gross gain of
only $163 per trade (8.1 bps of the notional traded). Net P&L reaches
zero at 1.28× the base-case costs, and is negative at 2×. Neither the
gross nor the net return is statistically distinguishable from zero
(approximate t-statistics 0.18 and 0.04), and the pair itself was not
statistically validated (ADR-008).

> **Multiple-testing disclosure: no pair survives correction.** All 28
> pairs in the candidate universe were tested for cointegration over the
> 2016–2020 formation period. The selected pair, EOG/FANG, had the lowest
> raw Engle-Granger p-value (0.0051), but after Holm correction for 28
> tests its p-value is 0.142, and no pair is significant at 5%. The
> project continues with the best raw p-value pair for the out-of-sample
> test, as its pre-registered rules required
> ([`DECISIONS.md`](DECISIONS.md) ADR-008). The same test on the
> 2021–2025 trading period does not detect cointegration either
> (p = 0.223; [`docs/stability_check.md`](docs/stability_check.md)). Any
> backtest result should be read as a test of a pair *found by searching*,
> not of a statistically established relationship.

---

## Problem Statement

**Hypothesis:** Two assets with a plausible economic link — here, two
US shale oil producers with large Permian Basin operations and exposure
to the same crude price, basin differentials, and service-cost cycle —
should have prices that drift apart in the short term but revert toward a
stable long-run relationship. If that relationship is real, a spread
between them that moves too far
from its historical mean should tend to move back, and a signal that buys
the relatively cheap asset and sells the relatively expensive one should
have some predictive value.

**Pair tested:** EOG Resources (EOG) / Diamondback Energy (FANG),
selected from 8 US oil and gas producers by a pre-registered rule (lowest
formation-period Engle-Granger p-value). See [`DECISIONS.md`](DECISIONS.md)
ADR-001, ADR-002, and ADR-008.

## Methodology

**Cointegration testing.** Engle-Granger two-step test on log adjusted
closes, 2016–2020 formation period, for all 28 pairs of
`XOM, CVX, COP, EOG, OXY, DVN, APA, FANG`. EOG/FANG: statistic −4.105
(5% critical value −3.341), raw p = 0.0051, Holm p = 0.142, hedge ratio
beta = 0.742. The hedge ratio is estimated on the formation period only
and held fixed for trading. Full table:
[`docs/pair_selection.md`](docs/pair_selection.md).

**Data.** Daily adjusted and unadjusted closes from yfinance,
2016-01-04 to 2025-12-31, for the 8 tickers above. Only dates on which
all 8 trade are kept (none were dropped), with no filling or repair. The
SHA-256 of the raw snapshot is recorded in
[`data/dataset_manifest.json`](data/dataset_manifest.json)
([`DECISIONS.md`](DECISIONS.md) ADR-007).

**Strategy and backtest.** The spread is
`log(EOG) − 0.742 × log(FANG) − 1.006`, with coefficients from the formation
period. Its z-score uses a trailing 60-day window. The strategy enters
short-spread at z ≥ +2 and long-spread at z ≤ −2, and exits when z comes
back inside ±0.5 (or overshoots through it). There is no stop-loss. Each
trade uses $100,000 of gross notional, split between the legs by the
hedge ratio, in whole shares, and is not compounded. Orders are executed
at the close of the day after the signal. P&L uses dividend-adjusted
closes, so the short leg pays dividends. Sharpe is annualized over every
trading day with a 0% risk-free rate (ADR-003, ADR-006, ADR-009, ADR-010).

**Transaction-cost model** (fixed before any backtest was run; ADR-004,
ADR-011). Per leg per order: 2 bps half-spread, 3 bps slippage, and
commission of $0.005/share with a $1 minimum. Short positions also pay
0.30%/year borrow. All of these are assumptions, not measurements.
Results are also reported at 0.5×, 2×, and 3× these costs.

**Bias controls — addressed explicitly, not just listed:**

- **Look-ahead bias:** controlled at three points. (1) The pair and its
  hedge ratio are chosen using 2016–2020 data only, and all performance is
  measured on 2021–2025. (2) The z-score at day t uses a trailing 60-day
  window ending at t, and positions come from a state machine that reads
  z only up to the current day. (3) A position decided at the close of
  day t is executed at the close of t+1. Point (2) is verified by
  [`tests/test_signal.py`](tests/test_signal.py): shocking a single future
  price of either stock, at several dates, leaves every earlier z-score
  and position identical. [`tests/test_cointegration.py`](tests/test_cointegration.py)
  checks that trading-period prices cannot change pair selection.
- **Survivorship bias:** present, and not corrected. The 8-ticker
  universe consists of companies listed today. Energy producers that were
  acquired or delisted during 2016–2025 (e.g. Anadarko, Noble Energy,
  Concho, Pioneer, Marathon Oil, Hess) are excluded, partly because free
  yfinance data for delisted tickers is unreliable. The candidate set is
  therefore survivor-selected, and the choice of an energy universe is
  itself informed by general market knowledge
  ([`DECISIONS.md`](DECISIONS.md) ADR-001).
- **Multiple-testing bias:** 28 pairs were tested and the one with the
  lowest raw p-value was selected. Five pairs had raw p < 0.05, against
  about 1.4 expected by chance if no pair were cointegrated. **After Holm
  correction, no pair is significant at 5%**: the selected pair's
  adjusted p-value is 0.142. Its raw p-value of 0.0051 is therefore the
  best of 28 correlated searches, not an independent significance level.
  Out of sample (2021–2025), the same test gives p = 0.223.

## Results

Trading period 2021–2025, EOG/FANG, $100,000 gross notional per trade,
executed at the next day's close. The gross column was recorded and
frozen before any cost model code existed
([`DECISIONS.md`](DECISIONS.md) ADR-010). The net column applies the
pre-registered cost model to the **same 20 trades**, which were not
regenerated (ADR-011).

| Metric | Gross of costs | Net of costs |
|---|---:|---:|
| Total return | +3.25% (+$3,253) | +0.72% (+$715) |
| Sharpe ratio | 0.08 | 0.02 |
| Max drawdown | −11.35% | −12.28% |
| Win rate | 60.0% | 60.0% |
| Number of trades | 20 | 20 |

**Why the numbers differ:** each round trip turns over about $202,000 of
notional (entry and exit on both legs). The strategy's average gross gain
is $163 per trade, only 8.1 bps of that notional. The pre-registered
costs take $127 of it: $101 from half-spread and slippage (5 bps per
side), $9 from commissions, and $17 from short borrow over an average
28-day hold. Across 20 trades, costs total $2,538, which is 78% of the
gross P&L. Win rate is unchanged because no winning trade was small
enough to be flipped by its ~$127 cost.

| Cost multiplier | 0× (gross) | 0.5× | **1× (base)** | 2× | 3× |
|---|---:|---:|---:|---:|---:|
| Net P&L | +$3,253 | +$1,984 | **+$715** | −$1,823 | −$4,362 |

Break-even is at 1.28× the base-case costs. Cost model:
[`DECISIONS.md`](DECISIONS.md) ADR-004 and ADR-011. Full tables, cost
breakdown, and every trade: [`docs/results.md`](docs/results.md),
[`docs/results_net.md`](docs/results_net.md),
[`docs/results_gross.md`](docs/results_gross.md).

## What Didn't Work / Limitations

- **The net result is a marginal profit that is not distinguishable from
  zero.** +0.72% over five years (Sharpe 0.02) with a −12.28% maximum
  drawdown is not a usable strategy. It disappears if real costs are 28%
  higher than assumed. The gross result (Sharpe 0.08, t ≈ 0.18) was not
  statistically meaningful either.
- The cointegration relationship is not stable across periods: EOG/FANG
  had p = 0.0051 in 2016–2020 but p = 0.223 in 2021–2025, although the
  hedge ratio itself barely moved (0.742 vs. 0.754). The 2016–2020
  formation period is dominated by the March 2020 crash.
- **The pair was never statistically validated.** It was the best of 28
  searched pairs, failed Holm correction (p = 0.142), and showed no
  cointegration out of sample (p = 0.223). The backtest therefore tests a
  pair found by searching, and its small gross profit may be luck rather
  than mean reversion.
- **No stop-loss.** The two largest losses (−$5,674 and −$6,014 gross)
  came from long-spread trades held 57 and 65 days while the spread kept
  diverging. A stop-loss was not pre-registered, and adding one after
  seeing these trades would be tuning to the result.
- **Cost assumptions are assumptions.** Spread, slippage, and borrow
  rates are not measured: yfinance has no quote data. Market impact,
  regulatory fees, borrow recalls, and margin interest are not modeled,
  and idle cash earns nothing.
- Daily-frequency, free public data only (yfinance) — no intraday
  signal, no paid data feeds.
- Single pair, single time period — no claim of generalization to other
  pairs or regimes without further testing.

## Project Documentation

- [`PROJECT.md`](PROJECT.md) — full specification
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — pipeline design
- [`DECISIONS.md`](DECISIONS.md) — decision records, including the full
  record of every pair tested
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — build plan
- [`TASKS.md`](TASKS.md) — granular task checklist
- [`CHANGELOG.md`](CHANGELOG.md) — version history

## Running Locally

Requires Python 3.11 or later (developed on 3.13.7; CI runs 3.11).
Dependency versions are pinned in `requirements.txt`.

```bash
git clone https://github.com/mateeniqbal3/pairs-trading-honest-costs.git
cd pairs-trading-honest-costs
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

bash scripts/run_pipeline.sh   # data -> pair selection -> stability check -> gross -> net
```

**Reproducibility note.** Raw prices are not committed, so a fresh run
downloads them again. Yahoo revises adjusted history over time, so a new
download can differ from the snapshot used here, which is identified by
its SHA-256 in `data/dataset_manifest.json`. The published numbers
reproduce exactly only from that snapshot. If the data differ, the gross
result changes, and `scripts/run_backtest_net.py` deliberately stops,
because it only applies costs to the frozen gross trade log
(ADR-010).

## Testing

```bash
pytest tests/ -v
```

## Tech Stack

Python · pandas · NumPy · statsmodels · matplotlib · pytest

Deliberately minimal — this project's value is in the rigor of a simple
idea, not in the sophistication of the tooling.

## License

MIT — see [`LICENSE`](LICENSE)
