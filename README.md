# Pairs Trading with Honest Cost Modeling

[![CI](https://github.com/mateeniqbal3/pairs-trading-honest-costs/actions/workflows/ci.yml/badge.svg)](https://github.com/mateeniqbal3/pairs-trading-honest-costs/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Research question:** How does incorporating realistic transaction
> costs affect the observed performance of a pairs-trading strategy? This
> project backtests a single cointegrated pair, reports gross and
> net-of-cost performance side by side from the same trades, and explains
> the mechanism behind any difference.

**Status:** work in progress — no experiment has been run yet, so no
results are reported below.

---

## Problem Statement

<!-- TODO: fill in once Phase 2 (cointegration testing / pair selection)
     completes. -->

**Hypothesis:** Two assets with a plausible economic link — _TBD, e.g.
same sector, similar business exposure_ — should have prices that drift
apart in the short term but revert toward a stable long-run relationship.
If that relationship is real, a spread between them that moves too far
from its historical mean should tend to move back, and a signal that buys
the relatively cheap asset and sells the relatively expensive one should
have some predictive value.

**Pair tested:** _TBD — see [`DECISIONS.md`](DECISIONS.md) ADR-002 for the
selected pair and the reasoning behind it._

## Methodology

<!-- TODO: fill in once the pipeline is built. This section must
     explicitly name and address each bias below — do not just list them. -->

**Cointegration testing.** _TBD — which test (Engle-Granger/Johansen), and
the result for the selected pair._

**Bias controls — addressed explicitly, not just listed:**

- **Look-ahead bias:** _TBD — the z-score signal will be computed using
  only a trailing rolling window of past prices, and a test in
  [`tests/test_signal.py`](tests/test_signal.py) will confirm that
  changing a future price does not change an earlier timestamp's signal
  value. (Not yet implemented.)_
- **Survivorship bias:** _TBD — state plainly whether the candidate
  universe was selected based on currently-listed, currently-liquid
  assets, and what that implies (the pair may look more attractive in
  hindsight than it would have looked in real time)._
- **Multiple-testing bias:** _TBD — state how many candidate pairs were
  actually tested for cointegration before this one was selected (see
  [`DECISIONS.md`](DECISIONS.md) ADR-001), and what that implies about how
  strongly to trust the selected pair's p-value._

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
- _TBD — any instability in the cointegration relationship over the
  sample period._
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
