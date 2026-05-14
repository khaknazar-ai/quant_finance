from __future__ import annotations

from pathlib import Path


def replace_imports(text: str) -> str:
    """Replace direct cost-model imports with generic backtest engine import."""
    old = """from src.backtesting.costs import (
    calculate_net_returns_after_costs,
    calculate_transaction_cost_returns,
    calculate_turnover,
)
"""
    new = "from src.backtesting.engine import run_rebalanced_backtest\n"

    if old not in text:
        raise ValueError("Expected direct cost import block not found in baselines.py.")

    return text.replace(old, new)


def replace_momentum_result_function(text: str) -> str:
    """Replace hand-written momentum backtest logic with generic engine call."""
    start_marker = "def calculate_momentum_top_k_result("
    end_marker = "\n\ndef calculate_momentum_top_k_returns("

    start = text.find(start_marker)
    end = text.find(end_marker)

    if start == -1:
        raise ValueError("calculate_momentum_top_k_result start marker not found.")

    if end == -1:
        raise ValueError("calculate_momentum_top_k_returns end marker not found.")

    new_function = '''def calculate_momentum_top_k_result(
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
'''

    return text[:start] + new_function + text[end:]


def patch_baselines(project_root: Path) -> None:
    """Patch src/strategies/baselines.py."""
    path = project_root / "src" / "strategies" / "baselines.py"
    text = path.read_text(encoding="utf-8")

    text = replace_imports(text)
    text = replace_momentum_result_function(text)

    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_baselines(project_root=Path("."))


if __name__ == "__main__":
    main()
