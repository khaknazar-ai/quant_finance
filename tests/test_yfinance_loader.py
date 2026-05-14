import pandas as pd
import pytest
from src.ingestion.yfinance_loader import CANONICAL_COLUMNS, canonicalize_yfinance_output


def test_canonicalize_multi_ticker_yfinance_output() -> None:
    dates = pd.to_datetime(["2020-01-01", "2020-01-02"])
    tickers = ["SPY", "QQQ"]
    fields = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

    columns = pd.MultiIndex.from_product([tickers, fields])
    raw = pd.DataFrame(
        [
            [
                100.0,
                102.0,
                99.0,
                101.0,
                101.0,
                1000000.0,
                200.0,
                203.0,
                198.0,
                202.0,
                202.0,
                2000000.0,
            ],
            [
                101.0,
                103.0,
                100.0,
                102.0,
                102.0,
                1100000.0,
                202.0,
                204.0,
                201.0,
                203.0,
                203.0,
                2100000.0,
            ],
        ],
        index=dates,
        columns=columns,
    )

    result = canonicalize_yfinance_output(raw=raw, tickers=tickers)

    assert list(result.columns) == CANONICAL_COLUMNS
    assert len(result) == 4
    assert set(result["ticker"]) == {"SPY", "QQQ"}
    assert result["adjusted_close"].notna().all()


def test_canonicalize_single_ticker_flat_yfinance_output() -> None:
    raw = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Adj Close": [101.0, 102.0],
            "Volume": [1000000.0, 1100000.0],
        },
        index=pd.to_datetime(["2020-01-01", "2020-01-02"]),
    )

    result = canonicalize_yfinance_output(raw=raw, tickers=["SPY"])

    assert list(result.columns) == CANONICAL_COLUMNS
    assert len(result) == 2
    assert set(result["ticker"]) == {"SPY"}


def test_missing_required_yfinance_column_fails() -> None:
    raw = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [102.0],
            "Low": [99.0],
            "Close": [101.0],
            "Volume": [1000000.0],
        },
        index=pd.to_datetime(["2020-01-01"]),
    )

    with pytest.raises(ValueError, match="missing yfinance columns"):
        canonicalize_yfinance_output(raw=raw, tickers=["SPY"])


def test_multi_ticker_without_multiindex_fails() -> None:
    raw = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [102.0],
            "Low": [99.0],
            "Close": [101.0],
            "Adj Close": [101.0],
            "Volume": [1000000.0],
        },
        index=pd.to_datetime(["2020-01-01"]),
    )

    with pytest.raises(ValueError, match="Expected MultiIndex"):
        canonicalize_yfinance_output(raw=raw, tickers=["SPY", "QQQ"])
