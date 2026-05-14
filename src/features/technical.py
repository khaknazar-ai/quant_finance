from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from src.config.settings import FeaturesConfig

TRADING_DAYS_PER_YEAR = 252


def build_technical_features(prices: pd.DataFrame, config: FeaturesConfig) -> pd.DataFrame:
    """Build leakage-safe technical features from canonical OHLCV prices.

    The function computes raw features from historical adjusted prices and then
    shifts all feature columns by config.leakage_control.shift_features_by_days
    within each ticker.

    This means a row for date t only contains signals that would have been known
    before date t.
    """
    _validate_required_columns(prices, required_columns=["date", "ticker", config.price_column])

    df = prices.sort_values(["ticker", "date"]).reset_index(drop=True).copy()
    price_column = config.price_column

    if (df[price_column] <= 0).any():
        raise ValueError(f"Price column must be strictly positive: {price_column}")

    df["daily_return_unshifted"] = df.groupby("ticker", observed=True)[price_column].pct_change()

    _add_return_features(df=df, price_column=price_column, windows=config.return_windows)
    _add_momentum_features(df=df, price_column=price_column, windows=config.momentum_windows)
    _add_volatility_features(df=df, windows=config.volatility_windows)
    _add_drawdown_features(df=df, price_column=price_column, windows=config.drawdown_windows)

    if config.ranking.enabled:
        _add_cross_sectional_ranks(df)

    feature_columns = get_feature_columns(df)

    shift_days = config.leakage_control.shift_features_by_days
    if shift_days > 0:
        df[feature_columns] = df.groupby("ticker", observed=True)[feature_columns].shift(shift_days)

    df = df.drop(columns=["daily_return_unshifted"])

    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return generated feature columns."""
    prefixes = (
        "return_",
        "momentum_",
        "volatility_",
        "drawdown_",
        "rank_",
    )
    return [column for column in df.columns if column.startswith(prefixes)]


def _add_return_features(df: pd.DataFrame, price_column: str, windows: Iterable[int]) -> None:
    for window in windows:
        df[f"return_{window}d"] = df.groupby("ticker", observed=True)[price_column].pct_change(
            periods=window
        )


def _add_momentum_features(df: pd.DataFrame, price_column: str, windows: Iterable[int]) -> None:
    for window in windows:
        df[f"momentum_{window}d"] = df.groupby("ticker", observed=True)[price_column].pct_change(
            periods=window
        )


def _add_volatility_features(df: pd.DataFrame, windows: Iterable[int]) -> None:
    grouped_returns = df.groupby("ticker", observed=True)["daily_return_unshifted"]

    for window in windows:
        df[f"volatility_{window}d"] = grouped_returns.rolling(
            window=window, min_periods=window
        ).std().reset_index(level=0, drop=True) * np.sqrt(TRADING_DAYS_PER_YEAR)


def _add_drawdown_features(df: pd.DataFrame, price_column: str, windows: Iterable[int]) -> None:
    grouped_prices = df.groupby("ticker", observed=True)[price_column]

    for window in windows:
        rolling_max = (
            grouped_prices.rolling(window=window, min_periods=window)
            .max()
            .reset_index(level=0, drop=True)
        )
        df[f"drawdown_{window}d"] = df[price_column] / rolling_max - 1.0


def _add_cross_sectional_ranks(df: pd.DataFrame) -> None:
    higher_is_better_prefixes = ("return_", "momentum_", "drawdown_")
    lower_is_better_prefixes = ("volatility_",)

    base_feature_columns = [
        column for column in get_feature_columns(df) if not column.startswith("rank_")
    ]

    for column in base_feature_columns:
        if column.startswith(higher_is_better_prefixes):
            ascending = True
        elif column.startswith(lower_is_better_prefixes):
            ascending = False
        else:
            continue

        df[f"rank_{column}"] = df.groupby("date", observed=True)[column].rank(
            method="average",
            pct=True,
            ascending=ascending,
        )


def _validate_required_columns(prices: pd.DataFrame, required_columns: Iterable[str]) -> None:
    missing_columns = sorted(set(required_columns) - set(prices.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns for feature engineering: {missing_columns}")
