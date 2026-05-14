from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from src.risk.metrics import calculate_performance_metrics
from src.strategies.factor_rotation import (
    FactorRotationParameters,
    run_factor_rotation_backtest,
    validate_price_matrix,
)


@dataclass(frozen=True)
class ObjectiveEvaluation:
    """Train-window evaluation result for one strategy parameter set."""

    parameters: FactorRotationParameters
    strategy_name: str
    train_start: str
    train_end: str
    valid: bool
    invalid_reason: str | None
    metrics: dict[str, float | int | None]
    objectives: dict[str, float]
    turnover_summary: dict[str, float | int | None]
    return_start: str | None
    return_end: str | None
    return_observation_count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation result to a JSON-compatible dictionary."""
        return asdict(self)


def finite_or_none(value: float | int | None) -> float | int | None:
    """Return numeric value only if it is finite."""
    if value is None:
        return None

    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        return None

    if isinstance(value, int):
        return int(value)

    return numeric_value


def date_to_string(value: pd.Timestamp | str) -> str:
    """Convert date-like value to YYYY-MM-DD string."""
    return str(pd.Timestamp(value).date())


def slice_price_matrix_for_window(
    price_matrix: pd.DataFrame,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
) -> pd.DataFrame:
    """Slice a price matrix to an inclusive train window."""
    validated_prices = validate_price_matrix(price_matrix)

    start_timestamp = pd.Timestamp(start_date)
    end_timestamp = pd.Timestamp(end_date)

    if start_timestamp > end_timestamp:
        raise ValueError("start_date must be less than or equal to end_date.")

    window_prices = validated_prices.loc[
        (validated_prices.index >= start_timestamp) & (validated_prices.index <= end_timestamp)
    ]

    if window_prices.empty:
        raise ValueError("No prices available in the requested window.")

    return window_prices


def summarize_turnover(turnover: pd.Series) -> dict[str, float | int | None]:
    """Summarize turnover series for objective reporting."""
    if turnover.empty:
        return {
            "average_turnover": None,
            "total_turnover": None,
            "max_turnover": None,
            "rebalance_count": 0,
            "turnover_observation_count": 0,
        }

    return {
        "average_turnover": float(turnover.mean()),
        "total_turnover": float(turnover.sum()),
        "max_turnover": float(turnover.max()),
        "rebalance_count": int((turnover > 0.0).sum()),
        "turnover_observation_count": int(turnover.shape[0]),
    }


def build_invalid_evaluation(
    parameters: FactorRotationParameters,
    train_start: str | pd.Timestamp,
    train_end: str | pd.Timestamp,
    invalid_reason: str,
    penalty_value: float,
) -> ObjectiveEvaluation:
    """Build an invalid objective result with optimizer-safe penalties."""
    return ObjectiveEvaluation(
        parameters=parameters,
        strategy_name=parameters.strategy_name(),
        train_start=date_to_string(train_start),
        train_end=date_to_string(train_end),
        valid=False,
        invalid_reason=invalid_reason,
        metrics={
            "cagr": None,
            "sharpe": None,
            "sortino": None,
            "max_drawdown": None,
            "calmar": None,
            "annualized_volatility": None,
            "monthly_win_rate": None,
            "cumulative_return": None,
            "final_equity": None,
        },
        objectives={
            "negative_sharpe": penalty_value,
            "negative_cagr": penalty_value,
            "max_drawdown_abs": penalty_value,
            "average_turnover": penalty_value,
        },
        turnover_summary={
            "average_turnover": None,
            "total_turnover": None,
            "max_turnover": None,
            "rebalance_count": 0,
            "turnover_observation_count": 0,
        },
        return_start=None,
        return_end=None,
        return_observation_count=0,
    )


def build_metric_dict(
    net_returns: pd.Series, risk_free_rate: float
) -> dict[str, float | int | None]:
    """Calculate performance metrics from net returns."""
    performance = calculate_performance_metrics(
        returns=net_returns,
        risk_free_rate=risk_free_rate,
    )

    final_equity = float((1.0 + net_returns).prod())

    return {
        "cagr": finite_or_none(performance.cagr),
        "sharpe": finite_or_none(performance.sharpe),
        "sortino": finite_or_none(performance.sortino),
        "max_drawdown": finite_or_none(performance.max_drawdown),
        "calmar": finite_or_none(performance.calmar),
        "annualized_volatility": finite_or_none(performance.annualized_volatility),
        "monthly_win_rate": finite_or_none(performance.monthly_win_rate),
        "cumulative_return": finite_or_none(performance.cumulative_return),
        "final_equity": finite_or_none(final_equity),
    }


def build_objectives(
    metrics: dict[str, float | int | None],
    turnover_summary: dict[str, float | int | None],
    penalty_value: float,
) -> dict[str, float]:
    """Build minimization objectives from metrics."""
    sharpe = metrics["sharpe"]
    cagr = metrics["cagr"]
    max_drawdown = metrics["max_drawdown"]
    average_turnover = turnover_summary["average_turnover"]

    required_values = {
        "sharpe": sharpe,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "average_turnover": average_turnover,
    }
    if any(value is None for value in required_values.values()):
        return {
            "negative_sharpe": penalty_value,
            "negative_cagr": penalty_value,
            "max_drawdown_abs": penalty_value,
            "average_turnover": penalty_value,
        }

    return {
        "negative_sharpe": -float(sharpe),
        "negative_cagr": -float(cagr),
        "max_drawdown_abs": abs(float(max_drawdown)),
        "average_turnover": float(average_turnover),
    }


def evaluate_factor_rotation_parameters_on_window(
    price_matrix: pd.DataFrame,
    parameters: FactorRotationParameters,
    train_start: str | pd.Timestamp,
    train_end: str | pd.Timestamp,
    transaction_cost_bps: float = 10.0,
    risk_free_rate: float = 0.0,
    min_return_observations: int = 252,
    penalty_value: float = 1_000_000.0,
    raise_on_invalid: bool = False,
) -> ObjectiveEvaluation:
    """Evaluate one factor-rotation parameter set on a train-only window.

    This function is optimizer-ready: invalid configurations return a penalized
    result by default instead of crashing the search loop.
    """
    try:
        if min_return_observations <= 0:
            raise ValueError("min_return_observations must be positive.")

        train_prices = slice_price_matrix_for_window(
            price_matrix=price_matrix,
            start_date=train_start,
            end_date=train_end,
        )

        backtest_result = run_factor_rotation_backtest(
            price_matrix=train_prices,
            parameters=parameters,
            transaction_cost_bps=transaction_cost_bps,
            execution_lag_days=1,
            include_initial_allocation_cost=True,
        )

        net_returns = backtest_result.net_returns

        if net_returns.shape[0] < min_return_observations:
            raise ValueError(
                "Insufficient return observations: "
                f"{net_returns.shape[0]} < {min_return_observations}"
            )

        if net_returns.index.max() > pd.Timestamp(train_end):
            raise ValueError("Evaluation returns extend beyond train_end.")

        metrics = build_metric_dict(
            net_returns=net_returns,
            risk_free_rate=risk_free_rate,
        )
        turnover_summary = summarize_turnover(backtest_result.turnover)
        objectives = build_objectives(
            metrics=metrics,
            turnover_summary=turnover_summary,
            penalty_value=penalty_value,
        )

        if any(value == penalty_value for value in objectives.values()):
            raise ValueError("Non-finite objective metrics.")

        return ObjectiveEvaluation(
            parameters=parameters,
            strategy_name=parameters.strategy_name(),
            train_start=date_to_string(train_start),
            train_end=date_to_string(train_end),
            valid=True,
            invalid_reason=None,
            metrics=metrics,
            objectives=objectives,
            turnover_summary=turnover_summary,
            return_start=date_to_string(net_returns.index.min()),
            return_end=date_to_string(net_returns.index.max()),
            return_observation_count=int(net_returns.shape[0]),
        )

    except Exception as exc:
        if raise_on_invalid:
            raise

        return build_invalid_evaluation(
            parameters=parameters,
            train_start=train_start,
            train_end=train_end,
            invalid_reason=str(exc),
            penalty_value=penalty_value,
        )
