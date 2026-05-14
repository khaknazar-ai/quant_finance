import pandas as pd
import pytest
from src.optimization.objective import (
    build_invalid_evaluation,
    evaluate_factor_rotation_parameters_on_window,
    slice_price_matrix_for_window,
    summarize_turnover,
)
from src.strategies.factor_rotation import FactorRotationParameters


def make_price_matrix() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=420)
    values = {
        "SPY": [100.0 * (1.0004**index) for index in range(len(dates))],
        "QQQ": [100.0 * (1.0007**index) for index in range(len(dates))],
        "IEF": [100.0 * (1.0001**index) for index in range(len(dates))],
        "GLD": [100.0 * (1.0003**index) for index in range(len(dates))],
    }

    return pd.DataFrame(values, index=dates)


def make_parameters() -> FactorRotationParameters:
    return FactorRotationParameters(
        momentum_window=21,
        volatility_window=21,
        drawdown_window=21,
        momentum_weight=1.0,
        volatility_weight=0.5,
        drawdown_weight=0.5,
        top_k=2,
        max_asset_weight=0.5,
        rebalance_frequency="ME",
    )


def test_slice_price_matrix_for_window_is_inclusive() -> None:
    price_matrix = make_price_matrix()
    start_date = price_matrix.index[10]
    end_date = price_matrix.index[20]

    sliced = slice_price_matrix_for_window(
        price_matrix=price_matrix,
        start_date=start_date,
        end_date=end_date,
    )

    assert sliced.index.min() == start_date
    assert sliced.index.max() == end_date
    assert sliced.shape[0] == 11


def test_evaluate_factor_rotation_parameters_on_window_returns_valid_result() -> None:
    price_matrix = make_price_matrix()
    parameters = make_parameters()

    result = evaluate_factor_rotation_parameters_on_window(
        price_matrix=price_matrix,
        parameters=parameters,
        train_start=price_matrix.index[0],
        train_end=price_matrix.index[-1],
        transaction_cost_bps=10.0,
        min_return_observations=100,
    )

    assert result.valid is True
    assert result.invalid_reason is None
    assert result.strategy_name == parameters.strategy_name()
    assert result.return_observation_count >= 100
    assert result.return_end <= str(price_matrix.index[-1].date())
    assert result.metrics["sharpe"] is not None
    assert result.metrics["cagr"] is not None
    assert result.metrics["max_drawdown"] is not None
    assert result.objectives["negative_sharpe"] == pytest.approx(-float(result.metrics["sharpe"]))
    assert result.objectives["negative_cagr"] == pytest.approx(-float(result.metrics["cagr"]))
    assert result.objectives["max_drawdown_abs"] == pytest.approx(
        abs(float(result.metrics["max_drawdown"]))
    )


def test_evaluate_returns_invalid_result_for_insufficient_observations() -> None:
    price_matrix = make_price_matrix()
    parameters = make_parameters()

    result = evaluate_factor_rotation_parameters_on_window(
        price_matrix=price_matrix,
        parameters=parameters,
        train_start=price_matrix.index[0],
        train_end=price_matrix.index[80],
        min_return_observations=252,
        penalty_value=123.0,
    )

    assert result.valid is False
    assert "Insufficient return observations" in str(result.invalid_reason)
    assert result.objectives["negative_sharpe"] == 123.0
    assert result.return_observation_count == 0


def test_evaluate_can_raise_on_invalid_configuration() -> None:
    price_matrix = make_price_matrix()
    parameters = make_parameters()

    with pytest.raises(ValueError, match="Insufficient return observations"):
        evaluate_factor_rotation_parameters_on_window(
            price_matrix=price_matrix,
            parameters=parameters,
            train_start=price_matrix.index[0],
            train_end=price_matrix.index[80],
            min_return_observations=252,
            raise_on_invalid=True,
        )


def test_invalid_evaluation_is_json_compatible() -> None:
    parameters = make_parameters()

    result = build_invalid_evaluation(
        parameters=parameters,
        train_start="2020-01-01",
        train_end="2020-12-31",
        invalid_reason="bad parameters",
        penalty_value=999.0,
    )

    payload = result.to_dict()

    assert payload["valid"] is False
    assert payload["parameters"]["top_k"] == 2
    assert payload["objectives"]["negative_sharpe"] == 999.0


def test_summarize_turnover_handles_empty_series() -> None:
    summary = summarize_turnover(pd.Series(dtype="float64"))

    assert summary["average_turnover"] is None
    assert summary["rebalance_count"] == 0


def test_evaluation_does_not_extend_beyond_train_end() -> None:
    price_matrix = make_price_matrix()
    parameters = make_parameters()
    train_end = price_matrix.index[300]

    result = evaluate_factor_rotation_parameters_on_window(
        price_matrix=price_matrix,
        parameters=parameters,
        train_start=price_matrix.index[0],
        train_end=train_end,
        min_return_observations=100,
    )

    assert result.valid is True
    assert pd.Timestamp(result.return_end) <= train_end
