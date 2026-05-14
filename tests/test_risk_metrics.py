import math

import pandas as pd
import pytest
from src.risk.metrics import (
    calculate_cagr,
    calculate_drawdown_series,
    calculate_equity_curve,
    calculate_max_drawdown,
    calculate_performance_metrics,
)


def test_equity_curve_includes_first_return() -> None:
    returns = pd.Series([0.10, -0.05, 0.02])

    equity = calculate_equity_curve(returns)

    assert equity.iloc[0] == pytest.approx(1.10)
    assert equity.iloc[-1] == pytest.approx(1.10 * 0.95 * 1.02)


def test_performance_metrics_cumulative_return_uses_initial_capital() -> None:
    returns = pd.Series([0.10])

    metrics = calculate_performance_metrics(returns)

    assert metrics.cumulative_return == pytest.approx(0.10)
    assert metrics.observation_count == 1


def test_drawdown_series_and_max_drawdown() -> None:
    equity = pd.Series([1.0, 1.2, 0.9, 1.5])

    drawdown = calculate_drawdown_series(equity)

    assert drawdown.iloc[0] == pytest.approx(0.0)
    assert drawdown.iloc[1] == pytest.approx(0.0)
    assert drawdown.iloc[2] == pytest.approx(-0.25)
    assert calculate_max_drawdown(equity) == pytest.approx(-0.25)


def test_cagr_uses_initial_capital_basis() -> None:
    equity = pd.Series([1.10])

    cagr = calculate_cagr(equity, initial_capital=1.0, periods_per_year=1)

    assert cagr == pytest.approx(0.10)


def test_monthly_win_rate_requires_datetime_index() -> None:
    returns = pd.Series([0.01, -0.01, 0.02])

    metrics = calculate_performance_metrics(returns)

    assert math.isnan(metrics.monthly_win_rate)


def test_performance_metrics_with_datetime_index_has_monthly_win_rate() -> None:
    returns = pd.Series(
        [0.01, 0.01, -0.01, -0.01],
        index=pd.to_datetime(
            [
                "2020-01-02",
                "2020-01-03",
                "2020-02-03",
                "2020-02-04",
            ]
        ),
    )

    metrics = calculate_performance_metrics(returns)

    assert metrics.monthly_win_rate == pytest.approx(0.5)


def test_empty_returns_fail() -> None:
    with pytest.raises(ValueError, match="returns must contain"):
        calculate_performance_metrics(pd.Series([], dtype=float))


def test_non_positive_initial_capital_fails() -> None:
    with pytest.raises(ValueError, match="initial_capital"):
        calculate_equity_curve(pd.Series([0.01]), initial_capital=0.0)
