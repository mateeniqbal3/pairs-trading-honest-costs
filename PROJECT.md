# PROJECT.md — Pairs Trading with Honest Cost Modeling

> **Status:** Not started
> **Owner:** mateeniqbal3
> **Track:** Quant Finance (standalone — not tied to any academic
> semester/summer phase, not part of the RTP/Fulbright thesis narrative,
> and not dependent on `lob-alpha-engine` or `stat-arb-optimizer`)
> **Repo:** `pairs-trading-honest-costs`
> **License:** MIT
> **Purpose:** an intentionally small, foundational project. Its value is
> not architectural sophistication — it's a complete, clean demonstration
> of the single most important discipline in quant research: measuring how
> a strategy's backtested edge changes once realistic costs are applied,
> and explaining why, rather than reporting only the flattering pre-cost
> number. This is the project a quant interviewer can read start to finish
> in ten minutes and come away trusting the candidate's judgment.

This is the canonical specification. Where it is ambiguous, make the most
reasonable engineering decision, record it in `DECISIONS.md`, and continue.
Changes to the research question, dataset, universe, time period,
parameters, cost assumptions, or evaluation methodology are never made
silently — see §11.

---

## 1. Purpose

Find two cointegrated assets, build a mean-reversion (pairs trading)
signal from their price relationship, backtest it, and report performance
**both with and without realistic transaction costs, side by side** —
with an honest discussion of why the edge changes between the two. The
deliverable is not "a profitable strategy." The deliverable is a rigorous,
transparent measurement of the gap between a naive backtest and a
cost-aware one, and what that gap teaches about evaluating trading ideas.

## 2. The point of this project, stated directly

The research question, stated neutrally (quote this in the README):

> "How does incorporating realistic transaction costs affect the observed
> performance of a pairs-trading strategy? This project backtests a
> single pair selected by a cointegration test, reports gross and net-of-cost performance side
> by side from the same trades, and explains the mechanism behind any
> difference."

The answer is not assumed in advance. A common prior is that a naive
pairs backtest looks profitable gross of costs and that much of the edge
disappears net of costs — but that is a hypothesis to be tested, not a
result. The README may state the finding only after the pipeline has
actually produced it, and must state it exactly as produced.

Every outcome is reportable: profitable net of costs, unprofitable gross
and net, profitable gross but not net, or inconclusive/unstable. Do not
tune costs downward, cherry-pick the pair, or adjust methodology to
manufacture a post-cost profit (or a dramatic post-cost collapse). The
value of this project is in the rigor and honesty of the comparison, not
in which side of profitability the result lands on.

## 3. Problem Statement

Given historical daily price data for a universe of liquid, related
assets (e.g. within the same sector or a small ETF/equity set), identify
a cointegrated pair, construct a z-score-based mean-reversion signal on
the spread, backtest it with a realistic transaction-cost model, and
report the strategy's Sharpe ratio, drawdown, and other standard metrics
**both gross and net of costs**, explaining the delta between them.

## 4. Success Criteria (Definition of Done)

- [ ] Research design (universe, periods, test, thresholds, execution and
      cost assumptions) recorded in `DECISIONS.md` before any price data
      is downloaded or any backtest is run
- [ ] Historical price data acquired for a candidate universe (free
      sources — see §5)
- [ ] Cointegration testing performed across candidate pairs (e.g.
      Engle-Granger or Johansen test), with the actual test statistics
      and p-values reported — not just an assertion that a pair is
      cointegrated
- [ ] Z-score mean-reversion signal constructed on the selected pair's
      spread, with entry/exit thresholds documented and justified
- [ ] Backtesting loop implemented (pandas/numpy — no need for a
      full event-driven engine at this project's scope)
- [ ] Realistic transaction cost model applied: at minimum, bid-ask
      spread cost and a slippage assumption; commission/fees if
      applicable to the chosen instruments
- [ ] **Results reported side by side: gross-of-costs vs. net-of-costs**
      — same metrics (Sharpe, total return, max drawdown, win rate),
      same table or chart, directly comparable
- [ ] Explicit bias-control section: look-ahead bias, survivorship bias,
      and multiple-testing bias (from pair selection) each named and
      addressed concretely, not just listed
- [ ] Honest "what didn't work / limitations" section in the README —
      framed as a positive signal of rigor, not hedging
- [ ] CI pipeline (lint + test)
- [ ] README structured per §9 exactly

## 5. Dataset — Free/Public Sources Only

**Budget constraint: $0**, same discipline as `lob-alpha-engine` and
`stat-arb-optimizer`. Use `yfinance` for historical daily price data —
this project's scope (a small number of candidate pairs, daily
frequency) fits comfortably within what yfinance provides for free.
Document the exact candidate universe and selected pair in
`data/dataset_manifest.json` and `DECISIONS.md`.

## 6. Tech Stack

Python · pandas · NumPy · statsmodels (for cointegration testing) ·
matplotlib · pytest

Deliberately minimal — this project does not need PyTorch, XGBoost, or any
heavy ML framework. A simple, well-executed statistical strategy is the
entire point; reaching for unnecessary ML sophistication here would
actually undercut the project's credibility with its target reader.

## 7. Bias Controls — Required, Named Explicitly

The README's Methodology section must explicitly name and address each of
these, not just gesture at "we controlled for bias":

- **Look-ahead bias**: the z-score signal at time T must be computed using
  only price data available at or before T (e.g. a rolling mean/std
  window that ends at T, never one that peeks forward). The same applies
  to pair selection and hedge-ratio estimation: parameters used to trade a
  given day must be estimated only from data available before that day.
  State this explicitly and verify it in a test.
- **Survivorship bias**: if the candidate universe is selected based on
  currently-listed, currently-liquid assets, say so plainly — this is a
  real limitation (the pair may only look attractive in hindsight because
  both assets survived to the present) and should be named, not hidden.
- **Multiple-testing bias from pair selection**: if more than one
  candidate pair was tested for cointegration before selecting the final
  one, the selection itself is a form of multiple testing that inflates
  the apparent significance of the "winning" pair. Report how many pairs
  were actually tested, and discuss (even briefly) what this implies
  about the reported p-value's real strength.

## 8. Results Presentation — Gross vs. Net, Side by Side

This is the project's central structural requirement. `docs/results.md`
and the README must present:

| Metric | Gross of costs | Net of costs |
|---|---|---|
| Total return | | |
| Sharpe ratio | | |
| Max drawdown | | |
| Win rate | | |
| Number of trades | | |

Alongside a brief, specific discussion of *why* the numbers differ the way
they do (e.g. "the strategy trades frequently at a tight z-score
threshold, so per-trade costs compound quickly" — a concrete mechanism,
not a vague gesture at "costs matter").

## 9. Required README Structure

Per the requirements given for this project, the README must include,
in this order:
1. **Problem statement** and the mechanism/hypothesis being tested (why
   would this pair mean-revert — what's the economic story, even if
   simple?)
2. **Methodology** section explicitly naming the bias controls from §7
3. **Results** — gross vs. net of costs, side by side (§8)
4. **What didn't work / limitations** — framed as a positive signal of
   rigor

## 10. Repository Structure

```
pairs-trading-honest-costs/
├── PROJECT.md
├── TASKS.md
├── IMPLEMENTATION_PLAN.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── CHANGELOG.md
├── README.md
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── .github/workflows/ci.yml
├── src/
│   ├── __init__.py
│   ├── data.py                # price data loading (yfinance)
│   ├── cointegration.py       # pair testing (Engle-Granger/Johansen)
│   ├── signal.py              # z-score mean-reversion signal construction
│   ├── backtest.py            # backtesting loop, gross and net-of-cost modes
│   └── costs.py               # transaction cost model (spread, slippage, fees)
├── tests/
│   ├── test_data.py
│   ├── test_cointegration.py
│   ├── test_signal.py         # includes a look-ahead-bias check
│   └── test_backtest.py
├── notebooks/
│   └── 01_pair_selection.ipynb
├── data/
│   ├── dataset_manifest.json
│   ├── raw/                   # gitignored
│   └── processed/             # gitignored
├── docs/
│   └── results.md             # the gross-vs-net table and discussion, section 8
├── paper/
│   └── writeup.md             # optional short writeup, see TASKS.md
└── scripts/
    └── run_pipeline.sh
```

Note: no `Dockerfile` is required for this project — its scope (a local
research script/notebook workflow) doesn't need containerized deployment,
and adding one would be scope inflation for a project whose value is
precisely its focus and simplicity.

## 11. Constraints & Guardrails

- $0 data constraint — yfinance only
- No Docker, no API, no deployment — this is a research script/notebook
  project, not a service
- Do not adjust the transaction cost model, pair selection, or
  methodology after seeing a result, in order to manufacture a more
  attractive (or more dramatic) outcome — see §2
- Never silently change the research question, dataset, universe, time
  period, parameters, cost assumptions, or evaluation methodology. If a
  change is necessary, record in `DECISIONS.md`: the original choice, the
  new choice, the reason, and whether any previously generated results
  are invalidated
- Never fabricate or hard-code results; documentation reports only what
  the pipeline has actually produced
- Report the actual number of pairs tested before selection (§7)

## 12. Definition of Done

See `TASKS.md`. At the project level: all boxes in §4 checked, gross vs.
net results presented side by side with an honest mechanistic
explanation, all three named biases (§7) explicitly addressed, README
structured exactly per §9, CI green.
