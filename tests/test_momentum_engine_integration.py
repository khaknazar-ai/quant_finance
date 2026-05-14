import pandas as pd
from src.backtesting.engine import run_rebalanced_backtest
from src.strategies.baselines import (
    calculate_asset_returns,
    calculate_momentum_top_k_result,
    calculate_momentum_top_k_weights,
)


def make_price_matrix() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=8)
    return pd.DataFrame(
        {
            "SPY": [100.0, 101.0, 102.0, 104.0, 103.0, 105.0, 107.0, 108.0],
            "QQQ": [100.0, 102.0, 103.0, 106.0, 109.0, 111.0, 110.0, 113.0],
            "IEF": [100.0, 100.5, 100.7, 100.8, 100.9, 101.0, 101.1, 101.2],
        },
        index=dates,
    )


def test_momentum_result_matches_generic_backtesting_engine() -> None:
    price_matrix = make_price_matrix()

    momentum_result = calculate_momentum_top_k_result(
        price_matrix=price_matrix,
        lookback_days=2,
        top_k=2,
        rebalance_frequency="B",
        transaction_cost_bps=10.0,
        include_initial_allocation_cost=True,
    )

    asset_returns = calculate_asset_returns(price_matrix)
    target_weights = calculate_momentum_top_k_weights(
        price_matrix=price_matrix,
        lookback_days=2,
        top_k=2,
        rebalance_frequency="B",
    ).dropna(how="all")

    engine_result = run_rebalanced_backtest(
        asset_returns=asset_returns,
        target_weights=target_weights,
        strategy_name="momentum_top_2_2d",
        transaction_cost_bps=10.0,
        execution_lag_days=1,
        include_initial_allocation_cost=True,
        max_leverage=1.0,
    )

    pd.testing.assert_series_equal(momentum_result.gross_returns, engine_result.gross_returns)
    pd.testing.assert_series_equal(momentum_result.net_returns, engine_result.net_returns)
    pd.testing.assert_series_equal(momentum_result.turnover, engine_result.turnover)
    pd.testing.assert_series_equal(momentum_result.cost_returns, engine_result.cost_returns)
    pd.testing.assert_frame_equal(momentum_result.target_weights, engine_result.target_weights)
