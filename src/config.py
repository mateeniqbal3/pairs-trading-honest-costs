"""Pre-registered research parameters.

Every value here was fixed in DECISIONS.md before any data was downloaded.
Changing one is a research decision: record it as a new ADR (original value,
new value, reason, which results are invalidated) before editing this file.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PRICES_PATH = PROJECT_ROOT / "data" / "raw" / "prices_raw.csv"
MANIFEST_PATH = PROJECT_ROOT / "data" / "dataset_manifest.json"
PAIR_TESTS_PATH = PROJECT_ROOT / "docs" / "pair_selection.md"

# ADR-001: candidate universe and periods (inclusive dates).
UNIVERSE: tuple[str, ...] = ("XOM", "CVX", "COP", "EOG", "OXY", "DVN", "APA", "FANG")
SAMPLE_START = "2016-01-01"
SAMPLE_END = "2025-12-31"
FORMATION_START = "2016-01-01"
FORMATION_END = "2020-12-31"
TRADING_START = "2021-01-01"
TRADING_END = "2025-12-31"

# ADR-002 / ADR-007: cointegration test and selection.
EG_TREND = "c"
EG_AUTOLAG = "aic"
SIGNIFICANCE_LEVEL = 0.05
MIN_OBSERVATIONS = 250  # sanity guard against broken data, not a research parameter

# ADR-003 / ADR-009: spread z-score signal.
ZSCORE_WINDOW = 60
ENTRY_Z = 2.0
EXIT_Z = 0.5

# ADR-004 / ADR-011: transaction cost model (per leg, per order; unchanged since pre-registration).
HALF_SPREAD_BPS = 2.0
SLIPPAGE_BPS = 3.0
COMMISSION_PER_SHARE = 0.005
COMMISSION_MIN = 1.0
BORROW_RATE_ANNUAL = 0.003
COST_MULTIPLIERS = (0.0, 0.5, 1.0, 2.0, 3.0)  # 1.0 is the headline net result
