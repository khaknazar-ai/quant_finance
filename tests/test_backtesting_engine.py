import pandas as pd
import pytest
from src.backtesting.engine import (
    calculate_portfolio_gross_returns,
    expand_target_weights_to_daily,
    run_rebalanced_backtest,
    validate_asset_return_frame,
)


def make_asset_returns() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=5)
    return pd.DataFrame(
        {
            "SPY": [0.01, 0.02, 0.03, 0.04, 0.05],
            "QQQ": [0.10, 0.10, 0.10, 0.10, 0.10],
        },
        index=dates,
    )


def make_target_weights() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=5)
    return pd.DataFrame(
        {
            "SPY": [1.0, 0.0],
            "QQQ": [0.0, 1.0],
        },
        index=[dates[0], dates[2]],
    )


def test_expand_target_weights_to_daily_shifts_execution_by_one_day() -> None:
    asset_returns = make_asset_returns()
    target_weights = make_target_weights()

    daily_weights = expand_target_weights_to_daily(
        asset_returns=asset_returns,
        target_weights=target_weights,
        execution_lag_days=1,
    )

    dates = asset_returns.index

    assert daily_weights.loc[dates[0]].isna().all()
    assert daily_weights.loc[dates[1], "SPY"] == 1.0
    assert daily_weights.loc[dates[1], "QQQ"] == 0.0
    assert daily_weights.loc[dates[2], "SPY"] == 1.0
    assert daily_weights.loc[dates[3], "SPY"] == 0.0
    assert daily_weights.loc[dates[3], "QQQ"] == 1.0


def test_calculate_portfolio_gross_returns_matches_manual_calculation() -> None:
    asset_returns = make_asset_returns()
    target_weights = make_target_weights()
    daily_weights = expand_target_weights_to_daily(
        asset_returns=asset_returns,
        target_weights=target_weights,
        execution_lag_days=1,
    )

    gross_returns = calculate_portfolio_gross_returns(
        asset_returns=asset_returns,
        daily_weights=daily_weights,
        strategy_name="test_strategy",
    )

    dates = asset_returns.index

    expected = pd.Series(
        [0.02, 0.03, 0.10, 0.10],
        index=dates[1:],
        name="test_strategy_gross",
    )

    pd.testing.assert_series_equal(gross_returns, expected)


def test_run_rebalanced_backtest_applies_transaction_costs_on_execution_dates() -> None:
    asset_returns = make_asset_returns()
    target_weights = make_target_weights()

    result = run_rebalanced_backtest(
        asset_returns=asset_returns,
        target_weights=target_weights,
        strategy_name="test_strategy",
        transaction_cost_bps=10.0,
        execution_lag_days=1,
        include_initial_allocation_cost=True,
    )

    dates = asset_returns.index

    expected_turnover = pd.Series(
        [1.0, 0.0, 2.0, 0.0],
        index=dates[1:],
        name="turnover",
    )
    expected_net_returns = pd.Series(
        [0.019, 0.03, 0.098, 0.10],
        index=dates[1:],
        name="test_strategy_net_10bps",
    )

    pd.testing.assert_series_equal(result.turnover, expected_turnover)
    pd.testing.assert_series_equal(result.net_returns, expected_net_returns)


def test_backtest_result_can_return_gross_or_net_returns() -> None:
    result = run_rebalanced_backtest(
        asset_returns=make_asset_returns(),
        target_weights=make_target_weights(),
        strategy_name="test_strategy",
        transaction_cost_bps=10.0,
    )

    pd.testing.assert_series_equal(result.to_return_series(True), result.net_returns)
    pd.testing.assert_series_equal(result.to_return_series(False), result.gross_returns)


def test_validate_asset_return_frame_rejects_nan_values() -> None:
    asset_returns = make_asset_returns()
    asset_returns.iloc[0, 0] = pd.NA

    with pytest.raises(ValueError, match="must not contain NaN"):
        validate_asset_return_frame(asset_returns)


def test_run_rebalanced_backtest_rejects_unknown_weight_assets() -> None:
    asset_returns = make_asset_returns()
    target_weights = pd.DataFrame(
        {"UNKNOWN": [1.0]},
        index=[asset_returns.index[0]],
    )

    with pytest.raises(ValueError, match="assets missing from returns"):
        run_rebalanced_backtest(
            asset_returns=asset_returns,
            target_weights=target_weights,
            strategy_name="bad_strategy",
        )


def test_run_rebalanced_backtest_rejects_non_return_decision_dates() -> None:
    asset_returns = make_asset_returns()
    target_weights = pd.DataFrame(
        {"SPY": [1.0], "QQQ": [0.0]},
        index=[pd.Timestamp("1999-01-01")],
    )

    with pytest.raises(ValueError, match="non-return dates"):
        run_rebalanced_backtest(
            asset_returns=asset_returns,
            target_weights=target_weights,
            strategy_name="bad_dates",
        )
