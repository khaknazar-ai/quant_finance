import pandas as pd
import pytest
from src.config.settings import FeaturesFileConfig
from src.features.technical import build_technical_features, get_feature_columns


def make_test_config():
    payload = {
        "features": {
            "price_column": "adjusted_close",
            "return_windows": [1],
            "momentum_windows": [2],
            "volatility_windows": [2],
            "drawdown_windows": [3],
            "ranking": {
                "enabled": True,
                "cross_sectional": True,
            },
            "leakage_control": {
                "shift_features_by_days": 1,
                "reason": "Unit test leakage control.",
            },
        }
    }
    return FeaturesFileConfig.model_validate(payload).features


def make_price_frame() -> pd.DataFrame:
    dates = pd.to_datetime(
        [
            "2020-01-01",
            "2020-01-02",
            "2020-01-03",
            "2020-01-04",
            "2020-01-05",
        ]
    )

    return pd.DataFrame(
        {
            "date": list(dates) * 2,
            "ticker": ["SPY"] * 5 + ["QQQ"] * 5,
            "adjusted_close": [
                100.0,
                110.0,
                121.0,
                133.1,
                146.41,
                100.0,
                100.0,
                100.0,
                100.0,
                100.0,
            ],
        }
    )


def test_build_technical_features_creates_expected_columns() -> None:
    config = make_test_config()
    prices = make_price_frame()

    features = build_technical_features(prices=prices, config=config)

    expected_columns = {
        "return_1d",
        "momentum_2d",
        "volatility_2d",
        "drawdown_3d",
        "rank_return_1d",
        "rank_momentum_2d",
        "rank_volatility_2d",
        "rank_drawdown_3d",
    }

    assert expected_columns.issubset(set(features.columns))
    assert "daily_return_unshifted" not in features.columns
    assert expected_columns.issubset(set(get_feature_columns(features)))


def test_features_are_shifted_by_one_day_to_prevent_leakage() -> None:
    config = make_test_config()
    prices = make_price_frame()

    features = build_technical_features(prices=prices, config=config)

    spy = features[features["ticker"] == "SPY"].sort_values("date")

    jan_02 = spy.loc[spy["date"] == pd.Timestamp("2020-01-02")].iloc[0]
    jan_03 = spy.loc[spy["date"] == pd.Timestamp("2020-01-03")].iloc[0]
    jan_04 = spy.loc[spy["date"] == pd.Timestamp("2020-01-04")].iloc[0]

    assert pd.isna(jan_02["return_1d"])
    assert jan_03["return_1d"] == pytest.approx(0.10)
    assert jan_04["momentum_2d"] == pytest.approx(0.21)


def test_cross_sectional_ranks_are_shifted_and_directional() -> None:
    config = make_test_config()
    prices = make_price_frame()

    features = build_technical_features(prices=prices, config=config)

    jan_04 = features[features["date"] == pd.Timestamp("2020-01-04")]

    spy_rank = jan_04.loc[jan_04["ticker"] == "SPY", "rank_momentum_2d"].iloc[0]
    qqq_rank = jan_04.loc[jan_04["ticker"] == "QQQ", "rank_momentum_2d"].iloc[0]

    assert spy_rank == pytest.approx(1.0)
    assert qqq_rank == pytest.approx(0.5)


def test_missing_price_column_fails() -> None:
    config = make_test_config()
    prices = make_price_frame().drop(columns=["adjusted_close"])

    with pytest.raises(ValueError, match="Missing required columns"):
        build_technical_features(prices=prices, config=config)


def test_non_positive_price_fails() -> None:
    config = make_test_config()
    prices = make_price_frame()
    prices.loc[0, "adjusted_close"] = 0.0

    with pytest.raises(ValueError, match="strictly positive"):
        build_technical_features(prices=prices, config=config)
