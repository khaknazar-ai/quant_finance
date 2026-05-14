import pandas as pd
import pytest
from src.backtesting.engine import BacktestResult
from src.strategies.factor_rotation import (
    FactorRotationParameters,
    calculate_factor_rotation_weights,
    calculate_factor_scores,
    calculate_trailing_drawdown,
    calculate_trailing_momentum,
    calculate_trailing_volatility,
    run_factor_rotation_backtest,
    validate_price_matrix,
)


def make_price_matrix() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=8)
    return pd.DataFrame(
        {
            "SPY": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "QQQ": [100.0, 102.0, 104.0, 108.0, 112.0, 116.0, 120.0, 124.0],
            "IEF": [100.0, 100.2, 100.4, 100.5, 100.6, 100.7, 100.8, 100.9],
            "GLD": [100.0, 99.0, 101.0, 100.0, 103.0, 102.0, 105.0, 104.0],
        },
        index=dates,
    )


def test_factor_rotation_parameters_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="momentum_window must be positive"):
        FactorRotationParameters(momentum_window=0)

    with pytest.raises(ValueError, match="At least one factor weight"):
        FactorRotationParameters(
            momentum_weight=0.0,
            volatility_weight=0.0,
            drawdown_weight=0.0,
        )

    with pytest.raises(ValueError, match="max_asset_weight"):
        FactorRotationParameters(max_asset_weight=1.5)


def test_validate_price_matrix_rejects_non_positive_prices() -> None:
    price_matrix = make_price_matrix()
    price_matrix.iloc[0, 0] = 0.0

    with pytest.raises(ValueError, match="strictly positive"):
        validate_price_matrix(price_matrix)


def test_trailing_factor_shapes_match_price_matrix() -> None:
    price_matrix = make_price_matrix()

    momentum = calculate_trailing_momentum(price_matrix, window=2)
    volatility = calculate_trailing_volatility(price_matrix, window=2)
    drawdown = calculate_trailing_drawdown(price_matrix, window=2)

    assert momentum.shape == price_matrix.shape
    assert volatility.shape == price_matrix.shape
    assert drawdown.shape == price_matrix.shape


def test_factor_scores_use_higher_is_better_rank_convention() -> None:
    price_matrix = make_price_matrix()
    parameters = FactorRotationParameters(
        momentum_window=2,
        volatility_window=2,
        drawdown_window=2,
        momentum_weight=1.0,
        volatility_weight=0.0,
        drawdown_weight=0.0,
        top_k=1,
        max_asset_weight=1.0,
        rebalance_frequency="B",
    )

    scores = calculate_factor_scores(
        price_matrix=price_matrix,
        parameters=parameters,
    )

    last_date = price_matrix.index[-1]
    assert scores.loc[last_date, "QQQ"] == scores.loc[last_date].max()


def test_factor_rotation_weights_select_top_assets_and_respect_max_weight() -> None:
    price_matrix = make_price_matrix()
    parameters = FactorRotationParameters(
        momentum_window=2,
        volatility_window=2,
        drawdown_window=2,
        momentum_weight=1.0,
        volatility_weight=0.0,
        drawdown_weight=0.0,
        top_k=2,
        max_asset_weight=0.4,
        rebalance_frequency="B",
    )

    weights = calculate_factor_rotation_weights(
        price_matrix=price_matrix,
        parameters=parameters,
    ).dropna(how="all")

    last_date = price_matrix.index[-1]

    assert weights.loc[last_date, "QQQ"] == 0.4
    assert weights.loc[last_date].sum() == pytest.approx(0.8)
    assert weights.max(axis=1).max() <= 0.4


def test_factor_rotation_rejects_top_k_larger_than_universe() -> None:
    price_matrix = make_price_matrix()
    parameters = FactorRotationParameters(top_k=10)

    with pytest.raises(ValueError, match="top_k cannot exceed"):
        calculate_factor_rotation_weights(
            price_matrix=price_matrix,
            parameters=parameters,
        )


def test_run_factor_rotation_backtest_returns_engine_result() -> None:
    price_matrix = make_price_matrix()
    parameters = FactorRotationParameters(
        momentum_window=2,
        volatility_window=2,
        drawdown_window=2,
        momentum_weight=1.0,
        volatility_weight=0.0,
        drawdown_weight=0.0,
        top_k=2,
        max_asset_weight=0.5,
        rebalance_frequency="B",
    )

    result = run_factor_rotation_backtest(
        price_matrix=price_matrix,
        parameters=parameters,
        transaction_cost_bps=10.0,
        execution_lag_days=1,
    )

    assert isinstance(result, BacktestResult)
    assert result.strategy_name == parameters.strategy_name()
    assert result.gross_returns.index.min() > price_matrix.index.min()
    assert result.net_returns.name.endswith("_net_10bps")
    assert (result.turnover >= 0.0).all()
