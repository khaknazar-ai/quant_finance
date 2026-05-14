from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.backtesting.engine import run_rebalanced_backtest


def build_price_matrix(
    prices: pd.DataFrame,
    price_column: str = "adjusted_close",
) -> pd.DataFrame:
    """Build a date-by-ticker adjusted price matrix."""
    required_columns = {"date", "ticker", price_column}
    missing_columns = required_columns.difference(prices.columns)
    if missing_columns:
        raise ValueError(f"Missing required price columns: {sorted(missing_columns)}")

    if prices.empty:
        raise ValueError("prices must not be empty.")

    duplicated_rows = prices.duplicated(subset=["date", "ticker"])
    if duplicated_rows.any():
        raise ValueError("prices must not contain duplicate date/ticker rows.")

    price_matrix = prices.pivot(index="date", columns="ticker", values=price_column)
    price_matrix = price_matrix.sort_index()
    price_matrix.index = pd.DatetimeIndex(price_matrix.index)

    if (price_matrix <= 0.0).any().any():
        raise ValueError("price matrix must contain strictly positive prices.")

    return price_matrix.astype("float64")


def calculate_asset_returns(price_matrix: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily asset returns without implicit forward-fill."""
    if price_matrix.empty:
        raise ValueError("price_matrix must not be empty.")

    return price_matrix.sort_index().pct_change(fill_method=None).dropna(how="all")


def calculate_buy_and_hold_returns(
    asset_returns: pd.DataFrame,
    ticker: str,
) -> pd.Series:
    """Return buy-and-hold daily returns for one ticker."""
    if ticker not in asset_returns.columns:
        raise ValueError(f"Ticker not found: {ticker}")

    returns = asset_returns[ticker].dropna().copy()
    returns.name = f"buy_hold_{ticker}"
    return returns


def calculate_equal_weight_returns(
    asset_returns: pd.DataFrame,
    tickers: list[str] | None = None,
) -> pd.Series:
    """Return daily rebalanced equal-weight portfolio returns."""
    if asset_returns.empty:
        raise ValueError("asset_returns must not be empty.")

    selected_returns = asset_returns
    if tickers is not None:
        missing_tickers = sorted(set(tickers).difference(asset_returns.columns))
        if missing_tickers:
            raise ValueError(f"Missing tickers in asset_returns: {missing_tickers}")
        selected_returns = asset_returns[tickers]

    returns = selected_returns.mean(axis=1, skipna=True).dropna().copy()
    returns.name = "equal_weight"
    return returns


def calculate_momentum_scores(
    price_matrix: pd.DataFrame,
    lookback_days: int = 252,
) -> pd.DataFrame:
    """Calculate trailing price momentum scores."""
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive.")

    if price_matrix.empty:
        raise ValueError("price_matrix must not be empty.")

    return price_matrix / price_matrix.shift(lookback_days) - 1.0


def get_actual_rebalance_dates(
    price_matrix: pd.DataFrame,
    rebalance_frequency: str = "ME",
) -> pd.DatetimeIndex:
    """Return actual trading dates used for calendar resampling periods."""
    if not isinstance(price_matrix.index, pd.DatetimeIndex):
        raise ValueError("price_matrix must use a DatetimeIndex.")

    if price_matrix.empty:
        raise ValueError("price_matrix must not be empty.")

    index_series = pd.Series(price_matrix.index, index=price_matrix.index)
    rebalance_dates = index_series.resample(rebalance_frequency).max().dropna()

    return pd.DatetimeIndex(rebalance_dates)


def calculate_momentum_top_k_weights(
    price_matrix: pd.DataFrame,
    lookback_days: int = 252,
    top_k: int = 5,
    rebalance_frequency: str = "ME",
) -> pd.DataFrame:
    """Calculate long-only equal-weight top-K momentum target weights."""
    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    if price_matrix.empty:
        raise ValueError("price_matrix must not be empty.")

    if top_k > len(price_matrix.columns):
        raise ValueError("top_k cannot exceed the number of assets.")

    momentum_scores = calculate_momentum_scores(
        price_matrix=price_matrix,
        lookback_days=lookback_days,
    )
    rebalance_dates = get_actual_rebalance_dates(
        price_matrix=price_matrix,
        rebalance_frequency=rebalance_frequency,
    )

    weights = pd.DataFrame(
        0.0,
        index=rebalance_dates,
        columns=price_matrix.columns,
        dtype="float64",
    )

    for rebalance_date in rebalance_dates:
        scores = momentum_scores.loc[rebalance_date].dropna()

        if scores.empty:
            weights.loc[rebalance_date, :] = pd.NA
            continue

        selected_tickers = scores.nlargest(top_k).index
        weights.loc[rebalance_date, selected_tickers] = 1.0 / len(selected_tickers)

    return weights.astype("float64")


@dataclass(frozen=True)
class MomentumTopKResult:
    """Cost-aware momentum strategy result."""

    name: str
    gross_returns: pd.Series
    target_weights: pd.DataFrame
    turnover: pd.Series
    cost_returns: pd.Series
    net_returns: pd.Series

    def to_return_series(self, use_net_returns: bool = True) -> pd.Series:
        """Return net or gross momentum returns."""
        if use_net_returns:
            return self.net_returns

        return self.gross_returns


def calculate_momentum_top_k_result(
    price_matrix: pd.DataFrame,
    lookback_days: int = 252,
    top_k: int = 5,
    rebalance_frequency: str = "ME",
    transaction_cost_bps: float = 10.0,
    include_initial_allocation_cost: bool = True,
) -> MomentumTopKResult:
    """Calculate gross/net top-K momentum returns with transaction costs."""
    asset_returns = calculate_asset_returns(price_matrix)
    raw_target_weights = calculate_momentum_top_k_weights(
        price_matrix=price_matrix,
        lookback_days=lookback_days,
        top_k=top_k,
        rebalance_frequency=rebalance_frequency,
    )
    target_weights = raw_target_weights.dropna(how="all")

    if target_weights.empty:
        raise ValueError("No valid momentum target weights available.")

    strategy_name = f"momentum_top_{top_k}_{lookback_days}d"
    backtest_result = run_rebalanced_backtest(
        asset_returns=asset_returns,
        target_weights=target_weights,
        strategy_name=strategy_name,
        transaction_cost_bps=transaction_cost_bps,
        execution_lag_days=1,
        include_initial_allocation_cost=include_initial_allocation_cost,
        max_leverage=1.0,
    )

    return MomentumTopKResult(
        name=strategy_name,
        gross_returns=backtest_result.gross_returns,
        target_weights=backtest_result.target_weights,
        turnover=backtest_result.turnover,
        cost_returns=backtest_result.cost_returns,
        net_returns=backtest_result.net_returns,
    )


def calculate_momentum_top_k_returns(
    price_matrix: pd.DataFrame,
    lookback_days: int = 252,
    top_k: int = 5,
    rebalance_frequency: str = "ME",
) -> pd.Series:
    """Calculate gross top-K momentum returns using the legacy no-cost name."""
    result = calculate_momentum_top_k_result(
        price_matrix=price_matrix,
        lookback_days=lookback_days,
        top_k=top_k,
        rebalance_frequency=rebalance_frequency,
        transaction_cost_bps=0.0,
        include_initial_allocation_cost=False,
    )
    returns = result.gross_returns.copy()
    returns.name = f"momentum_top_{top_k}_{lookback_days}d"
    return returns


def calculate_baseline_return_series(
    prices: pd.DataFrame,
    benchmark_ticker: str,
    universe_tickers: list[str],
    price_column: str = "adjusted_close",
    include_momentum: bool = False,
    momentum_lookback_days: int = 252,
    momentum_top_k: int = 5,
    momentum_rebalance_frequency: str = "ME",
) -> dict[str, pd.Series]:
    """Calculate baseline return series for benchmark/equal-weight/momentum."""
    price_matrix = build_price_matrix(prices=prices, price_column=price_column)
    asset_returns = calculate_asset_returns(price_matrix)

    benchmark_returns = calculate_buy_and_hold_returns(
        asset_returns=asset_returns,
        ticker=benchmark_ticker,
    )
    equal_weight_returns = calculate_equal_weight_returns(
        asset_returns=asset_returns,
        tickers=universe_tickers,
    )

    baseline_returns = {
        benchmark_returns.name: benchmark_returns,
        equal_weight_returns.name: equal_weight_returns,
    }

    if include_momentum:
        momentum_returns = calculate_momentum_top_k_returns(
            price_matrix=price_matrix[universe_tickers],
            lookback_days=momentum_lookback_days,
            top_k=momentum_top_k,
            rebalance_frequency=momentum_rebalance_frequency,
        )
        baseline_returns[momentum_returns.name] = momentum_returns

    return baseline_returns
