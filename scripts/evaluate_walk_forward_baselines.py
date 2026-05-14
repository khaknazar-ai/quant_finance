from __future__ import annotations

import argparse
import json
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

from scripts.evaluate_baselines import (
    align_return_series_to_common_window,
    make_json_safe_metrics,
    summarize_cost_impact,
)


def load_walk_forward_splits_report(path: Path) -> dict[str, Any]:
    """Load and validate the walk-forward split report."""
    report = json.loads(path.read_text(encoding="utf-8"))

    if "splits" not in report:
        raise ValueError("Walk-forward report must contain a 'splits' field.")

    if not report["splits"]:
        raise ValueError("Walk-forward report must contain at least one split.")

    return report


def build_cost_aware_baseline_returns(
    prices: pd.DataFrame,
    benchmark_ticker: str,
    universe_tickers: list[str],
    price_column: str = "adjusted_close",
    momentum_lookback_days: int = 252,
    momentum_top_k: int = 5,
    momentum_rebalance_frequency: str = "ME",
    transaction_cost_bps: float = 10.0,
) -> tuple[dict[str, pd.Series], Any]:
    """Build baseline return series and momentum cost-aware result."""
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
    momentum_result = calculate_momentum_top_k_result(
        price_matrix=price_matrix[universe_tickers],
        lookback_days=momentum_lookback_days,
        top_k=momentum_top_k,
        rebalance_frequency=momentum_rebalance_frequency,
        transaction_cost_bps=transaction_cost_bps,
        include_initial_allocation_cost=True,
    )

    baseline_returns = {
        benchmark_returns.name: benchmark_returns,
        equal_weight_returns.name: equal_weight_returns,
        momentum_result.gross_returns.name: momentum_result.gross_returns,
        momentum_result.net_returns.name: momentum_result.net_returns,
    }

    return baseline_returns, momentum_result


def filter_returns_to_test_window(
    return_series_by_strategy: dict[str, pd.Series],
    test_start: str,
    test_end: str,
) -> dict[str, pd.Series]:
    """Filter strategy returns to a test window and align exact shared dates."""
    start = pd.Timestamp(test_start)
    end = pd.Timestamp(test_end)

    if end < start:
        raise ValueError("test_end must be greater than or equal to test_start.")

    filtered_returns: dict[str, pd.Series] = {}
    for strategy_name, returns in return_series_by_strategy.items():
        filtered = returns.loc[(returns.index >= start) & (returns.index <= end)]
        if filtered.empty:
            raise ValueError(f"No returns for {strategy_name} in {test_start} -> {test_end}.")
        filtered_returns[strategy_name] = filtered

    return align_return_series_to_common_window(filtered_returns)


def aggregate_metrics_by_strategy(
    split_reports: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Aggregate split-level metrics by strategy."""
    strategy_names = sorted(
        {
            strategy_name
            for split_report in split_reports
            for strategy_name in split_report["metrics"]
        }
    )

    aggregate: dict[str, dict[str, Any]] = {}

    for strategy_name in strategy_names:
        strategy_split_metrics = [
            (split_report["split_id"], split_report["metrics"][strategy_name])
            for split_report in split_reports
            if strategy_name in split_report["metrics"]
        ]

        metric_names = sorted(
            {
                metric_name
                for _, metrics in strategy_split_metrics
                for metric_name in metrics
                if isinstance(metrics[metric_name], int | float)
            }
        )

        strategy_summary: dict[str, Any] = {
            "split_count": len(strategy_split_metrics),
            "metrics": {},
        }

        for metric_name in metric_names:
            values = [
                float(metrics[metric_name])
                for _, metrics in strategy_split_metrics
                if metrics.get(metric_name) is not None
            ]

            if not values:
                continue

            value_series = pd.Series(values, dtype="float64")
            strategy_summary["metrics"][metric_name] = {
                "mean": float(value_series.mean()),
                "std": float(value_series.std(ddof=0)),
                "min": float(value_series.min()),
                "max": float(value_series.max()),
            }

        cagr_records = [
            (split_id, float(metrics["cagr"]))
            for split_id, metrics in strategy_split_metrics
            if metrics.get("cagr") is not None
        ]

        if cagr_records:
            strategy_summary["positive_cagr_split_fraction"] = float(
                sum(cagr > 0.0 for _, cagr in cagr_records) / len(cagr_records)
            )
            strategy_summary["best_cagr_split_id"] = max(
                cagr_records,
                key=lambda item: item[1],
            )[0]
            strategy_summary["worst_cagr_split_id"] = min(
                cagr_records,
                key=lambda item: item[1],
            )[0]

        aggregate[strategy_name] = strategy_summary

    return aggregate


def build_walk_forward_baseline_report(
    prices: pd.DataFrame,
    splits_report: dict[str, Any],
    benchmark_ticker: str,
    universe_tickers: list[str],
    price_column: str = "adjusted_close",
    risk_free_rate: float = 0.0,
    momentum_lookback_days: int = 252,
    momentum_top_k: int = 5,
    momentum_rebalance_frequency: str = "ME",
    transaction_cost_bps: float = 10.0,
) -> dict[str, Any]:
    """Evaluate baseline strategies on each walk-forward OOS test split."""
    baseline_returns, momentum_result = build_cost_aware_baseline_returns(
        prices=prices,
        benchmark_ticker=benchmark_ticker,
        universe_tickers=universe_tickers,
        price_column=price_column,
        momentum_lookback_days=momentum_lookback_days,
        momentum_top_k=momentum_top_k,
        momentum_rebalance_frequency=momentum_rebalance_frequency,
        transaction_cost_bps=transaction_cost_bps,
    )

    split_level_reports: list[dict[str, Any]] = []

    for split in splits_report["splits"]:
        aligned_returns = filter_returns_to_test_window(
            return_series_by_strategy=baseline_returns,
            test_start=split["test_start"],
            test_end=split["test_end"],
        )

        common_index = next(iter(aligned_returns.values())).index

        metrics_by_strategy: dict[str, dict[str, float | int | None]] = {}
        for strategy_name, returns in aligned_returns.items():
            metrics = calculate_performance_metrics(
                returns=returns,
                risk_free_rate=risk_free_rate,
            )
            metrics_by_strategy[strategy_name] = make_json_safe_metrics(metrics.to_dict())

        split_level_reports.append(
            {
                "split_id": split["split_id"],
                "train_start": split["train_start"],
                "train_end": split["train_end"],
                "test_start": split["test_start"],
                "test_end": split["test_end"],
                "common_start_date": str(common_index.min().date()),
                "common_end_date": str(common_index.max().date()),
                "common_observation_count": int(len(common_index)),
                "momentum_cost_summary": summarize_cost_impact(
                    turnover=momentum_result.turnover,
                    cost_returns=momentum_result.cost_returns,
                    common_index=common_index,
                ),
                "metrics": metrics_by_strategy,
            }
        )

    aggregate_metrics = aggregate_metrics_by_strategy(split_level_reports)

    strategy_names = sorted(next(iter(split_level_reports))["metrics"])

    return {
        "evaluation_type": "walk_forward_baseline_oos",
        "benchmark_ticker": benchmark_ticker,
        "universe_tickers": universe_tickers,
        "price_column": price_column,
        "risk_free_rate": risk_free_rate,
        "return_alignment": "exact_common_date_intersection_per_split",
        "requested_split_count": len(splits_report["splits"]),
        "evaluated_split_count": len(split_level_reports),
        "strategy_count": len(strategy_names),
        "strategies": strategy_names,
        "momentum_lookback_days": momentum_lookback_days,
        "momentum_top_k": momentum_top_k,
        "momentum_rebalance_frequency": momentum_rebalance_frequency,
        "transaction_cost_bps": transaction_cost_bps,
        "cost_model": "net_return = gross_return - turnover * bps / 10000",
        "turnover_convention": "sum_abs_weight_change",
        "splits": split_level_reports,
        "aggregate_metrics": aggregate_metrics,
    }


def run_evaluate_walk_forward_baselines(
    input_path: Path,
    universe_config_path: Path,
    splits_path: Path,
    output_path: Path,
) -> None:
    """Run walk-forward baseline evaluation and save a JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prices = pd.read_parquet(input_path)
    validated_prices = validate_price_frame(prices)
    universe_config = load_universe_config(universe_config_path)
    splits_report = load_walk_forward_splits_report(splits_path)

    report = build_walk_forward_baseline_report(
        prices=validated_prices,
        splits_report=splits_report,
        benchmark_ticker=universe_config.universe.benchmark,
        universe_tickers=universe_config.universe.tickers,
        price_column="adjusted_close",
        risk_free_rate=0.0,
        momentum_lookback_days=252,
        momentum_top_k=5,
        momentum_rebalance_frequency="ME",
        transaction_cost_bps=10.0,
    )

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved walk-forward baseline metrics to: {output_path}")
    print(f"Evaluation type: {report['evaluation_type']}")
    print(f"Return alignment: {report['return_alignment']}")
    print(f"Evaluated splits: {report['evaluated_split_count']}")
    print(f"Strategy count: {report['strategy_count']}")

    for strategy_name in report["strategies"]:
        cagr_mean = report["aggregate_metrics"][strategy_name]["metrics"]["cagr"]["mean"]
        sharpe_mean = report["aggregate_metrics"][strategy_name]["metrics"]["sharpe"]["mean"]
        maxdd_mean = report["aggregate_metrics"][strategy_name]["metrics"]["max_drawdown"]["mean"]
        positive_fraction = report["aggregate_metrics"][strategy_name].get(
            "positive_cagr_split_fraction"
        )
        print(
            f"{strategy_name}: "
            f"mean_CAGR={cagr_mean}, "
            f"mean_Sharpe={sharpe_mean}, "
            f"mean_MaxDD={maxdd_mean}, "
            f"positive_CAGR_fraction={positive_fraction}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate baseline strategies on walk-forward OOS splits."
    )
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
        "--splits",
        type=Path,
        default=Path("reports/walk_forward_splits.json"),
        help="Walk-forward split report JSON path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/walk_forward_baseline_metrics.json"),
        help="Output walk-forward baseline metrics JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_evaluate_walk_forward_baselines(
        input_path=args.input,
        universe_config_path=args.universe_config,
        splits_path=args.splits,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
