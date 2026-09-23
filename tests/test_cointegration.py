"""Tests for src/cointegration.py."""

import numpy as np
import pandas as pd
import pytest

from src.cointegration import (
    engle_granger,
    hedge_ratio,
    run_all_pair_tests,
    select_pair,
    weak_relationship_flags,
)
from src.data import slice_period

N = 600


def random_walk(rng: np.random.Generator, n: int = N) -> np.ndarray:
    return np.cumsum(rng.normal(0, 0.02, n)) + 4.0


def cointegrated_pair(rng: np.random.Generator, alpha=0.5, beta=1.5, n: int = N):
    """y = alpha + beta * x + stationary AR(1) noise, with x a random walk."""
    x = random_walk(rng, n)
    noise = np.zeros(n)
    for t in range(1, n):
        noise[t] = 0.7 * noise[t - 1] + rng.normal(0, 0.01)
    return alpha + beta * x + noise, x


def as_series(values, name):
    return pd.Series(values, index=pd.bdate_range("2016-01-01", periods=len(values)), name=name)


class TestEngleGranger:
    def test_detects_cointegrated_pair(self):
        y, x = cointegrated_pair(np.random.default_rng(0))
        result = engle_granger(as_series(y, "Y"), as_series(x, "X"))
        assert result.pvalue < 0.01
        assert result.statistic < result.crit_1pct
        assert result.nobs == N

    def test_independent_random_walks_rarely_reject(self):
        rng = np.random.default_rng(1)
        rejections = sum(
            engle_granger(as_series(random_walk(rng), "Y"), as_series(random_walk(rng), "X")).pvalue
            < 0.05
            for _ in range(20)
        )
        assert rejections <= 4  # expected about 1 in 20 under the null

    def test_insufficient_observations_raises(self):
        y, x = cointegrated_pair(np.random.default_rng(0), n=100)
        with pytest.raises(ValueError, match="observations"):
            engle_granger(as_series(y, "Y"), as_series(x, "X"))

    def test_nan_raises(self):
        y, x = cointegrated_pair(np.random.default_rng(0))
        y[10] = np.nan
        with pytest.raises(ValueError, match="NaN"):
            engle_granger(as_series(y, "Y"), as_series(x, "X"))

    def test_mismatched_index_raises(self):
        y, x = cointegrated_pair(np.random.default_rng(0))
        x_series = as_series(x, "X")
        x_series.index = x_series.index + pd.Timedelta(days=1)
        with pytest.raises(ValueError, match="index"):
            engle_granger(as_series(y, "Y"), x_series)


def test_hedge_ratio_recovers_true_parameters():
    y, x = cointegrated_pair(np.random.default_rng(2), alpha=0.5, beta=1.5)
    alpha, beta = hedge_ratio(as_series(y, "Y"), as_series(x, "X"))
    assert beta == pytest.approx(1.5, abs=0.05)
    assert alpha == pytest.approx(0.5, abs=0.2)


def make_universe(seed: int = 3, n: int = N) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    y, x = cointegrated_pair(rng, n=n)
    frame = {"DDD": y, "BBB": x, "AAA": random_walk(rng, n), "CCC": random_walk(rng, n)}
    return pd.DataFrame(frame, index=pd.bdate_range("2016-01-01", periods=n))


class TestRunAllPairTests:
    def test_every_pair_tested_once_with_alphabetical_ordering(self):
        results = run_all_pair_tests(make_universe())
        assert len(results) == 6
        assert set(results["pair"]) == {
            "AAA/BBB", "AAA/CCC", "AAA/DDD", "BBB/CCC", "BBB/DDD", "CCC/DDD"
        }
        assert (results["y"] < results["x"]).all()
        assert list(results["rank"]) == list(range(1, 7))
        assert results["p_raw"].is_monotonic_increasing

    def test_planted_pair_ranks_first(self):
        results = run_all_pair_tests(make_universe())
        assert results.iloc[0]["pair"] == "BBB/DDD"

    def test_multiple_testing_adjustments(self):
        results = run_all_pair_tests(make_universe())
        m = len(results)
        p = results["p_raw"].to_numpy()  # already sorted ascending

        expected_bonf = np.minimum(1.0, p * m)
        expected_holm = np.minimum(1.0, np.maximum.accumulate(p * (m - np.arange(m))))
        np.testing.assert_allclose(results["p_bonferroni"], expected_bonf)
        np.testing.assert_allclose(results["p_holm"], expected_holm)
        assert (results["p_holm"] >= results["p_raw"]).all()
        assert (results["p_bonferroni"] >= results["p_holm"] - 1e-12).all()

    def test_reverse_ordering_reported(self):
        universe = make_universe()
        results = run_all_pair_tests(universe).set_index("pair")
        reverse = engle_granger(universe["DDD"], universe["BBB"])
        assert results.loc["BBB/DDD", "p_raw_reverse"] == pytest.approx(reverse.pvalue)

    def test_rejects_nan(self):
        universe = make_universe()
        universe.iloc[5, 0] = np.nan
        with pytest.raises(ValueError, match="NaN"):
            run_all_pair_tests(universe)

    def test_selection_ignores_data_after_formation_period(self):
        """Look-ahead guard: trading-period prices cannot change pair selection."""
        full = make_universe(n=900)
        formation_end = str(full.index[599].date())
        baseline = run_all_pair_tests(slice_period(full, "2016-01-01", formation_end))

        perturbed = full.copy()
        perturbed.iloc[600:] = perturbed.iloc[600:] * 5.0 + 3.0
        rerun = run_all_pair_tests(slice_period(perturbed, "2016-01-01", formation_end))

        pd.testing.assert_frame_equal(baseline, rerun)


class TestSelectPair:
    def test_lowest_raw_p_selected(self):
        results = pd.DataFrame({"pair": ["A/B", "A/C", "B/C"], "p_raw": [0.2, 0.01, 0.03]})
        assert select_pair(results)["pair"] == "A/C"

    def test_tie_broken_alphabetically(self):
        results = pd.DataFrame({"pair": ["B/C", "A/C", "A/B"], "p_raw": [0.01, 0.01, 0.5]})
        assert select_pair(results)["pair"] == "A/C"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            select_pair(pd.DataFrame({"pair": [], "p_raw": []}))


class TestWeakRelationshipFlags:
    def test_strong_pair_not_flagged(self):
        assert weak_relationship_flags(pd.Series({"p_raw": 0.001, "p_holm": 0.028})) == []

    def test_fails_holm_only(self):
        flags = weak_relationship_flags(pd.Series({"p_raw": 0.01, "p_holm": 0.28}))
        assert len(flags) == 1 and "Holm" in flags[0]

    def test_fails_both(self):
        assert len(weak_relationship_flags(pd.Series({"p_raw": 0.2, "p_holm": 1.0}))) == 2
