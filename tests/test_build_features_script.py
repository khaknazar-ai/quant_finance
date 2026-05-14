import pandas as pd
from scripts.build_features import build_feature_quality_report


def test_build_feature_quality_report() -> None:
    features = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-01",
                    "2020-01-02",
                ]
            ),
            "ticker": ["SPY", "SPY", "QQQ", "QQQ"],
            "adjusted_close": [100.0, 101.0, 200.0, 202.0],
            "momentum_2d": [None, 0.01, None, 0.02],
            "volatility_2d": [None, 0.20, None, 0.25],
        }
    )

    report = build_feature_quality_report(
        features=features,
        feature_columns=["momentum_2d", "volatility_2d"],
        leakage_shift_days=1,
    )

    assert report["rows"] == 4
    assert report["tickers"] == ["QQQ", "SPY"]
    assert report["ticker_count"] == 2
    assert report["feature_count"] == 2
    assert report["leakage_shift_days"] == 1
    assert report["complete_feature_rows"] == 2
    assert report["first_complete_feature_date"] == "2020-01-02"
    assert report["missing_values_by_feature"] == {
        "momentum_2d": 2,
        "volatility_2d": 2,
    }
    assert report["non_null_ratio_by_feature"] == {
        "momentum_2d": 0.5,
        "volatility_2d": 0.5,
    }
