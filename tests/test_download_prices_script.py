import pandas as pd
from scripts.download_prices import build_quality_report


def test_build_quality_report() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-01"]),
            "ticker": ["SPY", "SPY", "QQQ"],
            "open": [100.0, 101.0, 200.0],
            "high": [102.0, 103.0, 203.0],
            "low": [99.0, 100.0, 198.0],
            "close": [101.0, 102.0, 202.0],
            "adjusted_close": [101.0, 102.0, 202.0],
            "volume": [1000000.0, 1100000.0, 2000000.0],
        }
    )

    report = build_quality_report(df)

    assert report["rows"] == 3
    assert report["ticker_count"] == 2
    assert report["tickers"] == ["QQQ", "SPY"]
    assert report["min_date"] == "2020-01-01"
    assert report["max_date"] == "2020-01-02"
    assert report["rows_per_ticker"] == {"QQQ": 1, "SPY": 2}
    assert report["missing_values_by_column"]["adjusted_close"] == 0
