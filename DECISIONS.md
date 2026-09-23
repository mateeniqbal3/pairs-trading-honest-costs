# DECISIONS.md — Research Decision Records

Format: ADR number, status, Context / Decision / Consequences. Append real
ADRs as decisions are made.

Status values: `Proposed`, `Accepted`, `Superseded by ADR-00X`, `Rejected`.

Change rule: the research question, dataset, universe, time period,
parameters, cost assumptions, and evaluation methodology are never changed
silently. Any change is recorded as a new ADR (or an amendment block in
the affected ADR) stating the original choice, the new choice, the reason,
and whether previously generated results are invalidated.

**Pre-registration status (2026-09-23):** ADR-001 through ADR-004 and
ADR-006 below are a *proposed* research design. No price data has been
downloaded and no test or backtest has been run. Once the design is
accepted, each ADR's status moves to `Accepted` and the date is recorded;
only then does Phase 1 begin.

---

## ADR-000: Revisions to the initial project specification

**Status:** Accepted — 2026-09-23

**Context:** The initial scaffold stated the expected result as though it
were established ("once realistic transaction costs were modeled, the
edge mostly disappeared") and asked for that sentence to be quoted in the
README. It also contained placeholder tests that passed trivially,
including the look-ahead test, and a pipeline script that exited
successfully without doing anything. No results existed when these
revisions were made, so none are invalidated.

**Decision:**

| Item | Original | New | Reason |
|---|---|---|---|
| Research framing (`PROJECT.md` §2, README tagline) | Assumed result: "the edge mostly disappeared" | Neutral research question; the finding is stated only once produced | A hypothesis must not be presented as a result before the experiment runs |
| Placeholder tests | `assert True` (reported as passing) | `pytest.skip` with a reason | A passing look-ahead test that checks nothing is misleading; skipped is accurate |
| `scripts/run_pipeline.sh` | Printed TODO, exited 0 | Prints "not implemented", exits 1 | A no-op should not look like a successful run |
| Task order | Cost model parameters settled in Phase 5 | Full research design, including costs, recorded in Phase 0.5 before any data download | The original plan already asked for costs to be decided before seeing results; pre-registering makes that verifiable |
| Look-ahead scope (`PROJECT.md` §7) | Z-score window only | Also pair selection and hedge-ratio estimation | Selecting a pair and fitting its hedge ratio on the same data that is then traded is a form of look-ahead |
| `notebooks/01_pair_selection.ipynb` | Plain text with an `.ipynb` extension | Valid, empty notebook with a markdown header cell | The original file was not a loadable notebook |

**Consequences:** The README cannot carry a headline result until
Phase 5 produces one. CI shows skipped tests rather than green passes
until real tests exist.

---

## ADR-001: Candidate universe, sample period, and full pair-testing record

**Status:** Proposed — 2026-09-23 (awaiting confirmation; no data downloaded)

**Context:** `PROJECT.md` §7 requires disclosing every pair tested for
cointegration, not just the selected one, to address multiple-testing
bias honestly. The universe and dates must be fixed before any data is
seen.

**Decision (proposed):**

- **Universe:** 8 US-listed large-cap oil and gas producers (integrated
  and exploration & production): `XOM, CVX, COP, EOG, OXY, DVN, APA,
  FANG`. All eight C(8,2) = **28 pairs** are tested; no pair is dropped
  before testing.
- **Economic rationale for the universe:** these firms' revenues and
  equity values share a dominant common driver (crude oil and natural gas
  prices), which is the standard economic story for why prices within the
  group might share a long-run stochastic trend.
- **Sample:** the ten most recent complete calendar years,
  2016-01-01 to 2025-12-31, daily. Fixed end date for reproducibility.
- **Formation period:** 2016-01-01 to 2020-12-31 (5 years). Used for
  cointegration testing, pair selection, and hedge-ratio estimation.
- **Trading period (out of sample):** 2021-01-01 to 2025-12-31 (5 years).
  Every reported performance metric comes from this period only.
- **Split rule:** 50/50 by calendar years, chosen as a rule rather than
  by inspecting any data.

**Known limitations, stated in advance:**

- **Survivorship:** all eight tickers are listed today. Energy companies
  that were acquired or delisted during 2016–2025 (for example Anadarko,
  Noble Energy, Concho Resources, Pioneer Natural Resources, Marathon Oil,
  Hess) are excluded, partly because free yfinance data for delisted
  tickers is unreliable. The universe is therefore survivor-selected.
- **Hindsight in universe choice:** picking a sector known for
  co-movement is itself informed by general market knowledge.
- **Corporate actions:** several of these firms completed large mergers
  in the sample (OXY/Anadarko 2019, DVN/WPX 2021, COP/Concho 2021,
  XOM/Pioneer 2024, COP/Marathon 2024, CVX/Hess 2025), which change the
  businesses behind the tickers.
- **Regime:** the formation period includes the 2020 oil price collapse.

**Full pair-testing record:** _to be filled from pipeline output: all 28
pairs with test statistic, raw p-value, Holm and Bonferroni adjusted
p-values, and hedge ratio._

**Consequences:** _Fill in after Phase 2: given 28 tests, how strongly
should the selected pair's p-value be trusted?_

---

## ADR-002: Cointegration test, selection rule, and selected pair

**Status:** Proposed — 2026-09-23 (awaiting confirmation)

**Context:** Beyond passing a statistical test, a pairs trade should have
some plausible economic reason to mean-revert. The selection rule must be
fixed before seeing the test results.

**Decision (proposed):**

- **Test:** Engle-Granger two-step test (`statsmodels.tsa.stattools.coint`,
  constant term, lag length by AIC) on log adjusted-close prices, using
  formation-period data only.
- **Ordering:** the dependent variable is the alphabetically first ticker
  of each pair. This is arbitrary but chosen before seeing any data. The
  reverse ordering is also computed and reported as a robustness check,
  but not used for selection.
- **Selection rule:** the pair with the lowest raw Engle-Granger p-value
  in the formation period is selected and traded. Correlation is not used
  for selection.
- **Multiple-testing disclosure:** raw, Holm-adjusted, and
  Bonferroni-adjusted p-values are reported for all 28 pairs.
- **Weak-relationship rule:** if the selected pair's raw p-value is
  above 0.05, or it does not survive Holm adjustment at 5%, this is
  reported as a finding and raised with the project owner before the
  backtest proceeds. The selected pair is not silently replaced.
- **Out-of-sample stability diagnostic:** the same test is rerun on the
  trading period for the selected pair and reported. This is a diagnostic
  only and is never used to change the pair.

**Selected pair:** _to be filled from pipeline output._

**Consequences:** _Fill in after Phase 2._

---

## ADR-003: Hedge ratio, spread, z-score, and entry/exit thresholds

**Status:** Proposed — 2026-09-23 (awaiting confirmation)

**Context:** Entry/exit thresholds control trade frequency, which
directly interacts with cost sensitivity. They must be set before any
backtest (gross or net) is run.

**Decision (proposed):**

- **Hedge ratio:** OLS of log(Y) on a constant and log(X) over the
  formation period only. It stays fixed for the whole trading period and
  is not re-estimated.
- **Spread:** `s_t = log(Y_t) - beta * log(X_t) - alpha`.
- **Z-score:** `z_t = (s_t - mean(s_{t-59..t})) / std(s_{t-59..t})`, a
  60-trading-day trailing window ending at and including the close of
  day t. No centered or forward windows. At the start of the trading
  period the window uses formation-period spread values, which are
  genuinely past data.
- **Entry:** enter short-spread when `z_t >= +2.0`; enter long-spread
  when `z_t <= -2.0`.
- **Exit:** close when `|z_t| <= 0.5`. Any position still open at the end
  of the trading period is closed at the final close, costs included.
- **No stop-loss** (stated as a limitation: divergence risk is unbounded).
- **Justification:** ±2.0 entry and a 0.5 exit band are conventional
  values in the pairs-trading literature. A 60-day window is roughly one
  quarter. None of these values is tuned, and no sensitivity analysis is
  run over thresholds.

**Consequences:** _Fill in after Phase 4 (trade count, holding periods)._

---

## ADR-004: Transaction cost model parameters

**Status:** Proposed — 2026-09-23 (awaiting confirmation; set before any backtest)

**Context:** `PROJECT.md` §4 requires at minimum a bid-ask spread cost and
a slippage assumption. yfinance daily bars contain no quote data, so
spread and slippage are assumptions, not measurements.

**Decision (proposed), applied per leg, per side, to traded notional:**

| Component | Base case | Basis |
|---|---|---|
| Half bid-ask spread | 2 bps | Assumption: quoted spreads in US large-cap energy names are typically a few bps |
| Slippage / impact | 3 bps | Assumption: execution at or near the close at small size, plus timing noise |
| Commission | $0.005/share, $1.00 minimum per order | A published fixed-rate retail/pro broker schedule (e.g. Interactive Brokers Pro fixed) |
| Regulatory fees | Not modeled | Roughly 0.3 bps on sales; stated as a limitation |
| Short borrow | 0.30% per year on short notional, accrued daily | Assumption: general-collateral rate for easy-to-borrow large caps |

- A round trip on both legs therefore costs roughly 10–12 bps of gross
  notional plus borrow. This is an approximation and is labeled as one.
- **Sensitivity (pre-registered, reported in full):** net results at cost
  multipliers 0×, 0.5×, 1×, 2×, 3× of the base case (0× = gross). 1× is
  the headline "net" figure and is fixed now.
- A cost breakdown by component (spread, slippage, commission, borrow) is
  reported alongside net results.

**Consequences:** _Fill in after Phase 5._

---

## ADR-005: The gross-vs-net finding

**Status:** Open — filled in only from actual pipeline output

**Context:** This is the project's central result — see `PROJECT.md` §2.

**Decision:** _Fill in the actual finding, precisely: gross Sharpe X, net
Sharpe Y, driven primarily by [specific mechanism, e.g. trade frequency
at the chosen threshold multiplied by per-trade cost]._

**Consequences:** _Fill in: does the strategy remain profitable net of
costs, or not? State this plainly and let it stand as reported._

---

## ADR-006: Execution timing, position sizing, and accounting

**Status:** Proposed — 2026-09-23 (awaiting confirmation)

**Context:** Pairs trading involves simultaneous long and short positions;
the backtest must state how and when trades are executed and how returns
are measured.

**Decision (proposed):**

- **Prices:** yfinance adjusted closes (split- and dividend-adjusted), so
  the short leg is implicitly charged dividends.
- **Timing:** signal computed from the close of day t; both legs executed
  simultaneously at the close of day t+1. The one-day lag is a
  conservative stand-in for real decision latency.
- **Capital:** $100,000, not compounded. Each trade uses $100,000 of
  gross notional, split between legs as $1 of Y for every $|beta| of X
  (weights `1/(1+|beta|)` and `|beta|/(1+|beta|)`). Share counts are fixed
  at entry and not rebalanced while the trade is open.
- **Leverage and margin:** gross exposure 1× capital. Margin requirements
  for the short leg are not modeled beyond this.
- **Idle cash:** earns 0% and short proceeds earn no rebate (a
  conservative simplification).
- **Returns and metrics:** daily P&L divided by $100,000 of capital.
  Sharpe is annualized with √252 and a 0% risk-free rate. Reported for
  both gross and net: total return, annualized return, annualized
  volatility, Sharpe, max drawdown, number of round-trip trades, win rate
  (per trade), average trade P&L, average holding period, and turnover.

**Consequences:** _Fill in after Phase 4/5._

---

## ADR-007: [Template for future ADRs]

**Status:** Proposed / Accepted / Superseded / Rejected

**Context:** What situation forced this decision?

**Decision:** What was decided? If this changes an earlier decision:
original choice, new choice, reason, and which results are invalidated.

**Consequences:** What trade-offs does this create? Be honest.
