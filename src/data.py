"""Price data retrieval, validation, alignment, and period slicing.

Rules are fixed in DECISIONS.md ADR-007: adjusted closes, keep only dates on
which every ticker has a price, no filling or repair, fail loudly on bad data.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PRICE_FIELDS = ("Close", "Adj Close")


@dataclass(frozen=True)
class AlignmentReport:
    """What alignment removed, so it can be disclosed rather than hidden."""

    rows_before: int
    rows_after: int
    missing_by_ticker: dict[str, int]

    @property
    def rows_dropped(self) -> int:
        return self.rows_before - self.rows_after


def make_session() -> tuple[object, str]:
    """A curl_cffi browser-impersonating session if installed, else a requests session."""
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        import requests

        return requests.Session(), "requests"
    return cffi_requests.Session(impersonate="chrome"), "curl_cffi"


def _normalize_index(frame: pd.DataFrame) -> pd.DataFrame:
    idx = pd.DatetimeIndex(frame.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)  # keep the exchange-local calendar date
    frame = frame.copy()
    frame.index = idx.normalize()
    frame.index.name = "Date"
    return frame


def _tickers_with_data(frame: pd.DataFrame | None, tickers) -> list[str]:
    if frame is None or frame.empty:
        return []
    return [
        t for t in tickers
        if all((f, t) in frame.columns for f in PRICE_FIELDS) and frame[("Adj Close", t)].notna().any()
    ]


def _bulk_download(yf, tickers, start, end_exclusive, session, timeout) -> pd.DataFrame | None:
    return yf.download(
        list(tickers),
        start=start,
        end=end_exclusive,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="column",
        multi_level_index=True,
        threads=False,
        timeout=timeout,
        session=session,
    )


def _ticker_history(yf, ticker, start, end_exclusive, session, timeout) -> pd.DataFrame:
    hist = yf.Ticker(ticker, session=session).history(
        start=start,
        end=end_exclusive,
        interval="1d",
        auto_adjust=False,
        actions=False,
        timeout=timeout,
        raise_errors=True,
    )
    if hist is None or hist.empty or "Adj Close" not in hist.columns:
        raise RuntimeError(f"history() returned no Adj Close for {ticker}")
    return pd.concat({f: hist[[f]].rename(columns={f: ticker}) for f in PRICE_FIELDS}, axis=1)


def check_coverage(prices: pd.DataFrame, tickers, start: str, end_inclusive: str,
                   tolerance_days: int = 7) -> None:
    """Raise if any ticker's Adj Close history starts late or ends early (truncated download)."""
    lo = pd.Timestamp(start) + pd.Timedelta(days=tolerance_days)
    hi = pd.Timestamp(end_inclusive) - pd.Timedelta(days=tolerance_days)
    problems = []
    for t in tickers:
        valid = prices[("Adj Close", t)].dropna().index
        if valid.empty or valid[0] > lo or valid[-1] < hi:
            span = "no data" if valid.empty else f"{valid[0].date()}..{valid[-1].date()}"
            problems.append(f"{t} ({span})")
    if problems:
        raise RuntimeError(f"incomplete price history for: {', '.join(problems)}")


def download_prices(
    tickers: list[str] | tuple[str, ...],
    start: str,
    end_inclusive: str,
    timeout: int = 30,
    retries: int = 5,
    backoff_s: float = 2.0,
    sleep=time.sleep,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Download daily Close and Adj Close from yfinance, with retries and a fallback.

    Each ticker is tried with ``yf.download`` (one initial attempt plus
    ``retries`` retries, exponential backoff). Tickers still missing are
    then fetched one at a time with ``yf.Ticker(...).history()`` under the
    same retry policy. Both use Yahoo's chart endpoint with
    ``auto_adjust=False``. If any ticker is still missing or truncated, this
    raises; it never returns a partial universe.

    Returns a frame with two-level columns (field, ticker) and a mapping of
    ticker -> retrieval method, for the dataset manifest. yfinance treats
    ``end`` as exclusive, so one day is added to ``end_inclusive``.
    """
    import yfinance as yf  # imported lazily: only this function needs the network

    session, session_kind = make_session()
    end_exclusive = (pd.Timestamp(end_inclusive) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    attempts = retries + 1
    pieces: list[pd.DataFrame] = []
    sources: dict[str, str] = {}

    pending = list(tickers)
    for attempt in range(attempts):
        try:
            raw = _bulk_download(yf, pending, start, end_exclusive, session, timeout)
        except Exception:  # network errors surface in many forms; retry all of them
            raw = None
        got = _tickers_with_data(raw, pending)
        if got:
            pieces.append(_normalize_index(raw.loc[:, [(f, t) for f in PRICE_FIELDS for t in got]]))
            sources.update({t: f"yf.download ({session_kind})" for t in got})
            pending = [t for t in pending if t not in got]
        if not pending:
            break
        if attempt < attempts - 1:
            sleep(backoff_s * 2**attempt)

    for ticker in list(pending):
        for attempt in range(attempts):
            try:
                hist = _ticker_history(yf, ticker, start, end_exclusive, session, timeout)
            except Exception:
                if attempt < attempts - 1:
                    sleep(backoff_s * 2**attempt)
                continue
            pieces.append(_normalize_index(hist))
            sources[ticker] = f"yf.Ticker.history ({session_kind})"
            pending.remove(ticker)
            break

    if pending:
        raise RuntimeError(f"no price data after {attempts} attempts per method for: {pending}")

    combined = pd.concat(pieces, axis=1).sort_index()
    out = combined.loc[:, [(f, t) for f in PRICE_FIELDS for t in tickers]]
    check_coverage(out, tickers, start, end_inclusive)
    return out, sources


def save_raw(prices: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(path)


def load_raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, header=[0, 1], index_col=0, parse_dates=True)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_prices(prices: pd.DataFrame) -> None:
    """Raise ValueError on unsorted/duplicate dates or non-finite/non-positive prices.

    NaN is allowed here (it is handled by ``align_prices``); anything else
    that is not a strictly positive finite number is an error.
    """
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError("index must be a DatetimeIndex")
    if prices.index.has_duplicates:
        raise ValueError("duplicate dates in price data")
    if not prices.index.is_monotonic_increasing:
        raise ValueError("dates are not in increasing order")
    values = prices.to_numpy(dtype=float)
    present = ~np.isnan(values)
    if np.isinf(values).any():
        raise ValueError("infinite prices in price data")
    if (values[present] <= 0).any():
        raise ValueError("non-positive prices in price data")


def align_prices(
    adj_close: pd.DataFrame, tickers: list[str] | tuple[str, ...]
) -> tuple[pd.DataFrame, AlignmentReport]:
    """Keep only dates on which every ticker has a price. No filling of any kind."""
    absent = [t for t in tickers if t not in adj_close.columns]
    if absent:
        raise ValueError(f"tickers missing from price data: {absent}")
    frame = adj_close.loc[:, list(tickers)]
    validate_prices(frame)
    missing_by_ticker = {t: int(frame[t].isna().sum()) for t in tickers}
    aligned = frame.dropna(how="any")
    if aligned.empty:
        raise ValueError("no dates on which all tickers have prices")
    report = AlignmentReport(len(frame), len(aligned), missing_by_ticker)
    return aligned, report


def slice_period(prices: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Rows with start <= date <= end (both inclusive)."""
    if pd.Timestamp(start) > pd.Timestamp(end):
        raise ValueError(f"start {start} is after end {end}")
    return prices.loc[pd.Timestamp(start) : pd.Timestamp(end)]
