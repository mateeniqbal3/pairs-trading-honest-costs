"""Tests for src/costs.py. Cost amounts are checked by hand."""

import numpy as np
import pandas as pd
import pytest

from src.backtest import rebuild_from_trades, run_backtest
from src.costs import CostModel, apply_costs, borrow_costs, order_costs

MODEL = CostModel(half_spread_bps=2.0, slippage_bps=3.0, commission_per_share=0.005,
                  commission_min=1.0, borrow_rate_annual=0.003)


def execs(rows):
    return pd.DataFrame(rows, columns=["date", "trade_id", "kind", "ticker", "shares", "price",
                                       "notional"])


def test_default_model_matches_adr_004():
    assert CostModel() == MODEL


def test_order_costs_by_hand():
    d = pd.Timestamp("2021-01-04")
    out = order_costs(execs([
        (d, 1, "entry", "AAA", 100, 100.0, 10_000.0),  # commission 0.50 -> $1 minimum
        (d, 1, "entry", "BBB", -1_000, 50.0, 50_000.0),  # commission 1000 * 0.005 = $5
    ]), MODEL)
    assert out["spread_cost"].tolist() == pytest.approx([2.0, 10.0])  # 2 bps
    assert out["slippage_cost"].tolist() == pytest.approx([3.0, 15.0])  # 3 bps
    assert out["commission"].tolist() == pytest.approx([1.0, 5.0])
    assert out["order_cost"].tolist() == pytest.approx([6.0, 30.0])


def test_scaling_applies_to_every_component():
    zero = MODEL.scaled(0.0)
    assert all(v == 0 for v in vars(zero).values())
    double = MODEL.scaled(2.0)
    assert double.commission_min == 2.0 and double.borrow_rate_annual == pytest.approx(0.006)
    with pytest.raises(ValueError):
        MODEL.scaled(-1.0)


def test_borrow_charged_on_prior_close_short_value():
    idx = pd.bdate_range("2021-01-04", periods=4)
    short_value = pd.Series([0.0, 25_200.0, 25_200.0, 0.0], index=idx)
    borrow = borrow_costs(short_value, MODEL)
    daily = 25_200.0 * 0.003 / 252  # = $0.30 per night
    assert borrow.tolist() == pytest.approx([0.0, 0.0, daily, daily])


def small_backtest():
    idx = pd.bdate_range("2021-01-04", periods=8)
    close = pd.DataFrame({"YYY": [10, 10, 11, 12, 12, 11, 10, 10],
                          "XXX": [20, 20, 20, 19, 19, 20, 21, 21]}, index=idx, dtype=float)
    adj = close * np.linspace(0.97, 1.0, 8)[:, None]  # stand-in for dividend adjustment
    target = pd.Series([1, 1, 1, 0, -1, -1, -1, 0], index=idx)
    return run_backtest(target, adj, close, "YYY", "XXX", 1.0, 1_000.0), adj, close


def test_rebuild_from_trades_matches_the_backtest_exactly():
    result, adj, close = small_backtest()
    rebuilt = rebuild_from_trades(result.trades, adj, close, "YYY", "XXX")
    np.testing.assert_allclose(rebuilt.daily_pnl, result.daily["pnl"], rtol=0, atol=1e-9)
    np.testing.assert_allclose(rebuilt.trade_pnl.sort_index(), result.trades["pnl"], atol=1e-9)
    key = ["date", "trade_id", "kind", "ticker"]
    pd.testing.assert_frame_equal(
        rebuilt.executions.sort_values(key, ignore_index=True),
        result.executions.sort_values(key, ignore_index=True),
    )
    # short value = short shares x unadjusted close, on nights the trade is held
    expected = pd.Series(0.0, index=close.index)
    for tr in result.trades.itertuples():
        held = close.index[(close.index >= tr.entry_date) & (close.index < tr.exit_date)]
        for ticker in ("YYY", "XXX"):
            shares = getattr(tr, f"shares_{ticker}")
            if shares < 0:
                expected[held] += -shares * close.loc[held, ticker]
    np.testing.assert_allclose(rebuilt.short_value, expected)
    assert (rebuilt.short_value > 0).sum() == (result.daily["position"] != 0).sum()


def test_dividend_memo_splits_adjusted_minus_price_only_pnl():
    idx = pd.bdate_range("2021-01-04", periods=3)
    close = pd.DataFrame({"YYY": [10.0, 10.0, 10.0], "XXX": [20.0, 20.0, 20.0]}, index=idx)
    adj = pd.DataFrame({"YYY": [9.8, 9.8, 9.996], "XXX": [19.6, 19.6, 19.992]}, index=idx)
    trades = pd.DataFrame([{"trade_id": 1, "entry_date": idx[0], "exit_date": idx[2],
                            "shares_YYY": 50, "shares_XXX": -25}])
    rebuilt = rebuild_from_trades(trades, adj, close, "YYY", "XXX")
    assert rebuilt.dividends["long_leg"] == pytest.approx(500 * 0.02)  # received
    assert rebuilt.dividends["short_leg"] == pytest.approx(-500 * 0.02)  # paid
    assert rebuilt.short_value.tolist() == pytest.approx([500.0, 500.0, 0.0])


def test_zero_cost_net_equals_gross_and_trades_are_untouched():
    result, adj, close = small_backtest()
    rebuilt = rebuild_from_trades(result.trades, adj, close, "YYY", "XXX")
    trades_before = result.trades.copy()
    net = apply_costs(rebuilt.daily_pnl, rebuilt.trade_pnl, result.trades, rebuilt.executions,
                      rebuilt.short_value, MODEL.scaled(0.0))
    pd.testing.assert_series_equal(net.daily_pnl, rebuilt.daily_pnl.rename("pnl"))
    assert net.breakdown["total"] == 0.0
    pd.testing.assert_frame_equal(result.trades, trades_before)


def test_net_equals_gross_minus_costs_per_day_and_per_trade():
    result, adj, close = small_backtest()
    rebuilt = rebuild_from_trades(result.trades, adj, close, "YYY", "XXX")
    net = apply_costs(rebuilt.daily_pnl, rebuilt.trade_pnl, result.trades, rebuilt.executions,
                      rebuilt.short_value, MODEL)
    total_cost = net.breakdown["total"]
    assert total_cost > 0
    assert rebuilt.daily_pnl.sum() - net.daily_pnl.sum() == pytest.approx(total_cost)
    assert net.trade_pnl.sum() == pytest.approx(net.daily_pnl.sum())
    assert (net.trade_pnl < rebuilt.trade_pnl).all()
    orders = order_costs(rebuilt.executions, MODEL)
    assert net.breakdown["spread"] == pytest.approx(orders["notional"].sum() * 2e-4)
    assert net.breakdown["slippage"] == pytest.approx(orders["notional"].sum() * 3e-4)
