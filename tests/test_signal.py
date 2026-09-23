"""Tests for src/signal.py, including the look-ahead check required by PROJECT.md section 7."""

import numpy as np
import pandas as pd
import pytest

from src.signal import (
    FLAT,
    LONG_SPREAD,
    SHORT_SPREAD,
    compute_spread,
    generate_signal,
    positions_from_zscore,
    rolling_zscore,
)

WINDOW = 60


def synthetic_log_prices(n: int = 400, seed: int = 0) -> pd.DataFrame:
    """Log prices of a cointegrated pair: y = 1 + 0.75 x + AR(1) noise."""
    rng = np.random.default_rng(seed)
    x = np.cumsum(rng.normal(0, 0.02, n)) + 4.0
    noise = np.zeros(n)
    for t in range(1, n):
        noise[t] = 0.9 * noise[t - 1] + rng.normal(0, 0.02)
    idx = pd.bdate_range("2020-06-01", periods=n)
    return pd.DataFrame({"YYY": 1.0 + 0.75 * x + noise, "XXX": x}, index=idx)


def z_series(values) -> pd.Series:
    return pd.Series(values, index=pd.bdate_range("2021-01-04", periods=len(values)), dtype=float)


def signal_for(log_prices: pd.DataFrame, trading_start: str) -> pd.DataFrame:
    return generate_signal(
        log_prices, "YYY", "XXX", alpha=1.0, beta=0.75,
        trading_start=trading_start, trading_end=str(log_prices.index[-1].date()),
    )


# --- look-ahead ------------------------------------------------------------------------


@pytest.mark.parametrize("modified", [WINDOW, 150, 250, 399])
@pytest.mark.parametrize("column", ["YYY", "XXX"])
def test_no_lookahead_in_zscore(modified, column):
    """Changing one future price to an extreme value leaves every earlier z-score and
    target position identical; values at and after the change may differ."""
    prices = synthetic_log_prices()
    trading_start = str(prices.index[WINDOW].date())
    baseline = signal_for(prices, trading_start)

    shocked = prices.copy()
    shocked.iloc[modified, shocked.columns.get_loc(column)] += 5.0  # a ~150x price move
    rerun = signal_for(shocked, trading_start)

    cutoff = prices.index[modified]
    before = baseline.index < cutoff
    pd.testing.assert_frame_equal(baseline[before], rerun[before])
    assert not np.isclose(baseline.loc[cutoff, "zscore"], rerun.loc[cutoff, "zscore"])


def test_zscore_matches_manual_trailing_window():
    spread = pd.Series(np.random.default_rng(1).normal(size=200))
    z = rolling_zscore(spread, WINDOW)
    for t in (WINDOW - 1, 100, 199):
        window = spread.iloc[t - WINDOW + 1 : t + 1]
        expected = (spread.iloc[t] - window.mean()) / window.std(ddof=1)
        assert z.iloc[t] == pytest.approx(expected)


def test_zscore_depends_only_on_values_inside_its_window():
    """Changing data older than the window must not change z at all (not even by
    floating-point drift, which online rolling algorithms accumulate)."""
    rng = np.random.default_rng(4)
    tail = rng.normal(0, 0.05, 120)
    a = pd.Series(np.r_[rng.normal(0, 1e3, 300), tail])
    b = pd.Series(np.r_[rng.normal(0, 1e-3, 300), tail])
    za, zb = rolling_zscore(a, WINDOW), rolling_zscore(b, WINDOW)
    np.testing.assert_array_equal(za.iloc[300 + WINDOW - 1 :], zb.iloc[300 + WINDOW - 1 :])


def test_zscore_nan_until_full_window_and_for_zero_variance():
    spread = pd.Series(np.r_[np.random.default_rng(2).normal(size=80), np.zeros(70)])
    z = rolling_zscore(spread, WINDOW)
    assert z.iloc[: WINDOW - 1].isna().all()
    assert z.iloc[WINDOW - 1 : 80].notna().all()
    assert z.iloc[-5:].isna().all()  # last 60 values are all zero: std = 0


def test_rolling_zscore_rejects_tiny_window():
    with pytest.raises(ValueError):
        rolling_zscore(pd.Series([1.0, 2.0]), window=1)


def test_compute_spread():
    idx = pd.bdate_range("2021-01-04", periods=3)
    y, x = pd.Series([2.0, 2.5, 3.0], idx), pd.Series([1.0, 2.0, 4.0], idx)
    spread = compute_spread(y, x, alpha=0.5, beta=0.75)
    np.testing.assert_allclose(spread, [0.75, 0.5, -0.5])


def test_compute_spread_index_mismatch():
    y = pd.Series([1.0, 2.0], pd.bdate_range("2021-01-04", periods=2))
    x = pd.Series([1.0, 2.0], pd.bdate_range("2021-01-05", periods=2))
    with pytest.raises(ValueError):
        compute_spread(y, x, 0.0, 1.0)


# --- entry / exit rules (ADR-003, ADR-009) --------------------------------------------


@pytest.mark.parametrize(
    "zs, expected",
    [
        # short spread: enter at >= 2.0 (inclusive), hold, exit at <= 0.5 (inclusive)
        ([0.0, 2.0, 1.0, 0.6, 0.5, 0.0], [0, -1, -1, -1, 0, 0]),
        # long spread mirrored
        ([0.0, -2.0, -1.0, -0.6, -0.5, 0.0], [0, 1, 1, 1, 0, 0]),
        # just inside the entry threshold: no trade
        ([1.999, -1.999, 0.0], [0, 0, 0]),
        # overshoot across the band closes the trade (ADR-009)
        ([2.3, -0.9, -1.5], [-1, 0, 0]),
        # jump into the opposite entry zone closes and reverses the same day (ADR-009)
        ([2.3, -2.1, -1.0, -0.4], [-1, 1, 1, 0]),
        # NaN: hold an open position, never enter on it
        ([2.5, np.nan, 1.0, 0.2], [-1, -1, -1, 0]),
        ([np.nan, np.nan, 0.0], [0, 0, 0]),
        # divergence keeps the position open (no stop-loss, ADR-003)
        ([2.0, 3.0, 5.0, 8.0], [-1, -1, -1, -1]),
    ],
)
def test_state_machine(zs, expected):
    positions = positions_from_zscore(z_series(zs), entry=2.0, exit_=0.5)
    assert positions.tolist() == expected


def test_position_constants():
    assert (LONG_SPREAD, SHORT_SPREAD, FLAT) == (1, -1, 0)


@pytest.mark.parametrize("entry, exit_", [(2.0, 2.0), (2.0, -0.1), (0.5, 1.0)])
def test_invalid_thresholds(entry, exit_):
    with pytest.raises(ValueError):
        positions_from_zscore(z_series([0.0]), entry=entry, exit_=exit_)


# --- trading-period mechanics ---------------------------------------------------------


def test_warmup_uses_prior_history_and_output_is_trading_period_only():
    prices = synthetic_log_prices()
    trading_start = prices.index[100]
    sig = signal_for(prices, str(trading_start.date()))
    assert sig.index[0] == trading_start
    assert sig["zscore"].notna().all()  # the window is filled from pre-trading history


def test_starts_flat_with_no_position_carried_in():
    """A divergence just before the trading period does not create a position by itself."""
    n = 200
    idx = pd.bdate_range("2020-06-01", periods=n)
    rng = np.random.default_rng(3)
    x = np.full(n, 4.0)
    y = 1.0 + 0.75 * x + rng.normal(0, 0.01, n)
    y[149] += 0.2  # large positive spread shock on the last pre-trading day
    prices = pd.DataFrame({"YYY": y, "XXX": x}, index=idx)

    full = signal_for(prices, str(idx[0].date()))
    assert full.loc[idx[149], "target_position"] == SHORT_SPREAD  # it would have traded

    sig = signal_for(prices, str(idx[150].date()))
    first_z = sig["zscore"].iloc[0]
    assert abs(first_z) < 2.0
    assert sig["target_position"].iloc[0] == FLAT


def test_empty_trading_period_raises():
    prices = synthetic_log_prices(n=100)
    with pytest.raises(ValueError, match="trading period"):
        generate_signal(prices, "YYY", "XXX", 1.0, 0.75, "2030-01-01", "2030-12-31")
