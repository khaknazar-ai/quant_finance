from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.backtesting.engine import run_rebalanced_backtest
from src.optimization.nsga2_optimizer import NSGA2SearchSpace, run_nsga2_train_optimizer
from src.strategies.baselines import (
    calculate_asset_returns,
    calculate_buy_and_hold_returns,
    calculate_equal_weight_returns,
    calculate_momentum_top_k_weights,
)
from src.strategies.factor_rotation import FactorRotationParameters

from scripts.evaluate_factor_rotation_grid_smoke import (
    format_float,
    format_percent,
    load_universe_price_matrix,
)
from scripts.run_one_split_optimizer_selection import (
    align_return_series_to_common_index,
    build_metrics_for_return_series,
    calculate_selected_degradation,
    evaluate_selected_factor_rotation_on_test_window,
    find_test_metric_leaders,
    load_train_test_window_from_split_report,
    select_evaluation_by_metric,
)


def build_test_baseline_returns(
    price_matrix: pd.DataFrame,
    test_start: str,
    test_end: str,
    benchmark_ticker: str,
    transaction_cost_bps: float,
    momentum_lookback_days: int,
    momentum_top_k: int,
    momentum_rebalance_frequency: str,
) -> dict[str, pd.Series]:
    """Build OOS baseline returns for one test window.

    Momentum uses price context before test_start for lookback calculation,
    but target rebalance decisions are restricted to the OOS test window.
    """
    test_start_ts = pd.Timestamp(test_start)
    test_end_ts = pd.Timestamp(test_end)
    context_prices = price_matrix.loc[:test_end_ts]

    asset_returns_all = calculate_asset_returns(context_prices)
    test_asset_returns = asset_returns_all.loc[
        (asset_returns_all.index >= test_start_ts) & (asset_returns_all.index <= test_end_ts)
    ]

    baseline_returns = {
        f"buy_hold_{benchmark_ticker}": calculate_buy_and_hold_returns(
            asset_returns=test_asset_returns,
            ticker=benchmark_ticker,
        ),
        "equal_weight": calculate_equal_weight_returns(
            asset_returns=test_asset_returns,
        ),
    }

    momentum_weights_all = calculate_momentum_top_k_weights(
        price_matrix=context_prices,
        lookback_days=momentum_lookback_days,
        top_k=momentum_top_k,
        rebalance_frequency=momentum_rebalance_frequency,
    )
    momentum_target_weights = momentum_weights_all.loc[
        (momentum_weights_all.index >= test_start_ts) & (momentum_weights_all.index <= test_end_ts)
    ].dropna(how="all")

    if not momentum_target_weights.empty:
        strategy_name = f"momentum_top_{momentum_top_k}_{momentum_lookback_days}d"
        momentum_result = run_rebalanced_backtest(
            asset_returns=test_asset_returns,
            target_weights=momentum_target_weights,
            strategy_name=strategy_name,
            transaction_cost_bps=transaction_cost_bps,
            execution_lag_days=1,
            include_initial_allocation_cost=True,
            max_leverage=1.0,
        )

        gross_returns = momentum_result.gross_returns.copy()
        gross_returns.name = f"{strategy_name}_gross"
        net_returns = momentum_result.net_returns.copy()
        net_returns.name = f"{strategy_name}_net_{transaction_cost_bps:g}bps"

        baseline_returns[gross_returns.name] = gross_returns
        baseline_returns[net_returns.name] = net_returns

    return baseline_returns


def sanitize_selected_test_evaluation(
    selected_test_evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Remove non-JSON return series from selected test evaluation."""
    return {key: value for key, value in selected_test_evaluation.items() if key != "net_returns"}


def sanitize_train_evaluation(
    selected_train_evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Remove optimizer vector from selected train evaluation."""
    return {
        key: value for key, value in selected_train_evaluation.items() if key != "optimizer_vector"
    }


def run_single_walk_forward_optimizer_split(
    price_matrix: pd.DataFrame,
    split_window: dict[str, str],
    split_index: int,
    population_size: int,
    generations: int,
    seed: int,
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_train_return_observations: int,
    min_test_return_observations: int,
    selection_metric: str,
    benchmark_ticker: str,
    momentum_lookback_days: int,
    momentum_top_k: int,
    momentum_rebalance_frequency: str,
) -> dict[str, Any]:
    """Run optimizer train selection and OOS test evaluation for one split."""
    search_space = NSGA2SearchSpace(
        top_k_max=min(6, len(price_matrix.columns)),
    )

    optimizer_result = run_nsga2_train_optimizer(
        price_matrix=price_matrix,
        train_start=split_window["train_start"],
        train_end=split_window["train_end"],
        search_space=search_space,
        population_size=population_size,
        generations=generations,
        seed=seed,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        min_return_observations=min_train_return_observations,
    )

    selected_train_evaluation = select_evaluation_by_metric(
        evaluations=optimizer_result["all_evaluations"],
        metric_name=selection_metric,
        maximize=True,
    )
    selected_parameters = FactorRotationParameters(**selected_train_evaluation["parameters"])

    selected_test_evaluation = evaluate_selected_factor_rotation_on_test_window(
        price_matrix=price_matrix,
        parameters=selected_parameters,
        test_start=split_window["test_start"],
        test_end=split_window["test_end"],
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        min_test_return_observations=min_test_return_observations,
    )

    if not selected_test_evaluation["valid"]:
        raise ValueError(
            f"Split {split_index} selected candidate failed OOS evaluation: "
            f"{selected_test_evaluation['invalid_reason']}"
        )

    baseline_returns = build_test_baseline_returns(
        price_matrix=price_matrix,
        test_start=split_window["test_start"],
        test_end=split_window["test_end"],
        benchmark_ticker=benchmark_ticker,
        transaction_cost_bps=transaction_cost_bps,
        momentum_lookback_days=momentum_lookback_days,
        momentum_top_k=momentum_top_k,
        momentum_rebalance_frequency=momentum_rebalance_frequency,
    )

    return_series = {
        "optimizer_selected_net": selected_test_evaluation["net_returns"],
        **baseline_returns,
    }
    aligned_returns, common_index = align_return_series_to_common_index(return_series)
    test_common_metrics = build_metrics_for_return_series(
        aligned_returns=aligned_returns,
        risk_free_rate=risk_free_rate,
    )

    return {
        "split_index": split_index,
        "train_start": split_window["train_start"],
        "train_end": split_window["train_end"],
        "test_start": split_window["test_start"],
        "test_end": split_window["test_end"],
        "optimizer_summary": {
            "population_size": optimizer_result["population_size"],
            "generations": optimizer_result["generations"],
            "seed": optimizer_result["seed"],
            "evaluation_count": optimizer_result["evaluation_count"],
            "valid_evaluation_count": optimizer_result["valid_evaluation_count"],
            "invalid_evaluation_count": optimizer_result["invalid_evaluation_count"],
            "pareto_candidate_count": optimizer_result["pareto_candidate_count"],
        },
        "selected_train_evaluation": sanitize_train_evaluation(selected_train_evaluation),
        "selected_test_evaluation": sanitize_selected_test_evaluation(selected_test_evaluation),
        "selected_metric_degradation": calculate_selected_degradation(
            train_metrics=selected_train_evaluation["metrics"],
            test_metrics=selected_test_evaluation["metrics"],
        ),
        "test_common_window": {
            "start": str(common_index.min().date()),
            "end": str(common_index.max().date()),
            "observation_count": int(len(common_index)),
        },
        "test_common_metrics": test_common_metrics,
        "test_common_metric_leaders": find_test_metric_leaders(test_common_metrics),
    }


def finite_metric_values(
    split_reports: list[dict[str, Any]],
    strategy_name: str,
    metric_name: str,
) -> list[float]:
    """Collect finite metric values for one strategy across split reports."""
    values: list[float] = []

    for split_report in split_reports:
        metrics = split_report["test_common_metrics"].get(strategy_name)
        if metrics is None:
            continue

        value = metrics.get(metric_name)
        if value is not None:
            values.append(float(value))

    return values


def aggregate_metrics_by_strategy(
    split_reports: list[dict[str, Any]],
) -> dict[str, dict[str, float | int | None]]:
    """Aggregate OOS test metrics by strategy across all splits."""
    strategy_names = sorted(
        {
            strategy_name
            for split_report in split_reports
            for strategy_name in split_report["test_common_metrics"]
        }
    )
    metric_names = ["cagr", "sharpe", "max_drawdown", "calmar", "final_equity"]

    aggregate: dict[str, dict[str, float | int | None]] = {}

    for strategy_name in strategy_names:
        strategy_aggregate: dict[str, float | int | None] = {
            "evaluated_split_count": 0,
        }

        cagr_values = finite_metric_values(split_reports, strategy_name, "cagr")
        strategy_aggregate["evaluated_split_count"] = len(cagr_values)
        strategy_aggregate["positive_cagr_fraction"] = (
            sum(value > 0 for value in cagr_values) / len(cagr_values) if cagr_values else None
        )

        for metric_name in metric_names:
            values = finite_metric_values(split_reports, strategy_name, metric_name)
            if values:
                series = pd.Series(values, dtype="float64")
                strategy_aggregate[f"mean_{metric_name}"] = float(series.mean())
                strategy_aggregate[f"median_{metric_name}"] = float(series.median())
                strategy_aggregate[f"min_{metric_name}"] = float(series.min())
                strategy_aggregate[f"max_{metric_name}"] = float(series.max())
            else:
                strategy_aggregate[f"mean_{metric_name}"] = None
                strategy_aggregate[f"median_{metric_name}"] = None
                strategy_aggregate[f"min_{metric_name}"] = None
                strategy_aggregate[f"max_{metric_name}"] = None

        aggregate[strategy_name] = strategy_aggregate

    return aggregate


def count_split_metric_winners(
    split_reports: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Count which strategy wins each metric leader label across splits."""
    winner_counts: dict[str, dict[str, int]] = {}

    for split_report in split_reports:
        for leader_name, leader in split_report["test_common_metric_leaders"].items():
            if leader is None:
                continue

            strategy_name = leader["strategy_name"]
            winner_counts.setdefault(leader_name, {})
            winner_counts[leader_name][strategy_name] = (
                winner_counts[leader_name].get(strategy_name, 0) + 1
            )

    return winner_counts


def aggregate_selected_degradation(
    split_reports: list[dict[str, Any]],
) -> dict[str, float | None]:
    """Aggregate selected candidate test-minus-train deltas."""
    degradation_keys = sorted(
        {
            key
            for split_report in split_reports
            for key in split_report["selected_metric_degradation"]
        }
    )
    aggregate: dict[str, float | None] = {}

    for key in degradation_keys:
        values = [
            float(split_report["selected_metric_degradation"][key])
            for split_report in split_reports
            if split_report["selected_metric_degradation"].get(key) is not None
        ]
        aggregate[f"mean_{key}"] = (
            float(pd.Series(values, dtype="float64").mean()) if values else None
        )

    return aggregate


def build_walk_forward_optimizer_report(
    split_reports: list[dict[str, Any]],
    selection_metric: str,
    transaction_cost_bps: float,
    risk_free_rate: float,
    population_size: int,
    generations: int,
    base_seed: int,
    momentum_lookback_days: int,
    momentum_top_k: int,
    momentum_rebalance_frequency: str,
) -> dict[str, Any]:
    """Build full walk-forward optimizer selection report."""
    return {
        "evaluation_type": "walk_forward_optimizer_selection_oos",
        "protocol": (
            "For each split, NSGA-II is fit only on the train window. "
            "A single candidate is selected by a fixed train metric before "
            "the test window is evaluated. Test data is not used for selection."
        ),
        "selection_rule": {
            "metric": selection_metric,
            "direction": "maximize",
            "candidate_pool": "all_valid_train_evaluations",
            "test_data_used_for_selection": False,
        },
        "optimizer_config": {
            "population_size": population_size,
            "generations": generations,
            "base_seed": base_seed,
            "seed_policy": "base_seed + split_index",
        },
        "baseline_config": {
            "benchmark_ticker": "SPY",
            "momentum_lookback_days": momentum_lookback_days,
            "momentum_top_k": momentum_top_k,
            "momentum_rebalance_frequency": momentum_rebalance_frequency,
            "transaction_cost_bps": transaction_cost_bps,
        },
        "risk_free_rate": risk_free_rate,
        "evaluated_split_count": len(split_reports),
        "split_reports": split_reports,
        "aggregate_test_metrics": aggregate_metrics_by_strategy(split_reports),
        "split_metric_winner_counts": count_split_metric_winners(split_reports),
        "aggregate_selected_degradation": aggregate_selected_degradation(split_reports),
        "interpretation_rule": (
            "This is walk-forward OOS evidence, but it is still historical "
            "backtest evidence. Do not claim production trading performance. "
            "If optimizer wins only risk metrics but loses CAGR, describe it "
            "as a risk-return trade-off, not general outperformance."
        ),
    }


def build_walk_forward_optimizer_summary(report: dict[str, Any]) -> str:
    """Build Markdown summary for full walk-forward optimizer selection."""
    lines = [
        "# Walk-Forward Optimizer Selection OOS Report",
        "",
        "## Protocol",
        "",
        "- Evaluation type: `walk_forward_optimizer_selection_oos`.",
        "- For each split, NSGA-II is fit only on the train window.",
        "- Candidate selection uses a fixed train metric before test evaluation.",
        "- Test data is not used for candidate selection.",
        f"- Selection metric: `{report['selection_rule']['metric']}`.",
        f"- Evaluated splits: `{report['evaluated_split_count']}`.",
        f"- Population size: `{report['optimizer_config']['population_size']}`.",
        f"- Generations: `{report['optimizer_config']['generations']}`.",
        f"- Seed policy: `{report['optimizer_config']['seed_policy']}`.",
        f"- Transaction cost: " f"`{report['baseline_config']['transaction_cost_bps']}` bps.",
        "",
        "## Aggregate OOS Metrics",
        "",
        (
            "| Strategy | Mean CAGR | Mean Sharpe | Mean MaxDD | Mean Calmar | "
            "Positive CAGR Fraction | Splits |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for strategy_name, metrics in report["aggregate_test_metrics"].items():
        lines.append(
            "| "
            f"`{strategy_name}` | "
            f"{format_percent(metrics.get('mean_cagr'))} | "
            f"{format_float(metrics.get('mean_sharpe'))} | "
            f"{format_percent(metrics.get('mean_max_drawdown'))} | "
            f"{format_float(metrics.get('mean_calmar'))} | "
            f"{format_percent(metrics.get('positive_cagr_fraction'))} | "
            f"{metrics.get('evaluated_split_count')} |"
        )

    lines.extend(
        [
            "",
            "## Split Metric Winner Counts",
            "",
        ]
    )

    for leader_name, counts in report["split_metric_winner_counts"].items():
        formatted_counts = ", ".join(
            f"`{strategy}`: {count}" for strategy, count in sorted(counts.items())
        )
        lines.append(f"- {leader_name}: {formatted_counts}")

    lines.extend(
        [
            "",
            "## Selected Candidate Train-to-Test Degradation",
            "",
        ]
    )

    for key, value in report["aggregate_selected_degradation"].items():
        if "sharpe" in key or "calmar" in key:
            formatted_value = format_float(value)
        else:
            formatted_value = format_percent(value)
        lines.append(f"- {key}: {formatted_value}")

    lines.extend(
        [
            "",
            "## Split-Level Selected Strategy Results",
            "",
            "| Split | Test Window | Selected Candidate | Test CAGR | "
            "Test Sharpe | Test MaxDD | Common Window |",
            "|---:|---|---|---:|---:|---:|---|",
        ]
    )

    for split_report in report["split_reports"]:
        selected = split_report["selected_train_evaluation"]
        test_metrics = split_report["selected_test_evaluation"]["metrics"]
        common = split_report["test_common_window"]
        lines.append(
            "| "
            f"{split_report['split_index']} | "
            f"`{split_report['test_start']}` to `{split_report['test_end']}` | "
            f"`{selected['candidate_id']}` | "
            f"{format_percent(test_metrics.get('cagr'))} | "
            f"{format_float(test_metrics.get('sharpe'))} | "
            f"{format_percent(test_metrics.get('max_drawdown'))} | "
            f"`{common['start']}` to `{common['end']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "This report is the first full walk-forward optimizer-selection "
            "evidence. It must be interpreted against baselines. If the "
            "optimizer has lower CAGR but better drawdown or Calmar, describe "
            "that as a risk-control trade-off, not broad outperformance.",
            "",
        ]
    )

    return "\n".join(lines)


def run_walk_forward_optimizer_selection(
    prices_path: Path,
    universe_config_path: Path,
    split_report_path: Path,
    output_path: Path,
    summary_output_path: Path,
    population_size: int,
    generations: int,
    base_seed: int,
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_train_return_observations: int,
    min_test_return_observations: int,
    selection_metric: str,
    benchmark_ticker: str,
    momentum_lookback_days: int,
    momentum_top_k: int,
    momentum_rebalance_frequency: str,
    max_splits: int | None,
) -> dict[str, Any]:
    """Run walk-forward optimizer selection across all configured splits."""
    split_report = json.loads(split_report_path.read_text(encoding="utf-8"))
    split_count = len(split_report["splits"])
    if max_splits is not None:
        split_count = min(split_count, max_splits)

    price_matrix = load_universe_price_matrix(
        prices_path=prices_path,
        universe_config_path=universe_config_path,
    )

    split_reports: list[dict[str, Any]] = []

    for split_index in range(split_count):
        split_window = load_train_test_window_from_split_report(
            split_report_path=split_report_path,
            split_index=split_index,
        )

        print(
            "Running split "
            f"{split_index}: train {split_window['train_start']} -> "
            f"{split_window['train_end']}, test {split_window['test_start']} -> "
            f"{split_window['test_end']}"
        )

        split_reports.append(
            run_single_walk_forward_optimizer_split(
                price_matrix=price_matrix,
                split_window=split_window,
                split_index=split_index,
                population_size=population_size,
                generations=generations,
                seed=base_seed + split_index,
                transaction_cost_bps=transaction_cost_bps,
                risk_free_rate=risk_free_rate,
                min_train_return_observations=min_train_return_observations,
                min_test_return_observations=min_test_return_observations,
                selection_metric=selection_metric,
                benchmark_ticker=benchmark_ticker,
                momentum_lookback_days=momentum_lookback_days,
                momentum_top_k=momentum_top_k,
                momentum_rebalance_frequency=momentum_rebalance_frequency,
            )
        )

    report = build_walk_forward_optimizer_report(
        split_reports=split_reports,
        selection_metric=selection_metric,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        population_size=population_size,
        generations=generations,
        base_seed=base_seed,
        momentum_lookback_days=momentum_lookback_days,
        momentum_top_k=momentum_top_k,
        momentum_rebalance_frequency=momentum_rebalance_frequency,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_output_path.write_text(
        build_walk_forward_optimizer_summary(report),
        encoding="utf-8",
    )

    print(f"Saved walk-forward optimizer report to: {output_path}")
    print(f"Saved walk-forward optimizer summary to: {summary_output_path}")
    print(f"Evaluated splits: {report['evaluated_split_count']}")
    print(f"Aggregate metrics: {report['aggregate_test_metrics']}")
    print(f"Winner counts: {report['split_metric_winner_counts']}")

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full walk-forward optimizer selection.")
    parser.add_argument(
        "--prices",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
    )
    parser.add_argument(
        "--universe-config",
        type=Path,
        default=Path("configs/universe_etf.yaml"),
    )
    parser.add_argument(
        "--split-report",
        type=Path,
        default=Path("reports/walk_forward_splits.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/walk_forward_optimizer_selection.json"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("reports/walk_forward_optimizer_selection_summary.md"),
    )
    parser.add_argument("--population-size", type=int, default=12)
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--min-train-return-observations", type=int, default=1000)
    parser.add_argument("--min-test-return-observations", type=int, default=100)
    parser.add_argument("--selection-metric", type=str, default="sharpe")
    parser.add_argument("--benchmark-ticker", type=str, default="SPY")
    parser.add_argument("--momentum-lookback-days", type=int, default=252)
    parser.add_argument("--momentum-top-k", type=int, default=5)
    parser.add_argument("--momentum-rebalance-frequency", type=str, default="ME")
    parser.add_argument("--max-splits", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_walk_forward_optimizer_selection(
        prices_path=args.prices,
        universe_config_path=args.universe_config,
        split_report_path=args.split_report,
        output_path=args.output,
        summary_output_path=args.summary_output,
        population_size=args.population_size,
        generations=args.generations,
        base_seed=args.base_seed,
        transaction_cost_bps=args.transaction_cost_bps,
        risk_free_rate=args.risk_free_rate,
        min_train_return_observations=args.min_train_return_observations,
        min_test_return_observations=args.min_test_return_observations,
        selection_metric=args.selection_metric,
        benchmark_ticker=args.benchmark_ticker,
        momentum_lookback_days=args.momentum_lookback_days,
        momentum_top_k=args.momentum_top_k,
        momentum_rebalance_frequency=args.momentum_rebalance_frequency,
        max_splits=args.max_splits,
    )


if __name__ == "__main__":
    main()
