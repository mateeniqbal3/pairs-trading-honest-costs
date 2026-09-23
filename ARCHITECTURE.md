# ARCHITECTURE.md — pairs-trading-honest-costs

## 1. System Overview

A small, linear research pipeline — no services, no deployment. Data flows
through cointegration testing, signal construction, and a backtest that is
run twice with identical inputs and logic, differing only in whether
transaction costs are applied. The comparison between those two runs is
the entire architectural point of this repo.

## 2. Pipeline Flow

```
yfinance daily price data (candidate universe)
              |
              v
        src/data.py
   load, clean, align
              |
              v
   src/cointegration.py
   Engle-Granger/Johansen test across
   ALL candidate pairs (full record kept,
   not just the winner)
              |
              v
     Selected pair (documented selection
     + full multiple-testing record)
              |
              v
        src/signal.py
   z-score of spread, TRAILING WINDOW ONLY
   (look-ahead verified by test)
              |
              v
        src/backtest.py
   backtesting loop, trades the signal
              |
   +----------+----------+
   v                     v
Gross-of-costs           src/costs.py applied
metrics                   to the SAME trades
   |                     v
   |              Net-of-costs metrics
   |                     |
   +----------+----------+
              v
       docs/results.md
   side-by-side gross vs. net,
   with a specific mechanistic
   explanation of the gap
              |
              v
          README.md
   (the actual deliverable --
    structured per PROJECT.md
    section 9)
```

## 3. Why the Backtest Runs Twice, Not Once-With-A-Toggle

`src/backtest.py`'s core trade-generation logic (when to enter/exit based
on the signal) is identical for both the gross and net calculation — only
`src/costs.py`'s contribution differs. This is deliberate: it guarantees
the two result sets are comparing the same trades under different cost
assumptions, not two different strategies. If the trade list differs
between the gross and net runs, that's a bug, not a modeling choice — see
`tests/test_backtest.py`.

## 4. Component Responsibilities

| Component | Responsibility | Does NOT do |
|---|---|---|
| `src/data.py` | Load and align price data | Signal or cost logic |
| `src/cointegration.py` | Test all candidate pairs, keep full record | Signal construction |
| `src/signal.py` | Z-score signal, trailing-window only | Trade execution/backtesting |
| `src/backtest.py` | Generate trades from the signal, compute metrics | Cost modeling itself |
| `src/costs.py` | Model spread/slippage/fees, applied to backtest trades | Signal or trade-timing logic |

## 5. Key Architectural Decisions (summary — full rationale in DECISIONS.md)

- **Vectorized pandas/numpy backtest, not a full event-driven engine**:
  appropriate for daily-frequency, single-pair data at this project's
  scope — see `PROJECT.md` §6 on deliberately minimal tooling.
  `lob-alpha-engine`'s full event-driven backtester is the right tool for
  tick-level microstructure data; it would be overkill here.
- **Cost model as a separate, pluggable module** (`src/costs.py`) rather
  than inline in the backtest: keeps the "same trades, different cost
  assumption" comparison structurally clean and easy to verify.
- **Full record of all tested pairs kept from Phase 2 onward**: this is
  what makes the multiple-testing disclosure in the README possible —
  reconstructing this after the fact would not be credible.
