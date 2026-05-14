import pandas as pd
import pytest
from src.strategies.baselines import (
    build_price_matrix,
    calculate_asset_returns,
    calculate_baseline_return_series,
    calculate_buy_and_hold_returns,
    calculate_equal_weight_returns,
    calculate_momentum_scores,
    calculate_momentum_top_k_returns,
    calculate_momentum_top_k_weights,
    get_actual_rebalance_dates,
)


def make_price_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                ]
            ),
            "ticker": ["SPY", "SPY", "SPY", "QQQ", "QQQ", "QQQ"],
            "adjusted_close": [100.0, 110.0, 121.0, 200.0, 220.0, 198.0],
        }
    )


def make_momentum_price_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SPY": [100.0, 90.0, 180.0, 180.0],
            "QQQ": [100.0, 110.0, 110.0, 110.0],
            "IEF": [100.0, 100.0, 100.0, 100.0],
        },
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-01-06",
            ]
        ),
    )


def test_build_price_matrix() -> None:
    prices = make_price_frame()

    price_matrix = build_price_matrix(prices)

    assert list(price_matrix.columns) == ["QQQ", "SPY"]
    assert list(price_matrix.index) == list(
        pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"])
    )
    assert price_matrix.loc[pd.Timestamp("2020-01-02"), "SPY"] == pytest.approx(110.0)


def test_calculate_asset_returns() -> None:
    price_matrix = build_price_matrix(make_price_frame())

    returns = calculate_asset_returns(price_matrix)

    assert returns.loc[pd.Timestamp("2020-01-02"), "SPY"] == pytest.approx(0.10)
    assert returns.loc[pd.Timestamp("2020-01-03"), "SPY"] == pytest.approx(0.10)
    assert returns.loc[pd.Timestamp("2020-01-03"), "QQQ"] == pytest.approx(-0.10)


def test_calculate_buy_and_hold_returns() -> None:
    asset_returns = calculate_asset_returns(build_price_matrix(make_price_frame()))

    spy_returns = calculate_buy_and_hold_returns(asset_returns, ticker="SPY")

    assert spy_returns.name == "buy_hold_SPY"
    assert len(spy_returns) == 2
    assert spy_returns.iloc[0] == pytest.approx(0.10)


def test_calculate_equal_weight_returns() -> None:
    asset_returns = calculate_asset_returns(build_price_matrix(make_price_frame()))

    portfolio_returns = calculate_equal_weight_returns(asset_returns, tickers=["SPY", "QQQ"])

    assert portfolio_returns.name == "equal_weight"
    assert portfolio_returns.loc[pd.Timestamp("2020-01-02")] == pytest.approx(0.10)
    assert portfolio_returns.loc[pd.Timestamp("2020-01-03")] == pytest.approx(0.0)


def test_calculate_baseline_return_series() -> None:
    baselines = calculate_baseline_return_series(
        prices=make_price_frame(),
        benchmark_ticker="SPY",
        universe_tickers=["SPY", "QQQ"],
    )

    assert set(baselines) == {"buy_hold_SPY", "equal_weight"}
    assert baselines["buy_hold_SPY"].iloc[0] == pytest.approx(0.10)
    assert baselines["equal_weight"].iloc[-1] == pytest.approx(0.0)


def test_duplicate_date_ticker_rows_fail() -> None:
    prices = pd.concat([make_price_frame(), make_price_frame().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate"):
        build_price_matrix(prices)


def test_missing_ticker_fails() -> None:
    asset_returns = calculate_asset_returns(build_price_matrix(make_price_frame()))

    with pytest.raises(ValueError, match="Ticker not found"):
        calculate_buy_and_hold_returns(asset_returns, ticker="IWM")


def test_calculate_asset_returns_does_not_forward_fill_missing_prices() -> None:
    price_matrix = pd.DataFrame(
        {
            "SPY": [100.0, None, 110.0],
            "QQQ": [200.0, 220.0, 242.0],
        },
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
    )

    returns = calculate_asset_returns(price_matrix)

    assert pd.isna(returns.loc[pd.Timestamp("2020-01-02"), "SPY"])
    assert pd.isna(returns.loc[pd.Timestamp("2020-01-03"), "SPY"])
    assert returns.loc[pd.Timestamp("2020-01-02"), "QQQ"] == pytest.approx(0.10)
    assert returns.loc[pd.Timestamp("2020-01-03"), "QQQ"] == pytest.approx(0.10)


def test_calculate_momentum_scores() -> None:
    price_matrix = make_momentum_price_matrix()

    scores = calculate_momentum_scores(price_matrix, lookback_days=1)

    assert scores.loc[pd.Timestamp("2020-01-02"), "SPY"] == pytest.approx(-0.10)
    assert scores.loc[pd.Timestamp("2020-01-02"), "QQQ"] == pytest.approx(0.10)
    assert scores.loc[pd.Timestamp("2020-01-03"), "SPY"] == pytest.approx(1.0)
    assert scores.loc[pd.Timestamp("2020-01-03"), "QQQ"] == pytest.approx(0.0)


def test_get_actual_rebalance_dates_uses_actual_trading_days() -> None:
    price_matrix = pd.DataFrame(
        {"SPY": [100.0, 101.0, 102.0, 103.0]},
        index=pd.to_datetime(
            [
                "2020-01-30",
                "2020-01-31",
                "2020-02-27",
                "2020-02-28",
            ]
        ),
    )

    rebalance_dates = get_actual_rebalance_dates(price_matrix, rebalance_frequency="ME")

    assert list(rebalance_dates) == [
        pd.Timestamp("2020-01-31"),
        pd.Timestamp("2020-02-28"),
    ]


def test_calculate_momentum_top_k_weights_selects_top_asset() -> None:
    price_matrix = make_momentum_price_matrix()

    weights = calculate_momentum_top_k_weights(
        price_matrix=price_matrix,
        lookback_days=1,
        top_k=1,
        rebalance_frequency="D",
    )

    assert weights.loc[pd.Timestamp("2020-01-02"), "QQQ"] == pytest.approx(1.0)
    assert weights.loc[pd.Timestamp("2020-01-02"), "SPY"] == pytest.approx(0.0)
    assert weights.loc[pd.Timestamp("2020-01-03"), "SPY"] == pytest.approx(1.0)
    assert weights.loc[pd.Timestamp("2020-01-03"), "QQQ"] == pytest.approx(0.0)


def test_momentum_top_k_returns_are_shifted_to_avoid_same_day_leakage() -> None:
    price_matrix = make_momentum_price_matrix()

    returns = calculate_momentum_top_k_returns(
        price_matrix=price_matrix,
        lookback_days=1,
        top_k=1,
        rebalance_frequency="D",
    )

    assert returns.loc[pd.Timestamp("2020-01-03")] == pytest.approx(0.0)
    assert returns.loc[pd.Timestamp("2020-01-06")] == pytest.approx(0.0)


def test_momentum_top_k_rejects_invalid_top_k() -> None:
    price_matrix = make_momentum_price_matrix()

    with pytest.raises(ValueError, match="top_k cannot exceed"):
        calculate_momentum_top_k_weights(
            price_matrix=price_matrix,
            lookback_days=1,
            top_k=10,
            rebalance_frequency="D",
        )


def test_momentum_scores_reject_invalid_lookback() -> None:
    price_matrix = make_momentum_price_matrix()

    with pytest.raises(ValueError, match="lookback_days"):
        calculate_momentum_scores(price_matrix, lookback_days=0)
