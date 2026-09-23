"""Tests for src/backtest.py. Scenarios are small enough to verify by hand."""

import math

import numpy as np
import pandas as pd
import pytest

from src.backtest import compute_metrics, executed_positions, max_drawdown, run_backtest

CAPITAL = 1_000.0


def frame(y_prices, x_prices):
    idx = pd.bdate_range("2021-01-04", periods=len(y_prices))
    return pd.DataFrame({"YYY": y_prices, "XXX": x_prices}, index=idx, dtype=float)


def target(values, index):
    return pd.Series(values, index=index, dtype=int)


def run(tgt, close, adj=None, beta=1.0):
    adj = close if adj is None else adj
    return run_backtest(target(tgt, close.index), adj, close, "YYY", "XXX", beta, CAPITAL)


# --- execution timing -----------------------------------------------------------------


def test_executed_position_is_previous_target_and_final_day_flat():
    idx = pd.bdate_range("2021-01-04", periods=5)
    held = executed_positions(target([1, 1, -1, 1, 1], idx))
    assert held.tolist() == [0, 1, 1, -1, 0]


# --- hand-computed round trip -----------------------------------------------------------


def test_long_spread_round_trip_pnl_and_executions():
    close = frame([10, 10, 10, 12, 12, 12], [20, 20, 20, 20, 18, 18])
    result = run([0, 1, 1, 1, 0, 0], close)

    # target set at close of day 1 -> entered at close of day 2 (one-day lag)
    ex = result.executions
    entry = ex[ex["kind"] == "entry"].set_index("ticker")
    assert (entry["date"] == close.index[2]).all()
    assert entry.loc["YYY", "shares"] == 50  # floor(500 / 10), long Y
    assert entry.loc["XXX", "shares"] == -25  # floor(500 / 20), short X
    exit_ = ex[ex["kind"] == "exit"].set_index("ticker")
    assert (exit_["date"] == close.index[5]).all()
    assert exit_.loc["YYY", "shares"] == -50 and exit_.loc["XXX", "shares"] == 25
    assert exit_.loc["YYY", "notional"] == 600 and exit_.loc["XXX", "notional"] == 450

    # day 3: Y 10 -> 12 on 50 shares = +100; day 4: short X 20 -> 18 on 25 shares = +50
    assert result.daily["pnl"].tolist() == [0, 0, 0, 100, 50, 0]
    assert result.daily["position"].tolist() == [0, 0, 1, 1, 1, 0]
    assert result.daily["equity"].iloc[-1] == 1_150

    trade = result.trades.iloc[0]
    assert trade["pnl"] == 150 and trade["holding_days"] == 3
    assert trade["direction"] == 1 and not trade["forced_close"]
    assert trade["entry_notional"] == 1_000


def test_short_spread_signs():
    close = frame([10, 10, 8, 8], [20, 20, 20, 20])
    result = run([-1, -1, -1, 0], close)
    shares = result.executions.query("kind == 'entry'").set_index("ticker")["shares"]
    assert shares["YYY"] == -50 and shares["XXX"] == 25
    assert result.trades["pnl"].iloc[0] == 100  # short 50 Y from 10 to 8


def test_negative_beta_puts_both_legs_on_the_same_side():
    close = frame([10, 10, 10], [20, 20, 20])
    result = run([1, 1, 1], close, beta=-1.0)
    shares = result.executions.query("kind == 'entry'").set_index("ticker")["shares"]
    assert shares["YYY"] > 0 and shares["XXX"] > 0


def test_share_counts_round_down_using_unadjusted_close():
    close = frame([30, 30, 30], [7, 7, 7])
    adj = close * 0.5  # adjusted prices must not affect share counts
    result = run([1, 1, 1], close, adj=adj, beta=1.0)
    shares = result.executions.query("kind == 'entry'").set_index("ticker")["shares"]
    assert shares["YYY"] == math.floor(500 / 30)  # 16
    assert shares["XXX"] == -math.floor(500 / 7)  # -71


def test_pnl_follows_adjusted_close():
    """Unadjusted price flat but adjusted price up 2% (a dividend): the long leg earns it."""
    close = frame([10, 10, 10, 10], [20, 20, 20, 20])
    adj = frame([9.8, 9.8, 9.8, 9.996], [20, 20, 20, 20])
    result = run([1, 1, 1, 0], close, adj=adj)
    # entered at close of day 1; invested 50 * 10 = 500 in Y; day 3 adjusted return
    # 9.996 / 9.8 - 1 = 2% -> +10 (X unchanged)
    assert result.daily["pnl"].tolist() == pytest.approx([0.0, 0.0, 0.0, 10.0])


# --- reversals and the end of the period ---------------------------------------------------


def test_reversal_is_two_trades_on_the_same_day():
    close = frame([10] * 5, [20] * 5)
    result = run([-1, 1, 1, 1, 1], close)
    assert len(result.trades) == 2
    t1, t2 = result.trades.iloc[0], result.trades.iloc[1]
    assert t1["direction"] == -1 and t1["exit_date"] == close.index[2]
    assert t2["direction"] == 1 and t2["entry_date"] == close.index[2]
    assert len(result.executions.query("date == @close.index[2]")) == 4  # exit + entry legs


def test_open_position_is_force_closed_on_the_final_day():
    close = frame([10, 10, 11, 12], [20, 20, 20, 20])
    result = run([1, 1, 1, 1], close)
    trade = result.trades.iloc[0]
    assert trade["exit_date"] == close.index[-1] and trade["forced_close"]
    assert result.daily["position"].iloc[-1] == 0
    assert trade["pnl"] == 50 * 2


def test_signal_exit_on_final_day_is_not_flagged_forced():
    close = frame([10, 10, 10, 10], [20, 20, 20, 20])
    result = run([1, 1, 0, 0], close)  # held: [0, 1, 1, 0] -> the signal itself exits
    assert not result.trades["forced_close"].iloc[0]


def test_no_position_opened_on_the_final_day():
    close = frame([10] * 5, [20] * 5)
    result = run([0, 0, 0, 1, 1], close)
    assert result.trades.empty and result.executions.empty


def test_flat_target_means_no_trades_and_zero_pnl():
    close = frame([10, 11, 9, 12], [20, 19, 22, 18])
    result = run([0, 0, 0, 0], close)
    assert result.trades.empty
    assert (result.daily["pnl"] == 0).all()


# --- look-ahead ------------------------------------------------------------------------


def test_future_prices_do_not_change_past_pnl():
    rng = np.random.default_rng(0)
    close = frame(10 + rng.normal(0, 0.1, 30).cumsum(), 20 + rng.normal(0, 0.1, 30).cumsum())
    tgt = [0] * 5 + [1] * 10 + [0] * 5 + [-1] * 10
    base = run(tgt, close)
    shocked = close.copy()
    shocked.iloc[20:] *= 3.0
    rerun = run(tgt, shocked)
    pd.testing.assert_frame_equal(base.daily.iloc[:20], rerun.daily.iloc[:20])


# --- input validation ------------------------------------------------------------------


def test_invalid_inputs():
    close = frame([10, 10, 10], [20, 20, 20])
    with pytest.raises(ValueError, match="-1, 0, or"):
        run([0, 2, 0], close)
    with pytest.raises(ValueError, match="index"):
        run_backtest(target([0, 1, 0], close.index), close.iloc[:2], close, "YYY", "XXX", 1.0)
    bad = close.copy()
    bad.iloc[1, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        run([0, 1, 0], bad)
    with pytest.raises(ValueError, match="beta"):
        run([0, 1, 0], close, beta=0.0)


# --- metrics ---------------------------------------------------------------------------


def test_max_drawdown():
    assert max_drawdown(pd.Series([100.0, 110.0, 99.0, 120.0, 108.0])) == pytest.approx(-0.1)
    assert max_drawdown(pd.Series([100.0, 101.0, 102.0])) == 0.0


def test_compute_metrics_by_hand():
    pnl = pd.Series([0.0, 100.0, -50.0, 50.0])
    trades = pd.DataFrame({"pnl": [120.0, -20.0], "holding_days": [2, 4]})
    executions = pd.DataFrame({"notional": [500.0, 500.0, 600.0, 450.0]})
    m = compute_metrics(pnl, trades, executions, capital=1_000.0)

    r = pnl / 1_000.0
    assert m["total_pnl"] == 100.0
    assert m["total_return"] == pytest.approx(0.1)
    assert m["annualized_return"] == pytest.approx(r.mean() * 252)
    assert m["sharpe_ratio"] == pytest.approx(r.mean() / r.std(ddof=1) * math.sqrt(252))
    assert m["max_drawdown"] == pytest.approx(-50 / 1_100)
    assert m["n_trades"] == 2 and m["win_rate"] == 0.5
    assert m["avg_trade_pnl"] == 50.0 and m["avg_holding_days"] == 3.0
    assert m["turnover_per_year"] == pytest.approx(2_050 / 1_000 / (4 / 252))


def test_metrics_with_no_trades():
    m = compute_metrics(pd.Series([0.0, 0.0]), pd.DataFrame({"pnl": [], "holding_days": []}),
                        pd.DataFrame({"notional": []}))
    assert m["n_trades"] == 0 and math.isnan(m["sharpe_ratio"]) and math.isnan(m["win_rate"])
