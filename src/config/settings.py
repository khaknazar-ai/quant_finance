from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectConfig(StrictModel):
    name: str
    version: str


class DataConfig(StrictModel):
    source: str
    start_date: str
    end_date: str | None = None
    frequency: str = "1d"
    adjusted_prices: bool = True


class UniverseConfig(StrictModel):
    benchmark: str
    cash_proxy: str
    tickers: list[str]

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, tickers: list[str]) -> list[str]:
        if len(tickers) < 5:
            raise ValueError("ETF universe must contain at least 5 tickers.")
        if len(tickers) != len(set(tickers)):
            raise ValueError("ETF universe contains duplicate tickers.")
        return tickers


class QualityConfig(StrictModel):
    max_missing_ratio_per_ticker: float = Field(ge=0.0, le=1.0)
    max_duplicate_rows: int = Field(ge=0)
    allow_non_positive_prices: bool = False
    allow_negative_volume: bool = False


class UniverseFileConfig(StrictModel):
    project: ProjectConfig
    data: DataConfig
    universe: UniverseConfig
    quality: QualityConfig


class WalkForwardConfig(StrictModel):
    train_years: int = Field(gt=0)
    test_years: int = Field(gt=0)
    step_years: int = Field(gt=0)
    min_train_observations: int = Field(gt=0)
    rebalance_frequency: str


class BacktestConfig(StrictModel):
    initial_capital: float = Field(gt=0)
    transaction_cost_bps: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)
    allow_short: bool = False
    allow_leverage: bool = False
    max_asset_weight: float = Field(gt=0, le=1)


class WalkForwardFileConfig(StrictModel):
    walk_forward: WalkForwardConfig
    backtest: BacktestConfig


class RangeConfig(StrictModel):
    min: float
    max: float

    @field_validator("max")
    @classmethod
    def validate_range(cls, max_value: float, info: Any) -> float:
        min_value = info.data.get("min")
        if min_value is not None and max_value < min_value:
            raise ValueError("Range max must be greater than or equal to min.")
        return max_value


class OptimizerConfig(StrictModel):
    algorithm: str
    population_size: int = Field(gt=0)
    generations: int = Field(gt=0)
    random_seed: int


class SearchSpaceConfig(StrictModel):
    top_k_min: int = Field(gt=0)
    top_k_max: int = Field(gt=0)
    momentum_windows: RangeConfig
    volatility_windows: RangeConfig
    factor_weights: RangeConfig

    @field_validator("top_k_max")
    @classmethod
    def validate_top_k(cls, top_k_max: int, info: Any) -> int:
        top_k_min = info.data.get("top_k_min")
        if top_k_min is not None and top_k_max < top_k_min:
            raise ValueError("top_k_max must be greater than or equal to top_k_min.")
        return top_k_max


class ObjectivesConfig(StrictModel):
    maximize: list[str]
    minimize: list[str]


class ConstraintsConfig(StrictModel):
    max_drawdown_limit: float = Field(gt=0, le=1)
    max_annual_turnover: float = Field(gt=0)
    min_assets: int = Field(gt=0)
    long_only: bool = True


class EvolutionaryFileConfig(StrictModel):
    optimizer: OptimizerConfig
    search_space: SearchSpaceConfig
    objectives: ObjectivesConfig
    constraints: ConstraintsConfig


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")

    return data


def load_universe_config(path: str | Path) -> UniverseFileConfig:
    return UniverseFileConfig.model_validate(load_yaml(path))


def load_walk_forward_config(path: str | Path) -> WalkForwardFileConfig:
    return WalkForwardFileConfig.model_validate(load_yaml(path))


def load_evolutionary_config(path: str | Path) -> EvolutionaryFileConfig:
    return EvolutionaryFileConfig.model_validate(load_yaml(path))


class RankingConfig(StrictModel):
    enabled: bool
    cross_sectional: bool


class LeakageControlConfig(StrictModel):
    shift_features_by_days: int = Field(ge=0)
    reason: str


class FeaturesConfig(StrictModel):
    price_column: str
    return_windows: list[int]
    momentum_windows: list[int]
    volatility_windows: list[int]
    drawdown_windows: list[int]
    ranking: RankingConfig
    leakage_control: LeakageControlConfig

    @field_validator(
        "return_windows",
        "momentum_windows",
        "volatility_windows",
        "drawdown_windows",
    )
    @classmethod
    def validate_positive_unique_windows(cls, windows: list[int]) -> list[int]:
        if not windows:
            raise ValueError("Feature window list must not be empty.")
        if any(window <= 0 for window in windows):
            raise ValueError("Feature windows must be positive integers.")
        if len(windows) != len(set(windows)):
            raise ValueError("Feature windows must not contain duplicates.")
        return windows


class FeaturesFileConfig(StrictModel):
    features: FeaturesConfig


def load_features_config(path: str | Path) -> FeaturesFileConfig:
    return FeaturesFileConfig.model_validate(load_yaml(path))
