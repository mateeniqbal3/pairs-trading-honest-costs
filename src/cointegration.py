"""Engle-Granger cointegration tests across every candidate pair.

Every pair tested is kept in the output, not only the selected one, so the
multiple-testing disclosure (PROJECT.md section 7) can be made in full.
Test settings and the selection rule are fixed in DECISIONS.md ADR-002/007.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import coint

from src import config


@dataclass(frozen=True)
class EngleGrangerResult:
    statistic: float
    pvalue: float
    crit_1pct: float
    crit_5pct: float
    crit_10pct: float
    nobs: int


def _check_inputs(y: pd.Series, x: pd.Series, min_obs: int) -> None:
    if not y.index.equals(x.index):
        raise ValueError("y and x must share the same index")
    if y.isna().any() or x.isna().any():
        raise ValueError("y and x must not contain NaN")
    if len(y) < min_obs:
        raise ValueError(f"only {len(y)} observations; at least {min_obs} required")


def engle_granger(
    y: pd.Series, x: pd.Series, min_obs: int = config.MIN_OBSERVATIONS
) -> EngleGrangerResult:
    """Engle-Granger test with y as the dependent variable (constant, AIC lag choice)."""
    _check_inputs(y, x, min_obs)
    stat, pvalue, crit = coint(y, x, trend=config.EG_TREND, autolag=config.EG_AUTOLAG)
    return EngleGrangerResult(
        statistic=float(stat),
        pvalue=float(pvalue),
        crit_1pct=float(crit[0]),
        crit_5pct=float(crit[1]),
        crit_10pct=float(crit[2]),
        nobs=len(y),
    )


def hedge_ratio(
    y: pd.Series, x: pd.Series, min_obs: int = config.MIN_OBSERVATIONS
) -> tuple[float, float]:
    """OLS of y on a constant and x. Returns (alpha, beta)."""
    _check_inputs(y, x, min_obs)
    fit = sm.OLS(y.to_numpy(), sm.add_constant(x.to_numpy())).fit()
    alpha, beta = fit.params
    return float(alpha), float(beta)


def run_all_pair_tests(log_prices: pd.DataFrame, min_obs: int = config.MIN_OBSERVATIONS) -> pd.DataFrame:
    """Test every pair of columns; the alphabetically first ticker is the dependent variable.

    Returns one row per pair with the test statistic, raw p-value, Holm and
    Bonferroni adjusted p-values across all pairs tested, the formation
    hedge ratio, and the reverse-ordering p-value (reported, not used for
    selection). Rows are sorted by raw p-value, ties broken by pair label.
    """
    tickers = sorted(log_prices.columns)
    if len(tickers) < 2:
        raise ValueError("need at least two tickers")
    if log_prices.isna().any().any():
        raise ValueError("log prices must not contain NaN")

    rows = []
    for y_name, x_name in combinations(tickers, 2):
        y, x = log_prices[y_name], log_prices[x_name]
        forward = engle_granger(y, x, min_obs)
        reverse = engle_granger(x, y, min_obs)
        alpha, beta = hedge_ratio(y, x, min_obs)
        rows.append(
            {
                "pair": f"{y_name}/{x_name}",
                "y": y_name,
                "x": x_name,
                "nobs": forward.nobs,
                "eg_stat": forward.statistic,
                "crit_5pct": forward.crit_5pct,
                "p_raw": forward.pvalue,
                "alpha": alpha,
                "beta": beta,
                "p_raw_reverse": reverse.pvalue,
            }
        )

    results = pd.DataFrame(rows)
    results["p_holm"] = multipletests(results["p_raw"], method="holm")[1]
    results["p_bonferroni"] = multipletests(results["p_raw"], method="bonferroni")[1]
    results = results.sort_values(["p_raw", "pair"], kind="mergesort").reset_index(drop=True)
    results.insert(0, "rank", np.arange(1, len(results) + 1))
    return results


def select_pair(results: pd.DataFrame) -> pd.Series:
    """The pair with the lowest raw p-value; ties go to the alphabetically first label."""
    if results.empty:
        raise ValueError("no pair results to select from")
    ordered = results.sort_values(["p_raw", "pair"], kind="mergesort")
    return ordered.iloc[0]


def weak_relationship_flags(selected: pd.Series, alpha: float = config.SIGNIFICANCE_LEVEL) -> list[str]:
    """Reasons the ADR-002 weak-relationship rule is triggered (empty list if none)."""
    flags = []
    if selected["p_raw"] > alpha:
        flags.append(f"raw p-value {selected['p_raw']:.4f} > {alpha}")
    if selected["p_holm"] > alpha:
        flags.append(f"Holm-adjusted p-value {selected['p_holm']:.4f} > {alpha}")
    return flags
