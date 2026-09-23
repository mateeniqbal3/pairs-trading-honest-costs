# Pairs Trading with Honest Cost Modeling

[![CI](https://github.com/mateeniqbal3/pairs-trading-honest-costs/actions/workflows/ci.yml/badge.svg)](https://github.com/mateeniqbal3/pairs-trading-honest-costs/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Research question:** How does incorporating realistic transaction
> costs affect the observed performance of a pairs-trading strategy? This
> project backtests a single pair selected by a cointegration test, reports gross and
> net-of-cost performance side by side from the same trades, and explains
> the mechanism behind any difference.

**Status:** work in progress. Pair selection and the out-of-sample
stability check are complete; no backtest has been run, so no performance
results are reported below.

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
should have prices that drift apart in the short term but revert toward a stable long-run relationship.
If that relationship is real, a spread between them that moves too far
from its historical mean should tend to move back, and a signal that buys
the relatively cheap asset and sells the relatively expensive one should
have some predictive value.

**Pair tested:** EOG Resources (EOG) / Diamondback Energy (FANG),
selected from 8 US oil and gas producers by a pre-registered rule (lowest
formation-period Engle-Granger p-value). See [`DECISIONS.md`](DECISIONS.md)
ADR-001, ADR-002, and ADR-008.

## Methodology

<!-- TODO: fill in once the pipeline is built. This section must
     explicitly name and address each bias below — do not just list them. -->

**Cointegration testing.** Engle-Granger two-step test on log adjusted
closes, 2016–2020 formation period, for all 28 pairs of
`XOM, CVX, COP, EOG, OXY, DVN, APA, FANG`. EOG/FANG: statistic −4.105
(5% critical value −3.341), raw p = 0.0051, Holm p = 0.142, hedge ratio
beta = 0.742. The hedge ratio is estimated on the formation period only
and held fixed for trading. Full table:
[`docs/pair_selection.md`](docs/pair_selection.md).

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

<!-- TODO: embed docs/results.md content here once Phase 5 completes. -->

| Metric | Gross of costs | Net of costs |
|---|---|---|
| Total return | TBD | TBD |
| Sharpe ratio | TBD | TBD |
| Max drawdown | TBD | TBD |
| Win rate | TBD | TBD |
| Number of trades | TBD | TBD |

**Why the numbers differ:** _TBD — a specific, mechanistic explanation
(e.g. trade frequency at the chosen threshold multiplied by per-trade
cost), not a vague statement that "costs matter."_

Full cost model assumptions: [`DECISIONS.md`](DECISIONS.md) ADR-004.

## What Didn't Work / Limitations

<!-- TODO: fill in honestly once the project is complete. -->

- _TBD — the net-of-costs finding, stated directly as the actual result
  of this project, whatever it turns out to be._
- The cointegration relationship is not stable across periods: EOG/FANG
  had p = 0.0051 in 2016–2020 but p = 0.223 in 2021–2025, although the
  hedge ratio itself barely moved (0.742 vs. 0.754). The 2016–2020
  formation period is dominated by the March 2020 crash.
- _TBD — the multiple-testing caveat from Methodology, restated here in
  terms of what it means for confidence in the result._
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

```bash
git clone https://github.com/mateeniqbal3/pairs-trading-honest-costs.git
cd pairs-trading-honest-costs
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

bash scripts/run_pipeline.sh   # not implemented yet
```

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
