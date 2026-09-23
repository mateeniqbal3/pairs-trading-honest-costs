# DECISIONS.md — Research Decision Records

Format: ADR number, status, Context / Decision / Consequences. Append real
ADRs as decisions are made.

Status values: `Proposed`, `Accepted`, `Superseded by ADR-00X`, `Rejected`.

Change rule: the research question, dataset, universe, time period,
parameters, cost assumptions, and evaluation methodology are never changed
silently. Any change is recorded as a new ADR (or an amendment block in
the affected ADR) stating the original choice, the new choice, the reason,
and whether previously generated results are invalidated.

**Pre-registration status:** ADR-001 through ADR-004 and ADR-006 were
proposed and then accepted by the project owner on 2026-09-23, before any
price data was downloaded or any test or backtest was run. ADR-007 (data
handling) was also recorded before the download.

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

**Status:** Accepted — 2026-09-23

**Context:** `PROJECT.md` §7 requires disclosing every pair tested for
cointegration, not just the selected one, to address multiple-testing
bias honestly. The universe and dates must be fixed before any data is
seen.

**Decision:**

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

**Full pair-testing record:** all 28 pairs, with test statistic, raw,
Holm, and Bonferroni p-values, hedge ratio, and reverse-ordering p-value,
are in [`docs/pair_selection.md`](docs/pair_selection.md), generated by
`scripts/select_pair.py`. The machine-readable copy is in
`data/dataset_manifest.json`. Raw data SHA-256 `59106b32…823e2`,
downloaded 2026-09-23T17:55:59Z with yfinance 1.7.0. The aligned sample
runs from 2016-01-04 to 2025-12-31 (2,514 days, none dropped), and the
formation period has 1,259 days.

**Consequences (recorded 2026-09-23 from pipeline output):** 5 of 28
pairs have raw p < 0.05. If no pair were truly cointegrated, about 1.4
such results would be expected by chance. The 28 tests are not
independent, since every pair shares the same oil-price factor, so that
count is only a rough guide. After Holm correction, **no pair is
significant at 5%**: the smallest Holm-adjusted p-value is 0.142. The
selected pair's raw p-value of 0.0051 should therefore be read as the
best of 28 correlated searches, not as a standalone significance level.
The formation period is also dominated by the March 2020 crash: every
ticker's largest daily move falls in that month, most of them on
2020-03-09.

---

## ADR-002: Cointegration test, selection rule, and selected pair

**Status:** Accepted — 2026-09-23

**Context:** Beyond passing a statistical test, a pairs trade should have
some plausible economic reason to mean-revert. The selection rule must be
fixed before seeing the test results.

**Decision:**

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

**Selected pair (recorded 2026-09-23 from pipeline output):** **EOG / FANG**
(Y = EOG, X = FANG), selected by the pre-registered rule of lowest raw
p-value. Engle-Granger statistic −4.105 (5% critical value −3.341), raw
p = 0.0051, Holm p = 0.142, Bonferroni p = 0.142. Formation hedge ratio
beta = 0.7423, alpha = 1.0063. The reverse ordering gives p = 0.0036.
Economic rationale: both are US shale oil producers with large Permian
Basin operations (Diamondback almost entirely Permian), so both are
exposed to the same crude price, basin differentials, and service-cost
cycle.

**Weak-relationship rule: TRIGGERED.** The selected pair does not survive
Holm adjustment at 5% (0.142 > 0.05). As ADR-002 requires, this is
reported as a finding and raised with the project owner before any
backtest. The pair has not been replaced, and no signal or backtest has
been run.

**Consequences:** The owner chose to continue with EOG/FANG — see ADR-008.

---

## ADR-003: Hedge ratio, spread, z-score, and entry/exit thresholds

**Status:** Accepted — 2026-09-23

**Context:** Entry/exit thresholds control trade frequency, which
directly interacts with cost sensitivity. They must be set before any
backtest (gross or net) is run.

**Decision:**

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

**Status:** Accepted — 2026-09-23

**Context:** `PROJECT.md` §4 requires at minimum a bid-ask spread cost and
a slippage assumption. yfinance daily bars contain no quote data, so
spread and slippage are assumptions, not measurements.

**Decision, applied per leg, per side, to traded notional:**

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

**Status:** Accepted — 2026-09-23

**Context:** Pairs trading involves simultaneous long and short positions;
the backtest must state how and when trades are executed and how returns
are measured.

**Decision:**

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

## ADR-007: Data retrieval, cleaning, and implementation details of the test

**Status:** Accepted — 2026-09-23 (recorded before any data was downloaded)

**Context:** ADR-001 and ADR-002 fix the universe, periods, test, and
selection rule, but not how the raw data is retrieved and cleaned or a few
mechanical details of the test. Deciding these after seeing the data
would leave room to influence the result, so they are fixed here first.

**Decision:**

- **Retrieval:** one `yfinance.download` call for all 8 tickers,
  `start="2016-01-01"`, `end="2026-01-01"` (yfinance's `end` is exclusive,
  so the last possible date is 2025-12-31), `interval="1d"`,
  `auto_adjust=False` so both `Close` and `Adj Close` are stored. The raw
  download is saved to `data/raw/prices_raw.csv` (gitignored). Its SHA-256
  hash, the UTC download timestamp, and the yfinance version are recorded
  in `data/dataset_manifest.json`. Later runs reuse the saved file rather
  than downloading again, because Yahoo can revise history.
- **Series used:** `Adj Close` (ADR-006). Yahoo back-adjusts history for
  dividends and splits relative to the download date, so formation-period
  prices contain adjustment factors for events after 2020. Those factors
  are the same across every formation-period date, so they shift log
  prices by a constant. That constant only changes the intercept `alpha`,
  not `beta` or the Engle-Granger statistic, so it does not leak
  trading-period information into pair selection.
- **Alignment and missing data:** keep only dates on which all 8 tickers
  have an `Adj Close`. No forward-filling, interpolation, or outlier
  removal. The number of dates dropped, and which tickers caused it, is
  reported.
- **Validation (fails loudly, never silently repaired):** dates unique
  and increasing, all prices finite and strictly positive, all 8 tickers
  present.
- **Period slicing:** the formation period includes both endpoints
  (2016-01-01 to 2020-12-31) and is cut from the aligned full sample.
- **Test implementation:** `coint(y, x, trend="c", autolag="aic")`, with
  statsmodels' default maximum lag. The p-values are MacKinnon
  approximations. Holm and Bonferroni adjustments use
  `statsmodels.stats.multitest.multipletests` over the 28 raw p-values.
- **Ties:** if two pairs share the lowest raw p-value, the first pair in
  alphabetical order of its label (e.g. `APA/COP`) wins.
- **Sanity guard:** a pair test fails with an error if it has fewer than
  250 observations. This guards against broken data and is not a
  research parameter.
- **Peeking discipline:** trading-period (2021–2025) data is downloaded
  and passes the same validation, but is not analyzed, plotted, or tested
  during Phases 1–2. The out-of-sample stability diagnostic from ADR-002
  runs only after the owner has reviewed the Phase 2 results.
- **Parameters in code:** every value from ADR-001 to ADR-007 is defined
  once, in `src/config.py`, next to the ADR that justifies it.

**Amendment — 2026-09-23 (retrieval method):**

- **Original:** a single `yfinance.download` call for all 8 tickers.
- **New:** `yfinance.download` using a curl_cffi browser-impersonating
  session (a `requests` session if curl_cffi is unavailable), a 30-second
  request timeout, and up to 5 retries with exponential backoff (2, 4, 8,
  16, 32 s). Each retry re-requests only the tickers still missing. Any
  ticker still missing after that is fetched individually with
  `yfinance.Ticker(...).history()` (same chart endpoint, same
  `auto_adjust=False`, same dates) under the same retry policy. The
  download then fails unless every ticker has data starting within 7 days
  of 2016-01-01 and ending within 7 days of 2025-12-31, so a partial or
  truncated universe is never saved. The method used for each ticker is
  recorded in `data/dataset_manifest.json`.
- **Reason:** the first download attempt returned no data for any ticker
  (connection timeouts, and the cookie request to `fc.yahoo.com` timed
  out).
- **Results invalidated:** none. No data had been retrieved and no test
  had been run.

**Consequences:** The published results reproduce exactly only from the
same raw snapshot. Anyone who downloads again may get slightly different
revised prices, and can detect this by comparing the file hash.

---

## ADR-008: Continue with EOG/FANG although no pair survives multiple-testing correction

**Status:** Accepted — 2026-09-23 (owner decision, after reviewing the formation results)

**Context:** The ADR-002 weak-relationship rule triggered. EOG/FANG, the
pair with the lowest raw p-value, has raw p = 0.0051 but Holm-adjusted
p = 0.142, and no other pair does better after correction. The rule
required raising this with the owner before any backtest. It did not
allow the pair to be replaced.

**Decision:** **No pair survives multiple-testing correction. The project
continues with the best raw p-value pair, EOG/FANG (beta = 0.742), for
the out-of-sample test.** The pair, hedge ratio, and all other
pre-registered choices stay as they are. This failure is disclosed
prominently in the README and in every results document.

**Consequences:**

- The out-of-sample backtest tests a pair that was *found by searching*
  28 candidates. It does not test a relationship already shown to be
  statistically significant. Whatever the backtest shows, gross or net,
  cannot be credited to a cointegration relationship that the formation
  data established at the 5% level after correction.
- The out-of-sample stability check (ADR-002) is run next and reported
  whatever it shows. It is a diagnostic only and does not change the pair.
- A weak or unstable relationship is an acceptable finding. The pair will
  not be swapped for one that looks better in hindsight.

**Out-of-sample stability result (recorded 2026-09-23, from
[`docs/stability_check.md`](docs/stability_check.md)):** the same
Engle-Granger test on 2021-01-04 to 2025-12-31 (1,255 days) gives a
statistic of −2.638 against a 5% critical value of −3.341, **p = 0.223;
cointegration is not detected in the trading period.** The reverse
ordering gives p = 0.308. The OLS hedge ratio is stable (0.742 in the
formation period, 0.754 in the trading period). A supplementary check,
which was not pre-registered, runs an ADF test on the spread actually
traded (fixed formation alpha and beta) over the trading period: p =
0.080, mean 0.018, standard deviation 0.085. That is weak evidence of
mean reversion, not significant at 5%. As pre-registered, none of this
changes the pair or any parameter. It means the out-of-sample backtest
trades a relationship that could not be confirmed statistically in
either period after correcting for the search.

---

## ADR-009: Clarifying the z-score exit rule and signal mechanics

**Status:** Accepted — 2026-09-23 (recorded before the signal was run on any real data)

**Context:** ADR-003 says "close when `|z_t| <= 0.5`". Read literally, a
position stays open if z jumps across the exit band in one day, for
example from +2.3 to −0.9. The short-spread trade has then fully mean
reverted, but the literal rule keeps it open, and it would stay open
until z happened to land inside ±0.5. ADR-003 also leaves a few
mechanical details unstated. All of them are fixed here, before any
signal is computed on real data.

**Decision:**

| Item | ADR-003 wording | Implemented rule | Reason |
|---|---|---|---|
| Exit from short-spread | `\|z\| <= 0.5` | exit when `z <= +0.5` | Same as ADR-003 whenever z moves into the band; also exits when z overshoots past the band, which is the evident intent (the reversion is complete) |
| Exit from long-spread | `\|z\| <= 0.5` | exit when `z >= -0.5` | Same, mirrored |
| Exit and entry on the same day | not stated | exits are checked first; if z is then beyond the opposite entry threshold, the opposite position is entered the same day | Otherwise a valid entry signal would be ignored for one day with no reason |
| Rolling mean and standard deviation | not stated | computed directly from each window's 60 values; sample standard deviation (ddof = 1); no value until 60 observations are available; a window with standard deviation ≤ 1e-12 counts as zero variance | pandas' online rolling algorithm accumulates rounding error across the whole series (about 3e-8 on a constant window in testing), so z would depend slightly on data outside the window |
| Missing z (warm-up, or zero variance) | not stated | no new entry; an open position is held | A missing signal carries no information |
| Start of the trading period | not stated | flat on 2021-01-04, with no position carried in from the formation period; z at that date uses the previous 59 formation-period spread values, which is legitimately past data | The formation period is not traded |
| Output | not stated | target position decided at the close of day t: +1 long spread (long EOG, short FANG), −1 short spread, 0 flat. Execution at the close of t+1 and the forced final close are handled by the backtest (ADR-006) | Keeps signal timing separate from execution timing |

- **Original vs. new:** entry thresholds (±2.0), exit band (0.5), window
  (60), and the fixed formation hedge ratio are unchanged. Only the two
  cases ADR-003 did not cover are defined.
- **Results invalidated:** none. No signal had been computed on real data
  when this was recorded.

**Consequences:** In the overshoot case this rule closes positions no
later than the literal wording would, and usually sooner.

---

## ADR-010: Gross backtest accounting details, and freezing the gross result

**Status:** Accepted — 2026-09-23 (recorded before the backtest was run on any real data)

**Context:** ADR-006 fixes execution timing, capital, and position
sizing but leaves several accounting details open. These affect the
numbers, so they are fixed before the first run. The project's central
comparison also requires that the gross result cannot be adjusted after
the costed result has been seen.

**Decision — accounting (applies identically to the gross and net runs):**

| Item | Implemented rule | Reason |
|---|---|---|
| Execution | The target position decided at the close of day t (ADR-009) is executed at the close of day t+1 | ADR-006 |
| Leg sizing | $100,000 gross notional per trade: $100,000 / (1 + beta) in EOG and $100,000 × beta / (1 + beta) in FANG, with the formation beta = 0.7423 | ADR-006 |
| Share counts | Whole shares, rounded down, computed from the *unadjusted* close at execution: `floor(leg notional / Close)`. Held fixed until exit | Real orders are for whole shares at real prices. Phase 5 commissions are per share |
| P&L | Each leg's value moves with its *adjusted* close from the execution day: `invested × (AdjClose_t / AdjClose_exec)`, where `invested = shares × Close_exec`. Long legs gain and short legs lose from dividends through the adjustment | Total-return accounting from free data. The short leg pays dividends |
| Reversal | Closing one direction and opening the other on the same day counts as two trades (one exit, one entry) | Both would be real orders |
| End of the trading period | Any open position is closed at the close of 2025-12-31. A target set on the final day is not executed, and no new position is opened on the final day | ADR-003; a position opened and closed on the same close has no P&L but would incur costs |
| Capital and returns | $100,000, not compounded. Daily return = daily P&L / $100,000. Equity = $100,000 + cumulative P&L | ADR-006 |
| Sharpe ratio | mean(daily return) / std(daily return, ddof = 1) × √252 over *every* trading-period day, including flat days, with a 0% risk-free rate | ADR-006; excluding flat days would flatter the ratio |
| Max drawdown | Largest peak-to-trough fall of the equity curve, as a fraction of the peak | Standard |
| Win rate | Share of round-trip trades with P&L > 0. The forced final close counts as a trade | Stated so it is not ambiguous |
| Turnover | Total traded notional (both legs, entries and exits) / $100,000 / years | Needed to explain cost drag in Phase 5 |

**Decision — freezing the gross result:** the gross backtest is run and
recorded (`docs/results_gross.md` and `docs/results_gross.json`, with the
SHA-256 of the JSON written into this ADR) **before any cost model code
is written or run**. After that point the gross result, and every input
to it (pair, beta, thresholds, window, accounting rules above), may not
change because of what the net result shows. The net run must reuse the
identical executions and trades, and only subtract costs. If a genuine
bug is later found in the gross calculation, the fix is recorded as a
new ADR stating the original and corrected gross numbers side by side,
and both remain published.

**Consequences:** Whole-share rounding leaves each trade slightly below
$100,000 of gross notional. Total-return accounting from adjusted closes
approximates dividend reinvestment rather than modeling cash dividends
exactly.

**Frozen gross result (recorded 2026-09-23, before any cost model code
was written):** `docs/results_gross.json` SHA-256
`1acbfd35e8c899173a6e4cb355942cc5485bf01d5ac5d0bfc419d429746df853`.
Re-running `scripts/run_backtest_gross.py` on the same raw snapshot
reproduces this hash exactly.

| Metric (EOG/FANG, 2021-01-04 to 2025-12-31, gross) | Value |
|---|---:|
| Total P&L on $100,000 | +$3,253.41 (+3.25%) |
| Annualized return / volatility | 0.65% / 8.29% |
| Sharpe ratio | 0.08 |
| Max drawdown | −11.35% |
| Round-trip trades | 20 (1 closed at the end of the period) |
| Win rate | 60.0% |
| Average P&L per trade | +$162.67 |
| Average holding period | 28.1 trading days |
| Time in market | 44.7% |
| Turnover | 8.1× capital per year |

Verification: two trades (#18 and #20) were recomputed independently
from the raw prices and match to the cent. Every entry follows a close
with |z| ≥ 2.0, in the correct direction, one day earlier. Trade-level
P&L sums to daily P&L.

---

## ADR-011: [Template for future ADRs]

**Status:** Proposed / Accepted / Superseded / Rejected

**Context:** What situation forced this decision?

**Decision:** What was decided? If this changes an earlier decision:
original choice, new choice, reason, and which results are invalidated.

**Consequences:** What trade-offs does this create? Be honest.
