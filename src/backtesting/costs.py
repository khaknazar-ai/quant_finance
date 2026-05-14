from __future__ import annotations

import pandas as pd

BASIS_POINTS_DENOMINATOR = 10_000.0


def validate_long_only_weight_frame(
    weights: pd.DataFrame,
    max_leverage: float = 1.0,
    tolerance: float = 1e-9,
) -> pd.DataFrame:
    """Validate long-only portfolio weights.

    Rows may sum to less than one to represent cash. Rows must not exceed
    max_leverage because this project does not allow leverage.
    """
    if weights.empty:
        raise ValueError("weights must not be empty.")

    if max_leverage <= 0:
        raise ValueError("max_leverage must be positive.")

    if not isinstance(weights.index, pd.DatetimeIndex):
        raise ValueError("weights index must be a DatetimeIndex.")

    if weights.index.has_duplicates:
        raise ValueError("weights index contains duplicate dates.")

    numeric_weights = weights.apply(pd.to_numeric, errors="coerce")

    if numeric_weights.isna().any().any():
        raise ValueError("weights must not contain NaN values.")

    if (numeric_weights < -tolerance).any().any():
        raise ValueError("weights must be long-only.")

    row_sums = numeric_weights.sum(axis=1)
    if (row_sums > max_leverage + tolerance).any():
        raise ValueError("weights exceed max_leverage.")

    return numeric_weights.sort_index()


def calculate_turnover(
    weights: pd.DataFrame,
    include_initial_allocation: bool = True,
) -> pd.Series:
    """Calculate one-way portfolio turnover from target weights.

    A move from 100% SPY to 100% QQQ has turnover 2.0:
    sell 1.0 SPY and buy 1.0 QQQ.
    """
    validated_weights = validate_long_only_weight_frame(weights)

    previous_weights = validated_weights.shift(1)

    if include_initial_allocation:
        previous_weights.iloc[0] = 0.0

    turnover = (validated_weights - previous_weights).abs().sum(axis=1, min_count=1)
    turnover = turnover.dropna()
    turnover.name = "turnover"

    return turnover


def calculate_transaction_cost_returns(
    turnover: pd.Series,
    transaction_cost_bps: float,
) -> pd.Series:
    """Calculate return drag caused by transaction costs."""
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative.")

    if turnover.empty:
        raise ValueError("turnover must not be empty.")

    if turnover.index.has_duplicates:
        raise ValueError("turnover index contains duplicate dates.")

    numeric_turnover = pd.to_numeric(turnover, errors="coerce")

    if numeric_turnover.isna().any():
        raise ValueError("turnover must not contain NaN values.")

    if (numeric_turnover < 0).any():
        raise ValueError("turnover must be non-negative.")

    cost_returns = numeric_turnover * transaction_cost_bps / BASIS_POINTS_DENOMINATOR
    cost_returns.name = "transaction_cost_return"

    return cost_returns


def calculate_net_returns_after_costs(
    gross_returns: pd.Series,
    turnover: pd.Series,
    transaction_cost_bps: float,
) -> pd.Series:
    """Subtract transaction cost return drag from gross strategy returns."""
    if gross_returns.empty:
        raise ValueError("gross_returns must not be empty.")

    if not isinstance(gross_returns.index, pd.DatetimeIndex):
        raise ValueError("gross_returns index must be a DatetimeIndex.")

    if gross_returns.index.has_duplicates:
        raise ValueError("gross_returns index contains duplicate dates.")

    numeric_gross_returns = pd.to_numeric(gross_returns, errors="coerce")

    if numeric_gross_returns.isna().any():
        raise ValueError("gross_returns must not contain NaN values.")

    cost_returns = calculate_transaction_cost_returns(
        turnover=turnover,
        transaction_cost_bps=transaction_cost_bps,
    )

    dates_not_in_returns = cost_returns.index.difference(numeric_gross_returns.index)
    if not dates_not_in_returns.empty:
        raise ValueError("turnover contains dates that are not present in gross_returns.")

    aligned_cost_returns = cost_returns.reindex(numeric_gross_returns.index).fillna(0.0)
    net_returns = numeric_gross_returns - aligned_cost_returns
    net_returns.name = f"{gross_returns.name or 'portfolio'}_net"

    return net_returns
