from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.backtesting.costs import (
    calculate_net_returns_after_costs,
    calculate_transaction_cost_returns,
    calculate_turnover,
    validate_long_only_weight_frame,
)


@dataclass(frozen=True)
class BacktestResult:
    """Portfolio backtest result with gross/net returns and cost details."""

    strategy_name: str
    gross_returns: pd.Series
    net_returns: pd.Series
    turnover: pd.Series
    cost_returns: pd.Series
    daily_weights: pd.DataFrame
    target_weights: pd.DataFrame
    transaction_cost_bps: float
    execution_lag_days: int

    def to_return_series(self, use_net_returns: bool = True) -> pd.Series:
        """Return net or gross portfolio returns."""
        if use_net_returns:
            return self.net_returns

        return self.gross_returns


def validate_asset_return_frame(asset_returns: pd.DataFrame) -> pd.DataFrame:
    """Validate a date-by-asset return frame."""
    if asset_returns.empty:
        raise ValueError("asset_returns must not be empty.")

    if not isinstance(asset_returns.index, pd.DatetimeIndex):
        raise ValueError("asset_returns must use a DatetimeIndex.")

    if asset_returns.index.has_duplicates:
        raise ValueError("asset_returns must not contain duplicate dates.")

    if len(asset_returns.columns) == 0:
        raise ValueError("asset_returns must contain at least one asset column.")

    non_numeric_columns = [
        column
        for column in asset_returns.columns
        if not pd.api.types.is_numeric_dtype(asset_returns[column])
    ]
    if non_numeric_columns:
        raise ValueError(f"asset_returns contains non-numeric columns: {non_numeric_columns}")

    if asset_returns.isna().any().any():
        raise ValueError("asset_returns must not contain NaN values.")

    if (asset_returns <= -1.0).any().any():
        raise ValueError("asset_returns must be greater than -100%.")

    return asset_returns.sort_index().astype("float64")


def validate_execution_lag_days(execution_lag_days: int) -> None:
    """Validate execution lag convention."""
    if not isinstance(execution_lag_days, int):
        raise TypeError("execution_lag_days must be an integer.")

    if execution_lag_days < 0:
        raise ValueError("execution_lag_days must be non-negative.")


def prepare_target_weights(
    target_weights: pd.DataFrame,
    asset_returns: pd.DataFrame,
    max_leverage: float = 1.0,
) -> pd.DataFrame:
    """Validate target weights and align columns to asset returns."""
    validated_returns = validate_asset_return_frame(asset_returns)
    validated_weights = validate_long_only_weight_frame(
        weights=target_weights,
        max_leverage=max_leverage,
    )

    unknown_assets = sorted(set(validated_weights.columns).difference(validated_returns.columns))
    if unknown_assets:
        raise ValueError(f"target_weights contains assets missing from returns: {unknown_assets}")

    missing_decision_dates = validated_weights.index.difference(validated_returns.index)
    if len(missing_decision_dates) > 0:
        preview = [str(date.date()) for date in missing_decision_dates[:5]]
        raise ValueError(f"target_weights contains non-return dates: {preview}")

    return validated_weights.reindex(columns=validated_returns.columns, fill_value=0.0)


def expand_target_weights_to_daily(
    asset_returns: pd.DataFrame,
    target_weights: pd.DataFrame,
    execution_lag_days: int = 1,
    max_leverage: float = 1.0,
) -> pd.DataFrame:
    """Expand sparse target weights to daily investable weights.

    target_weights are decision-date weights. execution_lag_days=1 means the
    allocation becomes active on the next return observation, preventing
    same-day signal/execution leakage.
    """
    validate_execution_lag_days(execution_lag_days)

    validated_returns = validate_asset_return_frame(asset_returns)
    prepared_weights = prepare_target_weights(
        target_weights=target_weights,
        asset_returns=validated_returns,
        max_leverage=max_leverage,
    )

    daily_weights = prepared_weights.reindex(validated_returns.index).ffill()
    daily_weights = daily_weights.shift(execution_lag_days)
    daily_weights = daily_weights.reindex(columns=validated_returns.columns)
    daily_weights.index.name = validated_returns.index.name

    return daily_weights


def calculate_portfolio_gross_returns(
    asset_returns: pd.DataFrame,
    daily_weights: pd.DataFrame,
    strategy_name: str = "portfolio",
    max_leverage: float = 1.0,
) -> pd.Series:
    """Calculate gross portfolio returns from daily weights and asset returns."""
    validated_returns = validate_asset_return_frame(asset_returns)

    if daily_weights.empty:
        raise ValueError("daily_weights must not be empty.")

    if not isinstance(daily_weights.index, pd.DatetimeIndex):
        raise ValueError("daily_weights must use a DatetimeIndex.")

    if daily_weights.index.has_duplicates:
        raise ValueError("daily_weights must not contain duplicate dates.")

    unknown_assets = sorted(set(daily_weights.columns).difference(validated_returns.columns))
    if unknown_assets:
        raise ValueError(f"daily_weights contains assets missing from returns: {unknown_assets}")

    active_weights = daily_weights.reindex(columns=validated_returns.columns).dropna(how="all")
    if active_weights.empty:
        raise ValueError("No active daily weights are available after applying execution lag.")

    if active_weights.isna().any().any():
        raise ValueError("daily_weights must not contain partial NaN rows after activation.")

    if (active_weights < 0.0).any().any():
        raise ValueError("daily_weights must be long-only.")

    if (active_weights.sum(axis=1) > max_leverage + 1e-9).any():
        raise ValueError("daily_weights exceeds max_leverage.")

    aligned_returns = validated_returns.reindex(active_weights.index)
    if aligned_returns.isna().any().any():
        raise ValueError("daily_weights contains dates missing from asset_returns.")

    gross_returns = (active_weights * aligned_returns).sum(axis=1, min_count=1).dropna()
    gross_returns.name = f"{strategy_name}_gross"

    if gross_returns.empty:
        raise ValueError("gross portfolio returns are empty.")

    return gross_returns


def align_turnover_to_return_dates(
    asset_returns: pd.DataFrame,
    target_weights: pd.DataFrame,
    gross_returns: pd.Series,
    execution_lag_days: int,
    include_initial_allocation_cost: bool = True,
) -> pd.Series:
    """Calculate decision-date turnover and align it to return dates."""
    validate_execution_lag_days(execution_lag_days)

    validated_returns = validate_asset_return_frame(asset_returns)
    decision_date_turnover = calculate_turnover(
        weights=target_weights,
        include_initial_allocation=include_initial_allocation_cost,
    )

    return_date_turnover = (
        decision_date_turnover.reindex(validated_returns.index)
        .fillna(0.0)
        .shift(execution_lag_days)
        .fillna(0.0)
    )
    aligned_turnover = return_date_turnover.reindex(gross_returns.index).fillna(0.0)
    aligned_turnover.name = "turnover"

    return aligned_turnover


def run_rebalanced_backtest(
    asset_returns: pd.DataFrame,
    target_weights: pd.DataFrame,
    strategy_name: str,
    transaction_cost_bps: float = 10.0,
    execution_lag_days: int = 1,
    include_initial_allocation_cost: bool = True,
    max_leverage: float = 1.0,
) -> BacktestResult:
    """Run a long-only rebalanced portfolio backtest."""
    validated_returns = validate_asset_return_frame(asset_returns)
    prepared_target_weights = prepare_target_weights(
        target_weights=target_weights,
        asset_returns=validated_returns,
        max_leverage=max_leverage,
    )

    daily_weights = expand_target_weights_to_daily(
        asset_returns=validated_returns,
        target_weights=prepared_target_weights,
        execution_lag_days=execution_lag_days,
        max_leverage=max_leverage,
    )

    gross_returns = calculate_portfolio_gross_returns(
        asset_returns=validated_returns,
        daily_weights=daily_weights,
        strategy_name=strategy_name,
        max_leverage=max_leverage,
    )

    turnover = align_turnover_to_return_dates(
        asset_returns=validated_returns,
        target_weights=prepared_target_weights,
        gross_returns=gross_returns,
        execution_lag_days=execution_lag_days,
        include_initial_allocation_cost=include_initial_allocation_cost,
    )

    cost_returns = calculate_transaction_cost_returns(
        turnover=turnover,
        transaction_cost_bps=transaction_cost_bps,
    )

    net_returns = calculate_net_returns_after_costs(
        gross_returns=gross_returns,
        turnover=turnover,
        transaction_cost_bps=transaction_cost_bps,
    )
    net_returns.name = f"{strategy_name}_net_{transaction_cost_bps:g}bps"

    return BacktestResult(
        strategy_name=strategy_name,
        gross_returns=gross_returns,
        net_returns=net_returns,
        turnover=turnover,
        cost_returns=cost_returns,
        daily_weights=daily_weights,
        target_weights=prepared_target_weights,
        transaction_cost_bps=transaction_cost_bps,
        execution_lag_days=execution_lag_days,
    )
