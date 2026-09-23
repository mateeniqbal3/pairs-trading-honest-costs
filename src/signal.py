"""Z-score mean-reversion signal on the selected pair's spread.

Rules are fixed in DECISIONS.md ADR-003 and clarified in ADR-009:

- spread ``s_t = log(Y_t) - beta * log(X_t) - alpha`` with the formation-period
  alpha and beta, never re-estimated;
- ``z_t`` uses a trailing window of exactly ``window`` observations ending at
  and including t (sample standard deviation), so it depends only on data
  available at the close of day t;
- positions come from a sequential state machine that only reads ``z`` up to
  the current day.

The output is the *target* position decided at the close of day t. Executing it
at the close of t+1 is the backtest's job (ADR-006), not this module's.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from src import config

LONG_SPREAD = 1  # long Y, short X: bet that the spread rises back toward its mean
SHORT_SPREAD = -1  # short Y, long X: bet that the spread falls back toward its mean
FLAT = 0
ZERO_STD_TOL = 1e-12  # exact two-pass std of a constant window is ~1e-17; real spreads ~1e-2


def compute_spread(log_y: pd.Series, log_x: pd.Series, alpha: float, beta: float) -> pd.Series:
    """Spread with fixed (formation-period) coefficients."""
    if not log_y.index.equals(log_x.index):
        raise ValueError("log_y and log_x must share the same index")
    return (log_y - beta * log_x - alpha).rename("spread")


def rolling_zscore(spread: pd.Series, window: int = config.ZSCORE_WINDOW) -> pd.Series:
    """Trailing z-score: (s_t - mean(s_{t-window+1..t})) / std(s_{t-window+1..t}).

    NaN until ``window`` observations are available, and wherever the window's
    standard deviation is zero.
    """
    if window < 2:
        raise ValueError("window must be at least 2")
    # Each window's mean and std are computed directly from its own values rather
    # than with pandas' online rolling algorithm, whose rounding error accumulates
    # across the whole series (e.g. ~1e-8 std on a constant window). A window
    # containing NaN gives NaN.
    values = spread.to_numpy(dtype=float)
    mean = np.full(len(values), np.nan)
    std = np.full(len(values), np.nan)
    if len(values) >= window:
        windows = sliding_window_view(values, window)
        mean[window - 1 :] = windows.mean(axis=1)
        std[window - 1 :] = windows.std(axis=1, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(std > ZERO_STD_TOL, (values - mean) / std, np.nan)
    return pd.Series(z, index=spread.index, name="zscore")


def positions_from_zscore(
    z: pd.Series, entry: float = config.ENTRY_Z, exit_: float = config.EXIT_Z
) -> pd.Series:
    """Target position at each close from a sequential entry/exit state machine.

    - Flat: enter SHORT_SPREAD when z >= entry, LONG_SPREAD when z <= -entry.
    - SHORT_SPREAD exits when z <= exit_; LONG_SPREAD exits when z >= -exit_.
    - Exits are checked before entries on the same day, so a jump across the
      band into the opposite entry zone closes and reverses the position.
    - NaN z: no new entry, any open position is held.
    Starts flat at the first index of ``z``.
    """
    if not 0 <= exit_ < entry:
        raise ValueError("require 0 <= exit_ < entry")
    values = z.to_numpy(dtype=float)
    out = np.zeros(len(values), dtype=int)
    position = FLAT
    for i, zi in enumerate(values):
        if not np.isnan(zi):
            if position == SHORT_SPREAD and zi <= exit_:
                position = FLAT
            elif position == LONG_SPREAD and zi >= -exit_:
                position = FLAT
            if position == FLAT:
                if zi >= entry:
                    position = SHORT_SPREAD
                elif zi <= -entry:
                    position = LONG_SPREAD
        out[i] = position
    return pd.Series(out, index=z.index, name="target_position")


def generate_signal(
    log_prices: pd.DataFrame,
    y: str,
    x: str,
    alpha: float,
    beta: float,
    trading_start: str,
    trading_end: str,
    window: int = config.ZSCORE_WINDOW,
    entry: float = config.ENTRY_Z,
    exit_: float = config.EXIT_Z,
) -> pd.DataFrame:
    """Spread, z-score, and target positions for the trading period.

    ``log_prices`` may include history before ``trading_start``; it is used only
    to fill the trailing z-score window (genuinely past data). Positions start
    flat on the first trading day, with nothing carried in from before it.
    """
    spread = compute_spread(log_prices[y], log_prices[x], alpha, beta)
    z = rolling_zscore(spread, window)
    frame = pd.concat([spread, z], axis=1)
    frame = frame.loc[pd.Timestamp(trading_start) : pd.Timestamp(trading_end)]
    if frame.empty:
        raise ValueError("no data in the trading period")
    frame["target_position"] = positions_from_zscore(frame["zscore"], entry, exit_)
    return frame
