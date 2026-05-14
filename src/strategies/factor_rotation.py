from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.backtesting.engine import BacktestResult, run_rebalanced_backtest
from src.strategies.baselines import calculate_asset_returns


@dataclass(frozen=True)
class FactorRotationParameters:
    """Parameterized factor-rotation strategy configuration."""

    momentum_window: int = 126
    volatility_window: int = 63
    drawdown_window: int = 126
    momentum_weight: float = 1.0
    volatility_weight: float = 0.5
    drawdown_weight: float = 0.5
    top_k: int = 5
    max_asset_weight: float = 0.4
    rebalance_frequency: str = "ME"

    def __post_init__(self) -> None:
        """Validate strategy parameters."""
        windows = {
            "momentum_window": self.momentum_window,
            "volatility_window": self.volatility_window,
            "drawdown_window": self.drawdown_window,
        }
        for name, value in windows.items():
            if not isinstance(value, int):
                raise TypeError(f"{name} must be an integer.")
            if value <= 0:
                raise ValueError(f"{name} must be positive.")

        factor_weights = {
            "momentum_weight": self.momentum_weight,
            "volatility_weight": self.volatility_weight,
            "drawdown_weight": self.drawdown_weight,
        }
        for name, value in factor_weights.items():
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative.")

        if sum(factor_weights.values()) <= 0.0:
            raise ValueError("At least one factor weight must be positive.")

        if not isinstance(self.top_k, int):
            raise TypeError("top_k must be an integer.")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive.")

        if self.max_asset_weight <= 0.0 or self.max_asset_weight > 1.0:
            raise ValueError("max_asset_weight must be in the interval (0, 1].")

        if not self.rebalance_frequency:
            raise ValueError("rebalance_frequency must not be empty.")

    def normalized_factor_weights(self) -> dict[str, float]:
        """Return factor weights normalized to sum to 1."""
        total_weight = self.momentum_weight + self.volatility_weight + self.drawdown_weight

        return {
            "momentum": self.momentum_weight / total_weight,
            "volatility": self.volatility_weight / total_weight,
            "drawdown": self.drawdown_weight / total_weight,
        }

    def strategy_name(self) -> str:
        """Return stable strategy name for reports and optimizer outputs."""
        return (
            f"factor_rotation_m{self.momentum_window}"
            f"_v{self.volatility_window}"
            f"_d{self.drawdown_window}"
            f"_mw{self.momentum_weight:g}"
            f"_vw{self.volatility_weight:g}"
            f"_dw{self.drawdown_weight:g}"
            f"_top{self.top_k}"
            f"_maxw{self.max_asset_weight:g}"
        )


def validate_price_matrix(price_matrix: pd.DataFrame) -> pd.DataFrame:
    """Validate date-by-asset positive price matrix."""
    if price_matrix.empty:
        raise ValueError("price_matrix must not be empty.")

    if not isinstance(price_matrix.index, pd.DatetimeIndex):
        raise ValueError("price_matrix must use a DatetimeIndex.")

    if price_matrix.index.has_duplicates:
        raise ValueError("price_matrix must not contain duplicate dates.")

    if len(price_matrix.columns) == 0:
        raise ValueError("price_matrix must contain at least one asset column.")

    non_numeric_columns = [
        column
        for column in price_matrix.columns
        if not pd.api.types.is_numeric_dtype(price_matrix[column])
    ]
    if non_numeric_columns:
        raise ValueError(f"price_matrix contains non-numeric columns: {non_numeric_columns}")

    if price_matrix.isna().any().any():
        raise ValueError("price_matrix must not contain NaN values.")

    if (price_matrix <= 0.0).any().any():
        raise ValueError("price_matrix must contain strictly positive prices.")

    return price_matrix.sort_index().astype("float64")


def calculate_trailing_momentum(
    price_matrix: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Calculate trailing return momentum."""
    if window <= 0:
        raise ValueError("window must be positive.")

    validated_prices = validate_price_matrix(price_matrix)

    return validated_prices / validated_prices.shift(window) - 1.0


def calculate_trailing_volatility(
    price_matrix: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Calculate trailing realized volatility from daily returns."""
    if window <= 0:
        raise ValueError("window must be positive.")

    validated_prices = validate_price_matrix(price_matrix)
    asset_returns = validated_prices.pct_change(fill_method=None)

    return asset_returns.rolling(window=window, min_periods=window).std()


def calculate_trailing_drawdown(
    price_matrix: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Calculate trailing drawdown relative to rolling high."""
    if window <= 0:
        raise ValueError("window must be positive.")

    validated_prices = validate_price_matrix(price_matrix)
    rolling_high = validated_prices.rolling(window=window, min_periods=window).max()

    return validated_prices / rolling_high - 1.0


def cross_sectional_percentile_rank(
    values: pd.DataFrame,
    higher_is_better: bool,
) -> pd.DataFrame:
    """Convert raw factor values to cross-sectional percentile ranks.

    Output convention: higher rank is always better.
    """
    ranking_input = values if higher_is_better else -values

    return ranking_input.rank(axis=1, ascending=True, pct=True)


def calculate_factor_scores(
    price_matrix: pd.DataFrame,
    parameters: FactorRotationParameters,
) -> pd.DataFrame:
    """Calculate combined cross-sectional factor score per asset/date."""
    validated_prices = validate_price_matrix(price_matrix)
    normalized_weights = parameters.normalized_factor_weights()

    momentum_rank = cross_sectional_percentile_rank(
        calculate_trailing_momentum(
            price_matrix=validated_prices,
            window=parameters.momentum_window,
        ),
        higher_is_better=True,
    )
    volatility_rank = cross_sectional_percentile_rank(
        calculate_trailing_volatility(
            price_matrix=validated_prices,
            window=parameters.volatility_window,
        ),
        higher_is_better=False,
    )
    drawdown_rank = cross_sectional_percentile_rank(
        calculate_trailing_drawdown(
            price_matrix=validated_prices,
            window=parameters.drawdown_window,
        ),
        higher_is_better=True,
    )

    combined_score = (
        normalized_weights["momentum"] * momentum_rank
        + normalized_weights["volatility"] * volatility_rank
        + normalized_weights["drawdown"] * drawdown_rank
    )
    combined_score.index.name = validated_prices.index.name

    return combined_score


def get_actual_rebalance_dates(
    price_matrix: pd.DataFrame,
    rebalance_frequency: str,
) -> pd.DatetimeIndex:
    """Return actual trading dates used as rebalance decision dates."""
    validated_prices = validate_price_matrix(price_matrix)
    index_series = pd.Series(validated_prices.index, index=validated_prices.index)
    rebalance_dates = index_series.resample(rebalance_frequency).max().dropna()

    return pd.DatetimeIndex(rebalance_dates)


def calculate_factor_rotation_weights(
    price_matrix: pd.DataFrame,
    parameters: FactorRotationParameters,
) -> pd.DataFrame:
    """Calculate long-only target weights from combined factor scores."""
    validated_prices = validate_price_matrix(price_matrix)

    if parameters.top_k > len(validated_prices.columns):
        raise ValueError("top_k cannot exceed the number of assets.")

    scores = calculate_factor_scores(
        price_matrix=validated_prices,
        parameters=parameters,
    )
    rebalance_dates = get_actual_rebalance_dates(
        price_matrix=validated_prices,
        rebalance_frequency=parameters.rebalance_frequency,
    )

    weights = pd.DataFrame(
        0.0,
        index=rebalance_dates,
        columns=validated_prices.columns,
        dtype="float64",
    )

    for rebalance_date in rebalance_dates:
        available_scores = scores.loc[rebalance_date].dropna()

        if available_scores.empty:
            weights.loc[rebalance_date, :] = pd.NA
            continue

        selected_assets = available_scores.nlargest(parameters.top_k).index
        selected_weight = min(
            1.0 / len(selected_assets),
            parameters.max_asset_weight,
        )
        weights.loc[rebalance_date, selected_assets] = selected_weight

    weights.index.name = validated_prices.index.name

    return weights.astype("float64")


def run_factor_rotation_backtest(
    price_matrix: pd.DataFrame,
    parameters: FactorRotationParameters,
    transaction_cost_bps: float = 10.0,
    execution_lag_days: int = 1,
    include_initial_allocation_cost: bool = True,
) -> BacktestResult:
    """Run parameterized factor rotation through the generic backtesting engine."""
    validated_prices = validate_price_matrix(price_matrix)
    target_weights = calculate_factor_rotation_weights(
        price_matrix=validated_prices,
        parameters=parameters,
    ).dropna(how="all")

    if target_weights.empty:
        raise ValueError("No valid factor-rotation target weights available.")

    asset_returns = calculate_asset_returns(validated_prices)

    return run_rebalanced_backtest(
        asset_returns=asset_returns,
        target_weights=target_weights,
        strategy_name=parameters.strategy_name(),
        transaction_cost_bps=transaction_cost_bps,
        execution_lag_days=execution_lag_days,
        include_initial_allocation_cost=include_initial_allocation_cost,
        max_leverage=1.0,
    )
