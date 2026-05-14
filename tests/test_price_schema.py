import pandas as pd
import pytest
from pandera.errors import SchemaError
from src.validation.schemas import validate_price_frame


def test_valid_price_frame_passes() -> None:
    df = pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02"],
            "ticker": ["SPY", "SPY"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "adjusted_close": [101.0, 102.0],
            "volume": [1000000.0, 1100000.0],
        }
    )

    validated = validate_price_frame(df)

    assert len(validated) == 2
    assert str(validated["date"].dtype).startswith("datetime64")


def test_duplicate_date_ticker_fails() -> None:
    df = pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-01"],
            "ticker": ["SPY", "SPY"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "adjusted_close": [101.0, 102.0],
            "volume": [1000000.0, 1100000.0],
        }
    )

    with pytest.raises(ValueError, match="duplicate"):
        validate_price_frame(df)


def test_negative_price_fails() -> None:
    df = pd.DataFrame(
        {
            "date": ["2020-01-01"],
            "ticker": ["SPY"],
            "open": [-100.0],
            "high": [102.0],
            "low": [99.0],
            "close": [101.0],
            "adjusted_close": [101.0],
            "volume": [1000000.0],
        }
    )

    with pytest.raises(SchemaError):
        validate_price_frame(df)


def test_invalid_ohlc_relationship_fails() -> None:
    df = pd.DataFrame(
        {
            "date": ["2020-01-01"],
            "ticker": ["SPY"],
            "open": [100.0],
            "high": [98.0],
            "low": [99.0],
            "close": [101.0],
            "adjusted_close": [101.0],
            "volume": [1000000.0],
        }
    )

    with pytest.raises(ValueError, match="OHLC"):
        validate_price_frame(df)
