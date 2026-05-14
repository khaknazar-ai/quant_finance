from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

PRICE_SCHEMA = pa.DataFrameSchema(
    {
        "date": pa.Column(pa.DateTime, nullable=False),
        "ticker": pa.Column(str, nullable=False),
        "open": pa.Column(float, pa.Check.gt(0), nullable=False),
        "high": pa.Column(float, pa.Check.gt(0), nullable=False),
        "low": pa.Column(float, pa.Check.gt(0), nullable=False),
        "close": pa.Column(float, pa.Check.gt(0), nullable=False),
        "adjusted_close": pa.Column(float, pa.Check.gt(0), nullable=False),
        "volume": pa.Column(float, pa.Check.ge(0), nullable=False),
    },
    strict=True,
    coerce=True,
)


def validate_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Validate canonical OHLCV price data.

    This function intentionally fails fast. It does not fill missing values,
    patch individual tickers, or silently repair vendor data.
    """
    validated = PRICE_SCHEMA.validate(df)

    duplicate_count = validated.duplicated(subset=["date", "ticker"]).sum()
    if duplicate_count > 0:
        raise ValueError(f"Found duplicate date/ticker rows: {duplicate_count}")

    invalid_ohlc = (
        (validated["high"] < validated["low"])
        | (validated["high"] < validated["open"])
        | (validated["high"] < validated["close"])
        | (validated["low"] > validated["open"])
        | (validated["low"] > validated["close"])
    )

    if invalid_ohlc.any():
        raise ValueError(f"Found invalid OHLC relationships: {int(invalid_ohlc.sum())}")

    return validated
