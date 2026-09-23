"""Tests for src/data.py."""

import numpy as np
import pandas as pd
import pytest

from src.data import (
    align_prices,
    download_prices,
    load_raw,
    save_raw,
    slice_period,
    validate_prices,
)


def make_prices(n: int = 10, tickers=("AAA", "BBB", "CCC")) -> pd.DataFrame:
    idx = pd.bdate_range("2020-01-01", periods=n)
    data = {t: np.linspace(10 + i, 20 + i, n) for i, t in enumerate(tickers)}
    return pd.DataFrame(data, index=idx)


class TestValidatePrices:
    def test_accepts_clean_data_with_nan(self):
        prices = make_prices()
        prices.iloc[3, 1] = np.nan
        validate_prices(prices)

    def test_rejects_duplicate_dates(self):
        prices = make_prices()
        prices = pd.concat([prices, prices.iloc[[2]]]).sort_index()
        with pytest.raises(ValueError, match="duplicate"):
            validate_prices(prices)

    def test_rejects_unsorted_dates(self):
        with pytest.raises(ValueError, match="increasing"):
            validate_prices(make_prices().iloc[::-1])

    @pytest.mark.parametrize("bad", [0.0, -1.0])
    def test_rejects_non_positive(self, bad):
        prices = make_prices()
        prices.iloc[4, 0] = bad
        with pytest.raises(ValueError, match="non-positive"):
            validate_prices(prices)

    def test_rejects_infinite(self):
        prices = make_prices()
        prices.iloc[4, 0] = np.inf
        with pytest.raises(ValueError, match="infinite"):
            validate_prices(prices)

    def test_rejects_non_datetime_index(self):
        with pytest.raises(ValueError, match="DatetimeIndex"):
            validate_prices(make_prices().reset_index(drop=True))


class TestAlignPrices:
    def test_drops_dates_with_any_missing_ticker_without_filling(self):
        prices = make_prices()
        prices.iloc[2, 0] = np.nan
        prices.iloc[5, 2] = np.nan
        aligned, report = align_prices(prices, ("AAA", "BBB", "CCC"))

        assert len(aligned) == 8
        assert prices.index[2] not in aligned.index
        assert prices.index[5] not in aligned.index
        pd.testing.assert_frame_equal(aligned, prices.drop(prices.index[[2, 5]]))
        assert report.rows_dropped == 2
        assert report.missing_by_ticker == {"AAA": 1, "BBB": 0, "CCC": 1}

    def test_selects_and_orders_requested_tickers(self):
        aligned, _ = align_prices(make_prices(), ("CCC", "AAA"))
        assert list(aligned.columns) == ["CCC", "AAA"]

    def test_missing_ticker_raises(self):
        with pytest.raises(ValueError, match="missing"):
            align_prices(make_prices(), ("AAA", "ZZZ"))

    def test_no_common_dates_raises(self):
        prices = make_prices(n=4)
        prices.iloc[:2, 0] = np.nan
        prices.iloc[2:, 1] = np.nan
        with pytest.raises(ValueError, match="no dates"):
            align_prices(prices, ("AAA", "BBB"))


class TestSlicePeriod:
    def test_both_endpoints_inclusive(self):
        prices = make_prices(n=10)
        start, end = prices.index[2], prices.index[6]
        out = slice_period(prices, str(start.date()), str(end.date()))
        assert out.index[0] == start
        assert out.index[-1] == end
        assert len(out) == 5

    def test_start_after_end_raises(self):
        with pytest.raises(ValueError):
            slice_period(make_prices(), "2020-02-01", "2020-01-01")


def test_raw_round_trip(tmp_path):
    prices = make_prices(tickers=("AAA", "BBB"))
    raw = pd.concat({"Close": prices, "Adj Close": prices * 0.9}, axis=1)
    raw.index.name = "Date"
    path = tmp_path / "raw.csv"
    save_raw(raw, path)
    loaded = load_raw(path)
    pd.testing.assert_frame_equal(loaded, raw, check_freq=False)


START, END = "2020-01-01", "2020-03-31"
DATES = pd.bdate_range("2020-01-01", "2020-03-31")


def bulk_frame(tickers, dates=DATES, nan_tickers=()):
    cols = pd.MultiIndex.from_product([["Adj Close", "Close", "Open"], list(tickers)])
    frame = pd.DataFrame(1.0, index=dates, columns=cols)
    for t in nan_tickers:
        frame.loc[:, (slice(None), t)] = np.nan
    return frame


def history_frame(dates=DATES):
    idx = dates.tz_localize("America/New_York")
    return pd.DataFrame({"Open": 1.0, "Close": 2.0, "Adj Close": 1.5, "Volume": 10}, index=idx)


class FakeYF:
    """Stand-in for the yfinance module: scripted responses, records every call."""

    def __init__(self, bulk_responses, history_ok=()):
        self.bulk_responses = list(bulk_responses)
        self.history_ok = set(history_ok)
        self.bulk_calls, self.history_calls = [], []

    def download(self, tickers, **kwargs):
        self.bulk_calls.append((list(tickers), kwargs))
        response = self.bulk_responses.pop(0) if self.bulk_responses else None
        if isinstance(response, Exception):
            raise response
        return response(tickers) if callable(response) else response

    def Ticker(self, ticker, session=None):  # noqa: N802 - mirrors the yfinance API
        fake = self

        class _T:
            def history(self, **kwargs):
                fake.history_calls.append((ticker, kwargs))
                if ticker not in fake.history_ok:
                    raise ConnectionError("timeout")
                return history_frame()

        return _T()


@pytest.fixture
def fake_yf(monkeypatch):
    import sys

    def install(fake):
        monkeypatch.setitem(sys.modules, "yfinance", fake)
        return fake

    return install


def no_sleep(_seconds):
    pass


def test_download_arguments_and_sources(fake_yf):
    fake = fake_yf(FakeYF([bulk_frame]))
    out, sources = download_prices(["AAA", "BBB"], START, END, sleep=no_sleep)

    tickers, kwargs = fake.bulk_calls[0]
    assert tickers == ["AAA", "BBB"]
    assert kwargs["end"] == "2020-04-01"  # yfinance end is exclusive
    assert kwargs["start"] == START
    assert kwargs["auto_adjust"] is False
    assert kwargs["timeout"] == 30
    assert kwargs["session"] is not None
    assert list(out.columns) == [
        ("Close", "AAA"), ("Close", "BBB"), ("Adj Close", "AAA"), ("Adj Close", "BBB")
    ]
    assert all(v.startswith("yf.download") for v in sources.values())


def test_retries_bulk_download_for_missing_tickers_only(fake_yf):
    fake = fake_yf(
        FakeYF([ConnectionError("timeout"), lambda t: bulk_frame(t, nan_tickers=["BBB"]), bulk_frame])
    )
    sleeps = []
    out, sources = download_prices(["AAA", "BBB"], START, END, sleep=sleeps.append)

    assert [c[0] for c in fake.bulk_calls] == [["AAA", "BBB"], ["AAA", "BBB"], ["BBB"]]
    assert sleeps == [2.0, 4.0]
    assert out[("Adj Close", "BBB")].notna().all()
    assert set(sources) == {"AAA", "BBB"}


def test_falls_back_to_ticker_history(fake_yf):
    bulk_fail = [lambda t: bulk_frame(t, nan_tickers=["BBB"])] + [None] * 5
    fake = fake_yf(FakeYF(bulk_fail, history_ok={"BBB"}))
    out, sources = download_prices(["AAA", "BBB"], START, END, retries=5, sleep=no_sleep)

    assert len(fake.bulk_calls) == 6  # 1 attempt + 5 retries
    assert sources["AAA"].startswith("yf.download")
    assert sources["BBB"].startswith("yf.Ticker.history")
    ticker, kwargs = fake.history_calls[0]
    assert ticker == "BBB" and kwargs["auto_adjust"] is False and kwargs["timeout"] == 30
    assert out[("Adj Close", "BBB")].eq(1.5).all()
    assert out.index.tz is None
    assert out.index[0] == pd.Timestamp("2020-01-01")


def test_raises_when_every_method_fails(fake_yf):
    fake = fake_yf(FakeYF([ConnectionError("down")] * 6))
    with pytest.raises(RuntimeError, match="AAA"):
        download_prices(["AAA"], START, END, retries=5, sleep=no_sleep)
    assert len(fake.bulk_calls) == 6
    assert len(fake.history_calls) == 6


def test_truncated_history_raises(fake_yf):
    late = pd.bdate_range("2020-02-15", "2020-03-31")
    fake_yf(FakeYF([lambda t: bulk_frame(t, dates=late)]))
    with pytest.raises(RuntimeError, match="incomplete"):
        download_prices(["AAA"], START, END, sleep=no_sleep)
