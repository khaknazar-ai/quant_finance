from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.config.settings import load_universe_config

RAW_TO_CANONICAL_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adjusted_close",
    "Volume": "volume",
}

CANONICAL_COLUMNS = [
    "date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
]


def download_price_history(
    tickers: Sequence[str],
    start_date: str,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Download OHLCV price history from yfinance.

    The function returns canonical long-format data:

    date, ticker, open, high, low, close, adjusted_close, volume

    It does not fill missing values, patch individual tickers, or silently repair
    vendor data. Data quality is handled by the validation layer.
    """
    if not tickers:
        raise ValueError("tickers must not be empty.")

    unique_tickers = list(dict.fromkeys(tickers))
    if len(unique_tickers) != len(tickers):
        raise ValueError("tickers contains duplicates.")

    raw = yf.download(
        tickers=unique_tickers,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    if raw.empty:
        raise ValueError("yfinance returned an empty dataframe.")

    return canonicalize_yfinance_output(raw=raw, tickers=unique_tickers)


def download_price_history_from_config(config_path: str | Path) -> pd.DataFrame:
    """Download price history using configs/universe_etf.yaml."""
    config = load_universe_config(config_path)

    return download_price_history(
        tickers=config.universe.tickers,
        start_date=config.data.start_date,
        end_date=config.data.end_date,
    )


def canonicalize_yfinance_output(raw: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    """Convert yfinance output into canonical long-format OHLCV data."""
    frames: list[pd.DataFrame] = []

    for ticker in tickers:
        ticker_frame = _select_ticker_frame(raw=raw, ticker=ticker, ticker_count=len(tickers))
        canonical_frame = _canonicalize_single_ticker_frame(ticker_frame, ticker)
        frames.append(canonical_frame)

    if not frames:
        raise ValueError("No ticker frames were canonicalized.")

    result = pd.concat(frames, ignore_index=True)
    return result[CANONICAL_COLUMNS].sort_values(["date", "ticker"]).reset_index(drop=True)


def _select_ticker_frame(raw: pd.DataFrame, ticker: str, ticker_count: int) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        level_0_values = set(raw.columns.get_level_values(0).astype(str))
        level_1_values = set(raw.columns.get_level_values(1).astype(str))

        if ticker in level_0_values:
            return raw[ticker].copy()

        if ticker in level_1_values:
            return raw.xs(ticker, axis=1, level=1).copy()

        raise ValueError(f"Ticker {ticker} not found in yfinance MultiIndex output.")

    if ticker_count == 1:
        return raw.copy()

    raise ValueError("Expected MultiIndex columns for multiple tickers.")


def _canonicalize_single_ticker_frame(ticker_frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    available_columns = set(ticker_frame.columns.astype(str))
    required_columns = set(RAW_TO_CANONICAL_COLUMNS)

    missing_columns = sorted(required_columns - available_columns)
    if missing_columns:
        raise ValueError(f"Ticker {ticker} is missing yfinance columns: {missing_columns}")

    frame = ticker_frame.rename(columns=RAW_TO_CANONICAL_COLUMNS)
    frame = frame[list(RAW_TO_CANONICAL_COLUMNS.values())].copy()

    frame.index.name = "date"
    frame = frame.reset_index()
    frame["ticker"] = ticker

    return frame[CANONICAL_COLUMNS]
