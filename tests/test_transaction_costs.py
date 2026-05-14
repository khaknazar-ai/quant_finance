import pandas as pd
import pytest
from src.backtesting.costs import (
    calculate_net_returns_after_costs,
    calculate_transaction_cost_returns,
    calculate_turnover,
    validate_long_only_weight_frame,
)


def test_calculate_turnover_counts_initial_allocation_and_rebalance() -> None:
    weights = pd.DataFrame(
        {
            "SPY": [1.0, 0.0],
            "QQQ": [0.0, 1.0],
        },
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
    )

    turnover = calculate_turnover(weights, include_initial_allocation=True)

    assert turnover.loc[pd.Timestamp("2020-01-02")] == pytest.approx(1.0)
    assert turnover.loc[pd.Timestamp("2020-01-03")] == pytest.approx(2.0)


def test_calculate_turnover_can_exclude_initial_allocation() -> None:
    weights = pd.DataFrame(
        {
            "SPY": [1.0, 0.0],
            "QQQ": [0.0, 1.0],
        },
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
    )

    turnover = calculate_turnover(weights, include_initial_allocation=False)

    assert list(turnover.index) == [pd.Timestamp("2020-01-03")]
    assert turnover.iloc[0] == pytest.approx(2.0)


def test_calculate_transaction_cost_returns() -> None:
    turnover = pd.Series(
        [0.0, 2.0],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
    )

    cost_returns = calculate_transaction_cost_returns(
        turnover=turnover,
        transaction_cost_bps=10,
    )

    assert cost_returns.loc[pd.Timestamp("2020-01-02")] == pytest.approx(0.0)
    assert cost_returns.loc[pd.Timestamp("2020-01-03")] == pytest.approx(0.002)


def test_calculate_net_returns_after_costs() -> None:
    gross_returns = pd.Series(
        [0.010, 0.020],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        name="strategy",
    )
    turnover = pd.Series(
        [1.0, 2.0],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
    )

    net_returns = calculate_net_returns_after_costs(
        gross_returns=gross_returns,
        turnover=turnover,
        transaction_cost_bps=10,
    )

    assert net_returns.name == "strategy_net"
    assert net_returns.loc[pd.Timestamp("2020-01-02")] == pytest.approx(0.009)
    assert net_returns.loc[pd.Timestamp("2020-01-03")] == pytest.approx(0.018)


def test_negative_transaction_cost_bps_fails() -> None:
    turnover = pd.Series([1.0], index=pd.to_datetime(["2020-01-02"]))

    with pytest.raises(ValueError, match="transaction_cost_bps"):
        calculate_transaction_cost_returns(turnover=turnover, transaction_cost_bps=-1)


def test_negative_weights_fail() -> None:
    weights = pd.DataFrame(
        {
            "SPY": [1.1],
            "QQQ": [-0.1],
        },
        index=pd.to_datetime(["2020-01-02"]),
    )

    with pytest.raises(ValueError, match="long-only"):
        validate_long_only_weight_frame(weights)


def test_leveraged_weights_fail() -> None:
    weights = pd.DataFrame(
        {
            "SPY": [0.8],
            "QQQ": [0.4],
        },
        index=pd.to_datetime(["2020-01-02"]),
    )

    with pytest.raises(ValueError, match="max_leverage"):
        validate_long_only_weight_frame(weights)


def test_turnover_dates_outside_returns_fail() -> None:
    gross_returns = pd.Series(
        [0.010],
        index=pd.to_datetime(["2020-01-02"]),
    )
    turnover = pd.Series(
        [1.0],
        index=pd.to_datetime(["2020-01-03"]),
    )

    with pytest.raises(ValueError, match="not present in gross_returns"):
        calculate_net_returns_after_costs(
            gross_returns=gross_returns,
            turnover=turnover,
            transaction_cost_bps=10,
        )
