from pathlib import Path

from src.config.settings import (
    load_evolutionary_config,
    load_universe_config,
    load_walk_forward_config,
)

ROOT = Path(__file__).resolve().parents[1]


def test_load_universe_config() -> None:
    config = load_universe_config(ROOT / "configs" / "universe_etf.yaml")

    assert config.project.name == "Evolutionary Quant Finance Research Pipeline"
    assert config.data.source == "yfinance"
    assert config.universe.benchmark == "SPY"
    assert config.universe.cash_proxy == "BIL"
    assert len(config.universe.tickers) >= 5


def test_load_walk_forward_config() -> None:
    config = load_walk_forward_config(ROOT / "configs" / "walk_forward.yaml")

    assert config.walk_forward.train_years > 0
    assert config.walk_forward.test_years > 0
    assert config.walk_forward.step_years > 0
    assert config.backtest.initial_capital > 0
    assert config.backtest.transaction_cost_bps >= 0
    assert 0 < config.backtest.max_asset_weight <= 1


def test_load_evolutionary_config() -> None:
    config = load_evolutionary_config(ROOT / "configs" / "evolutionary_nsga2.yaml")

    assert config.optimizer.algorithm == "NSGA2"
    assert config.optimizer.population_size > 0
    assert config.optimizer.generations > 0
    assert config.search_space.top_k_max >= config.search_space.top_k_min
    assert "sharpe" in config.objectives.maximize
    assert "max_drawdown" in config.objectives.minimize
