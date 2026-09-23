# TASKS.md — pairs-trading-honest-costs

Ordered checklist. Work top to bottom, commit after each phase group.
Read `PROJECT.md` §2 before Phase 5 (backtest with costs) — that's where
this project's central discipline lives.

## Phase 0 — Setup

- [ ] Init git repo, `.gitignore` (Python, data/raw, data/processed,
      .env, __pycache__, local assistant/editor files)
- [x] `pyproject.toml`, `requirements.txt`
- [x] `LICENSE` (MIT, mateeniqbal3, current year)
- [x] Folder structure per `PROJECT.md` §10
- [ ] Commit: "chore: initial project scaffold"

## Phase 0.5 — Research Design (recorded before any data is downloaded)

- [ ] Record in `DECISIONS.md`, with status `Accepted`, before Phase 1:
      candidate universe, sample and formation/trading periods,
      cointegration test and selection rule, hedge-ratio and spread
      construction, z-score window and entry/exit thresholds, execution
      timing, position sizing, and the transaction cost model with its
      parameters
- [ ] Commit: "docs: pre-register research design"

## Phase 1 — Data + Candidate Universe

- [ ] Pull historical daily price data via `yfinance` for the
      pre-registered candidate universe
- [ ] Write `data/dataset_manifest.json`: tickers, date range, source
- [ ] Write `src/data.py`: load, clean, align
- [ ] `tests/test_data.py`
- [ ] Commit: "feat: price data pipeline"

## Phase 2 — Cointegration Testing

- [ ] Write `src/cointegration.py`: Engle-Granger (or Johansen) test
      across all candidate pairs in the universe
- [ ] Record the actual test statistic and p-value for EVERY pair tested,
      not just the one ultimately selected — this full record is required
      for the multiple-testing disclosure in `PROJECT.md` §7
- [ ] Select the pair using the pre-registered selection rule; document
      the selection and the full list of pairs tested in `DECISIONS.md`
- [ ] `notebooks/01_pair_selection.ipynb`: visualize the candidate pairs'
      price series and spreads
- [ ] `tests/test_cointegration.py`
- [ ] Commit: "feat: cointegration testing across candidate pairs — see DECISIONS.md for full results"

## Phase 3 — Signal Construction

- [ ] Write `src/signal.py`: z-score of the spread, computed using ONLY a
      trailing rolling window (never a window that includes future data)
- [ ] Implement the pre-registered entry/exit z-score thresholds
- [ ] `tests/test_signal.py`: MUST include an explicit test verifying no
      look-ahead — e.g. confirm that changing a future price value does
      not change the z-score computed at an earlier timestamp
- [ ] Commit: "feat: z-score mean-reversion signal (look-ahead verified by test)"

## Phase 4 — Backtest (gross of costs)

- [ ] Write `src/backtest.py`: simple event-driven-in-spirit backtesting
      loop (a pandas/numpy vectorized backtest is fine at this project's
      scope) that trades the signal from Phase 3
- [ ] Compute gross-of-costs metrics: total return, Sharpe ratio, max
      drawdown, win rate, number of trades
- [ ] `tests/test_backtest.py`
- [ ] Commit: "feat: gross-of-costs backtest"

## Phase 5 — Realistic Transaction Costs (the central discipline)

- [ ] Write `src/costs.py`: implement the pre-registered transaction cost
      model — bid-ask spread cost, a slippage assumption, and
      commission/fees if applicable to the chosen instruments
- [ ] Apply this cost model to the SAME backtest from Phase 4, producing
      net-of-costs metrics using the identical signal and trades — only
      the cost treatment differs
- [ ] Generate `docs/results.md`: the side-by-side gross vs. net table
      from `PROJECT.md` §8, plus a concrete, specific explanation of why
      the numbers differ (not a vague "costs matter" statement)
- [ ] Do NOT adjust the cost model, signal thresholds, or pair selection
      after seeing this result in order to change the net-of-cost number
      — see `PROJECT.md` §2 and §11
- [ ] Commit: "feat: realistic transaction cost model applied — see docs/results.md for gross vs. net comparison"

## Phase 6 — CI

- [x] `.github/workflows/ci.yml`: lint + test on push/PR to `main`
- [ ] Confirm CI is green on GitHub after the first push
- [ ] Commit: "ci: add lint + test workflow"

## Phase 7 — Optional Writeup

- [ ] Write `paper/writeup.md`: a short writeup (this project doesn't
      need a full academic paper — a clear few-page writeup covering
      hypothesis, methodology, bias controls, and the gross-vs-net
      finding is sufficient) — optional but recommended given this
      project's interview-narrative purpose
- [ ] Commit: "docs: writeup complete" (if pursued)

## Phase 8 — README (this is the actual deliverable — see PROJECT.md section 9)

- [ ] Write `README.md` in the exact structure required by `PROJECT.md`
      §9: (1) problem statement + mechanism/hypothesis, (2) methodology
      with explicit bias controls (§7), (3) gross vs. net results side by
      side (§8), (4) honest "what didn't work / limitations" section
      framed as a positive signal
- [ ] Include the research-question quote from `PROJECT.md` §2, followed
      by the finding exactly as the pipeline produced it
- [ ] Fill `DECISIONS.md` with all real decisions, including the full
      list of pairs tested (Phase 2) and cost model parameters
- [ ] `CHANGELOG.md` v1.0.0 entry
- [ ] Final review: does the README read like an honest research finding,
      or like a strategy pitch? If it leans toward the latter anywhere,
      rewrite that section.
- [ ] Publication check: search the repo for assistant references, local
      absolute paths, secrets, and stale or unexecuted notebook outputs

## Definition of Done

All boxes checked, gross vs. net results presented side by side with an
honest mechanistic explanation, all three named biases addressed
explicitly, README structured exactly per `PROJECT.md` §9, CI green.
