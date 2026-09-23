# CHANGELOG.md

All notable changes to this project are documented here. Loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Planned
- Gross-of-costs backtest
- Realistic transaction cost model applied to the same trades
- Side-by-side gross vs. net results
- README structured per the required format (problem, methodology with
  bias controls, results, limitations)

### Added
- Out-of-sample stability check for EOG/FANG (`scripts/stability_check.py`,
  `docs/stability_check.md`): cointegration not detected in 2021–2025
  (p = 0.223)
- Z-score signal (`src/signal.py`) with a look-ahead test; exit-rule
  clarification recorded as ADR-009
- ADR-008: continue with EOG/FANG although no pair survives Holm correction
- Gross-of-costs backtest (`src/backtest.py`, `scripts/run_backtest_gross.py`):
  EOG/FANG 2021–2025, +3.25% total, Sharpe 0.08, max drawdown −11.35%,
  20 trades; frozen before any cost code (ADR-010)

### Fixed
- Rolling z-score computed directly from each window, avoiding the
  rounding drift of pandas' online rolling algorithm

---

## [0.2.0] — 2026-09-23 — Data pipeline and cointegration testing

### Added
- yfinance download with timeouts, retries, and a per-ticker fallback
- Engle-Granger tests on all 28 candidate pairs (formation 2016–2020);
  selected EOG/FANG (raw p = 0.0051, Holm p = 0.142)

---

## [0.1.0] — 2026-09-23 — Scaffold

### Added
- Repository structure
- `PROJECT.md`, `TASKS.md`, `IMPLEMENTATION_PLAN.md`, `ARCHITECTURE.md`,
  `DECISIONS.md` — full project specification, including the neutral
  research question and honesty guardrails, before any code was written
- MIT License

### Changed
- Research framing rewritten as a neutral question rather than an
  assumed result; placeholder tests skip instead of passing trivially —
  see `DECISIONS.md` ADR-000

---

<!--
Template for future entries — append above this comment.
Suggested version bumps: 0.2.0 after cointegration testing, 0.3.0 after
signal + gross backtest, 0.4.0 after cost model + net backtest, 1.0.0 at
README completion.

## [0.X.0] — YYYY-MM-DD — Short title

### Added
-

### Changed
-

### Fixed
-
-->
