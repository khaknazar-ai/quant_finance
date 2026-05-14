from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
from src.config.settings import load_universe_config
from src.risk.metrics import calculate_performance_metrics
from src.strategies.baselines import (
    build_price_matrix,
    calculate_asset_returns,
    calculate_buy_and_hold_returns,
    calculate_equal_weight_returns,
    calculate_momentum_top_k_result,
)
from src.validation.schemas import validate_price_frame


def make_json_safe_metrics(metrics: dict[str, float | int]) -> dict[str, float | int | None]:
    """Convert NaN/inf metric values to None before JSON serialization."""
    safe_metrics: dict[str, float | int | None] = {}

    for key, value in metrics.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            safe_metrics[key] = None
        else:
            safe_metrics[key] = value

    return safe_metrics


def align_return_series_to_common_window(
    return_series_by_strategy: dict[str, pd.Series],
) -> dict[str, pd.Series]:
    """Align all strategy returns to the exact shared date intersection."""
    if not return_series_by_strategy:
        raise ValueError("return_series_by_strategy must not be empty.")

    cleaned_returns: dict[str, pd.Series] = {}
    common_dates: set[pd.Timestamp] | None = None

    for strategy_name, returns in return_series_by_strategy.items():
        if not isinstance(returns.index, pd.DatetimeIndex):
            raise ValueError(f"Returns index must be a DatetimeIndex for {strategy_name}.")

        if returns.index.has_duplicates:
            raise ValueError(f"Returns index contains duplicate dates for {strategy_name}.")

        clean_returns = pd.to_numeric(returns, errors="coerce").dropna().sort_index()
        if clean_returns.empty:
            raise ValueError(f"No valid returns available for {strategy_name}.")

        cleaned_returns[strategy_name] = clean_returns
        strategy_dates = set(pd.DatetimeIndex(clean_returns.index))
        common_dates = strategy_dates if common_dates is None else common_dates & strategy_dates

    if not common_dates:
        raise ValueError("No overlapping return dates across strategies.")

    common_index = pd.DatetimeIndex(sorted(common_dates))

    aligned_returns: dict[str, pd.Series] = {}
    for strategy_name, returns in cleaned_returns.items():
        strategy_returns = returns.reindex(common_index).dropna()

        if strategy_returns.empty:
            raise ValueError(f"No aligned returns available for {strategy_name}.")

        if len(strategy_returns) != len(common_index):
            raise ValueError(f"Aligned returns contain missing dates for {strategy_name}.")

        aligned_returns[strategy_name] = strategy_returns

    return aligned_returns


def summarize_cost_impact(
    turnover: pd.Series,
    cost_returns: pd.Series,
    common_index: pd.DatetimeIndex,
) -> dict[str, float | int]:
    """Summarize transaction cost impact on the aligned evaluation window."""
    aligned_turnover = turnover.reindex(common_index).fillna(0.0)
    aligned_cost_returns = cost_returns.reindex(common_index).fillna(0.0)

    return {
        "average_turnover": float(aligned_turnover.mean()),
        "total_turnover": float(aligned_turnover.sum()),
        "average_transaction_cost_return": float(aligned_cost_returns.mean()),
        "total_transaction_cost_return": float(aligned_cost_returns.sum()),
        "cost_observation_count": int(len(common_index)),
    }


def build_baseline_metrics_report(
    prices: pd.DataFrame,
    benchmark_ticker: str,
    universe_tickers: list[str],
    price_column: str = "adjusted_close",
    risk_free_rate: float = 0.0,
    include_momentum: bool = True,
    momentum_lookback_days: int = 252,
    momentum_top_k: int = 5,
    momentum_rebalance_frequency: str = "ME",
    transaction_cost_bps: float = 10.0,
) -> dict[str, Any]:
    """Build comparable performance metrics report for baseline strategies."""
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

    baseline_returns: dict[str, pd.Series] = {
        benchmark_returns.name: benchmark_returns,
        equal_weight_returns.name: equal_weight_returns,
    }
    momentum_cost_summary: dict[str, float | int] | None = None

    if include_momentum:
        momentum_result = calculate_momentum_top_k_result(
            price_matrix=price_matrix[universe_tickers],
            lookback_days=momentum_lookback_days,
            top_k=momentum_top_k,
            rebalance_frequency=momentum_rebalance_frequency,
            transaction_cost_bps=transaction_cost_bps,
            include_initial_allocation_cost=True,
        )
        baseline_returns[momentum_result.gross_returns.name] = momentum_result.gross_returns
        baseline_returns[momentum_result.net_returns.name] = momentum_result.net_returns

    aligned_returns = align_return_series_to_common_window(baseline_returns)

    common_index = next(iter(aligned_returns.values())).index
    common_start = common_index.min()
    common_end = common_index.max()

    if include_momentum:
        momentum_cost_summary = summarize_cost_impact(
            turnover=momentum_result.turnover,
            cost_returns=momentum_result.cost_returns,
            common_index=common_index,
        )

    metrics_by_strategy: dict[str, dict[str, float | int | None]] = {}
    date_ranges: dict[str, dict[str, str]] = {}

    for strategy_name, returns in aligned_returns.items():
        metrics = calculate_performance_metrics(
            returns=returns,
            risk_free_rate=risk_free_rate,
        )
        metrics_by_strategy[strategy_name] = make_json_safe_metrics(metrics.to_dict())

        date_ranges[strategy_name] = {
            "start": str(returns.index.min().date()),
            "end": str(returns.index.max().date()),
        }

    return {
        "benchmark_ticker": benchmark_ticker,
        "universe_tickers": universe_tickers,
        "price_column": price_column,
        "risk_free_rate": risk_free_rate,
        "return_alignment": "exact_common_date_intersection",
        "common_start_date": str(common_start.date()),
        "common_end_date": str(common_end.date()),
        "common_observation_count": int(len(common_index)),
        "include_momentum": include_momentum,
        "momentum_lookback_days": momentum_lookback_days,
        "momentum_top_k": momentum_top_k,
        "momentum_rebalance_frequency": momentum_rebalance_frequency,
        "transaction_cost_bps": transaction_cost_bps,
        "cost_model": "net_return = gross_return - turnover * bps / 10000",
        "turnover_convention": "sum_abs_weight_change",
        "momentum_cost_summary": momentum_cost_summary,
        "strategy_count": len(metrics_by_strategy),
        "date_ranges": date_ranges,
        "metrics": metrics_by_strategy,
    }


def run_evaluate_baselines(
    input_path: Path,
    universe_config_path: Path,
    output_path: Path,
) -> None:
    """Read validated prices, evaluate baseline strategies, and save JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prices = pd.read_parquet(input_path)
    validated_prices = validate_price_frame(prices)

    universe_config = load_universe_config(universe_config_path)

    report = build_baseline_metrics_report(
        prices=validated_prices,
        benchmark_ticker=universe_config.universe.benchmark,
        universe_tickers=universe_config.universe.tickers,
        price_column="adjusted_close",
        risk_free_rate=0.0,
        include_momentum=True,
        momentum_lookback_days=252,
        momentum_top_k=5,
        momentum_rebalance_frequency="ME",
        transaction_cost_bps=10.0,
    )

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved baseline metrics to: {output_path}")
    print(f"Benchmark: {report['benchmark_ticker']}")
    print(f"Universe size: {len(report['universe_tickers'])}")
    print(f"Return alignment: {report['return_alignment']}")
    print(f"Common date range: {report['common_start_date']} -> {report['common_end_date']}")
    print(f"Common observations: {report['common_observation_count']}")
    print(f"Transaction cost bps: {report['transaction_cost_bps']}")
    print(f"Strategy count: {report['strategy_count']}")

    for strategy_name, metrics in report["metrics"].items():
        print(
            f"{strategy_name}: "
            f"CAGR={metrics['cagr']}, "
            f"Sharpe={metrics['sharpe']}, "
            f"MaxDD={metrics['max_drawdown']}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate baseline portfolio strategies.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
        help="Input validated OHLCV parquet path.",
    )
    parser.add_argument(
        "--universe-config",
        type=Path,
        default=Path("configs/universe_etf.yaml"),
        help="Universe config YAML path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/baseline_metrics.json"),
        help="Output baseline metrics JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_evaluate_baselines(
        input_path=args.input,
        universe_config_path=args.universe_config,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
