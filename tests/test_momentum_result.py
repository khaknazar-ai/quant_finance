import pandas as pd
import pytest
from src.strategies.baselines import calculate_momentum_top_k_result


def make_price_matrix() -> pd.DataFrame:
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


def test_momentum_top_k_result_contains_gross_weights_turnover_costs_and_net() -> None:
    result = calculate_momentum_top_k_result(
        price_matrix=make_price_matrix(),
        lookback_days=1,
        top_k=1,
        rebalance_frequency="D",
        transaction_cost_bps=10,
    )

    assert result.name == "momentum_top_1_1d"
    assert result.gross_returns.name == "momentum_top_1_1d_gross"
    assert result.net_returns.name == "momentum_top_1_1d_net_10bps"
    assert not result.target_weights.empty
    assert not result.turnover.empty
    assert not result.cost_returns.empty
    assert len(result.gross_returns) == len(result.net_returns)


def test_momentum_top_k_result_applies_costs_only_on_return_dates() -> None:
    result = calculate_momentum_top_k_result(
        price_matrix=make_price_matrix(),
        lookback_days=1,
        top_k=1,
        rebalance_frequency="D",
        transaction_cost_bps=10,
        include_initial_allocation_cost=True,
    )

    assert result.gross_returns.loc[pd.Timestamp("2020-01-03")] == pytest.approx(0.0)
    assert (
        result.net_returns.loc[pd.Timestamp("2020-01-03")]
        < result.gross_returns.loc[pd.Timestamp("2020-01-03")]
    )


def test_to_return_series_can_return_gross_or_net() -> None:
    result = calculate_momentum_top_k_result(
        price_matrix=make_price_matrix(),
        lookback_days=1,
        top_k=1,
        rebalance_frequency="D",
        transaction_cost_bps=10,
    )

    assert result.to_return_series(use_net_returns=True).equals(result.net_returns)
    assert result.to_return_series(use_net_returns=False).equals(result.gross_returns)


def test_momentum_top_k_result_drops_pre_signal_nan_weight_rows() -> None:
    result = calculate_momentum_top_k_result(
        price_matrix=make_price_matrix(),
        lookback_days=1,
        top_k=1,
        rebalance_frequency="D",
        transaction_cost_bps=10,
    )

    assert result.target_weights.index.min() == pd.Timestamp("2020-01-02")
    assert not result.target_weights.isna().any().any()


def test_momentum_top_k_result_aligns_turnover_to_return_dates() -> None:
    result = calculate_momentum_top_k_result(
        price_matrix=make_price_matrix(),
        lookback_days=1,
        top_k=1,
        rebalance_frequency="D",
        transaction_cost_bps=10,
        include_initial_allocation_cost=True,
    )

    assert result.turnover.index.equals(result.gross_returns.index)
    assert result.turnover.loc[pd.Timestamp("2020-01-03")] == pytest.approx(1.0)
    assert result.turnover.loc[pd.Timestamp("2020-01-06")] == pytest.approx(2.0)
    assert result.cost_returns.loc[pd.Timestamp("2020-01-03")] == pytest.approx(0.001)
    assert result.cost_returns.loc[pd.Timestamp("2020-01-06")] == pytest.approx(0.002)
