from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
from src.backtesting.engine import run_rebalanced_backtest
from src.optimization.nsga2_optimizer import NSGA2SearchSpace, run_nsga2_train_optimizer
from src.optimization.objective import build_metric_dict, summarize_turnover
from src.strategies.baselines import (
    calculate_asset_returns,
    calculate_buy_and_hold_returns,
    calculate_equal_weight_returns,
)
from src.strategies.factor_rotation import (
    FactorRotationParameters,
    calculate_factor_rotation_weights,
)

from scripts.evaluate_factor_rotation_grid_smoke import (
    format_float,
    format_percent,
    load_universe_price_matrix,
)


def get_split_value(split: dict[str, Any], candidate_keys: list[str]) -> str:
    """Read split date using flexible key names."""
    for key in candidate_keys:
        if key in split:
            return str(split[key])

    raise KeyError(f"None of these split keys were found: {candidate_keys}")


def load_train_test_window_from_split_report(
    split_report_path: Path,
    split_index: int,
) -> dict[str, str]:
    """Load train/test boundaries from walk-forward split report."""
    report = json.loads(split_report_path.read_text(encoding="utf-8"))
    splits = report["splits"]

    if split_index < 0 or split_index >= len(splits):
        raise IndexError(f"split_index out of range: {split_index}")

    split = splits[split_index]

    return {
        "train_start": get_split_value(split, ["train_start", "train_start_date"]),
        "train_end": get_split_value(split, ["train_end", "train_end_date"]),
        "test_start": get_split_value(split, ["test_start", "test_start_date"]),
        "test_end": get_split_value(split, ["test_end", "test_end_date"]),
    }


def select_evaluation_by_metric(
    evaluations: list[dict[str, Any]],
    metric_name: str,
    maximize: bool = True,
) -> dict[str, Any]:
    """Select one valid train evaluation by a pre-declared metric rule."""
    scored: list[tuple[float, str, dict[str, Any]]] = []

    for evaluation in evaluations:
        metric_value = evaluation.get("metrics", {}).get(metric_name)
        candidate_id = str(evaluation.get("candidate_id", ""))

        if evaluation.get("valid") and metric_value is not None:
            scored.append((float(metric_value), candidate_id, evaluation))

    if not scored:
        raise ValueError(f"No valid evaluations with metric: {metric_name}")

    scored = sorted(
        scored,
        key=lambda item: (item[0], item[1]),
        reverse=maximize,
    )

    return scored[0][2]


def align_return_series_to_common_index(
    return_series_by_strategy: dict[str, pd.Series],
) -> tuple[dict[str, pd.Series], pd.DatetimeIndex]:
    """Align strategy return series to exact common date intersection."""
    cleaned: dict[str, pd.Series] = {}

    for strategy_name, returns in return_series_by_strategy.items():
        if returns.empty:
            raise ValueError(f"Return series is empty: {strategy_name}")
        if not isinstance(returns.index, pd.DatetimeIndex):
            raise TypeError(f"Return series must use DatetimeIndex: {strategy_name}")
        if returns.index.has_duplicates:
            raise ValueError(f"Return series has duplicate dates: {strategy_name}")

        numeric_returns = pd.to_numeric(returns, errors="raise").dropna().sort_index()
        if numeric_returns.empty:
            raise ValueError(f"Return series has no numeric observations: {strategy_name}")

        cleaned[strategy_name] = numeric_returns.astype("float64")

    common_index: pd.DatetimeIndex | None = None

    for returns in cleaned.values():
        common_index = (
            returns.index if common_index is None else common_index.intersection(returns.index)
        )

    if common_index is None or common_index.empty:
        raise ValueError("No common return dates across strategies.")

    aligned = {
        strategy_name: returns.reindex(common_index) for strategy_name, returns in cleaned.items()
    }

    for strategy_name, returns in aligned.items():
        if returns.isna().any():
            raise ValueError(f"Aligned return series contains NaN: {strategy_name}")

    return aligned, common_index


def build_metrics_for_return_series(
    aligned_returns: dict[str, pd.Series],
    risk_free_rate: float,
) -> dict[str, dict[str, float | int | None]]:
    """Calculate metrics for aligned return series."""
    return {
        strategy_name: build_metric_dict(
            net_returns=returns,
            risk_free_rate=risk_free_rate,
        )
        for strategy_name, returns in aligned_returns.items()
    }


def find_test_metric_leaders(
    metrics_by_strategy: dict[str, dict[str, float | int | None]],
) -> dict[str, dict[str, Any] | None]:
    """Find simple test-window metric leaders."""
    leader_specs = {
        "highest_test_cagr": ("cagr", True),
        "highest_test_sharpe": ("sharpe", True),
        "least_severe_test_max_drawdown": ("max_drawdown", True),
        "highest_test_calmar": ("calmar", True),
    }

    leaders: dict[str, dict[str, Any] | None] = {}

    for leader_name, (metric_name, maximize) in leader_specs.items():
        scored: list[tuple[float, str]] = []

        for strategy_name, metrics in metrics_by_strategy.items():
            value = metrics.get(metric_name)
            if value is not None:
                scored.append((float(value), strategy_name))

        if not scored:
            leaders[leader_name] = None
            continue

        scored = sorted(scored, key=lambda item: item[0], reverse=maximize)
        best_value, best_strategy = scored[0]
        leaders[leader_name] = {
            "strategy_name": best_strategy,
            "metric": metric_name,
            "value": best_value,
        }

    return leaders


def evaluate_selected_factor_rotation_on_test_window(
    price_matrix: pd.DataFrame,
    parameters: FactorRotationParameters,
    test_start: str,
    test_end: str,
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_test_return_observations: int,
) -> dict[str, Any]:
    """Evaluate selected factor-rotation parameters on OOS test window.

    Rolling factor history may use prices before test_start, but target
    rebalance decisions are restricted to the test window.
    """
    test_start_ts = pd.Timestamp(test_start)
    test_end_ts = pd.Timestamp(test_end)

    if test_start_ts > test_end_ts:
        raise ValueError("test_start must be <= test_end.")

    context_prices = price_matrix.loc[:test_end_ts]
    target_weights_all = calculate_factor_rotation_weights(
        price_matrix=context_prices,
        parameters=parameters,
    )

    target_weights = target_weights_all.loc[
        (target_weights_all.index >= test_start_ts) & (target_weights_all.index <= test_end_ts)
    ].dropna(how="all")

    if target_weights.empty:
        return {
            "valid": False,
            "invalid_reason": "No valid target weights in test window.",
            "strategy_name": parameters.strategy_name(),
            "parameters": asdict(parameters),
            "metrics": {},
            "turnover_summary": {},
            "return_start": None,
            "return_end": None,
            "return_observation_count": 0,
        }

    asset_returns_all = calculate_asset_returns(context_prices)
    test_asset_returns = asset_returns_all.loc[
        (asset_returns_all.index >= test_start_ts) & (asset_returns_all.index <= test_end_ts)
    ]

    if test_asset_returns.empty:
        return {
            "valid": False,
            "invalid_reason": "No asset returns in test window.",
            "strategy_name": parameters.strategy_name(),
            "parameters": asdict(parameters),
            "metrics": {},
            "turnover_summary": {},
            "return_start": None,
            "return_end": None,
            "return_observation_count": 0,
        }

    result = run_rebalanced_backtest(
        asset_returns=test_asset_returns,
        target_weights=target_weights,
        strategy_name=f"{parameters.strategy_name()}_selected_oos",
        transaction_cost_bps=transaction_cost_bps,
        execution_lag_days=1,
        include_initial_allocation_cost=True,
        max_leverage=1.0,
    )

    net_returns = result.net_returns.loc[
        (result.net_returns.index >= test_start_ts) & (result.net_returns.index <= test_end_ts)
    ]

    if len(net_returns) < min_test_return_observations:
        return {
            "valid": False,
            "invalid_reason": (
                "Insufficient selected-strategy test observations: "
                f"{len(net_returns)} < {min_test_return_observations}."
            ),
            "strategy_name": result.strategy_name,
            "parameters": asdict(parameters),
            "metrics": {},
            "turnover_summary": summarize_turnover(result.turnover),
            "return_start": str(net_returns.index.min().date()) if not net_returns.empty else None,
            "return_end": str(net_returns.index.max().date()) if not net_returns.empty else None,
            "return_observation_count": int(len(net_returns)),
        }

    turnover = result.turnover.reindex(net_returns.index).fillna(0.0)

    return {
        "valid": True,
        "invalid_reason": None,
        "strategy_name": result.strategy_name,
        "parameters": asdict(parameters),
        "metrics": build_metric_dict(
            net_returns=net_returns,
            risk_free_rate=risk_free_rate,
        ),
        "turnover_summary": summarize_turnover(turnover),
        "return_start": str(net_returns.index.min().date()),
        "return_end": str(net_returns.index.max().date()),
        "return_observation_count": int(len(net_returns)),
        "net_returns": net_returns,
    }


def build_simple_test_baseline_returns(
    price_matrix: pd.DataFrame,
    test_start: str,
    test_end: str,
    benchmark_ticker: str = "SPY",
) -> dict[str, pd.Series]:
    """Build simple OOS baseline returns for the selected test window."""
    test_start_ts = pd.Timestamp(test_start)
    test_end_ts = pd.Timestamp(test_end)

    asset_returns = calculate_asset_returns(price_matrix.loc[:test_end_ts])
    test_asset_returns = asset_returns.loc[
        (asset_returns.index >= test_start_ts) & (asset_returns.index <= test_end_ts)
    ]

    return {
        f"buy_hold_{benchmark_ticker}": calculate_buy_and_hold_returns(
            asset_returns=test_asset_returns,
            ticker=benchmark_ticker,
        ),
        "equal_weight": calculate_equal_weight_returns(
            asset_returns=test_asset_returns,
        ),
    }


def calculate_selected_degradation(
    train_metrics: dict[str, float | int | None],
    test_metrics: dict[str, float | int | None],
) -> dict[str, float | None]:
    """Calculate test-minus-train metric deltas for selected candidate."""
    metric_names = ["cagr", "sharpe", "max_drawdown", "calmar"]

    degradation: dict[str, float | None] = {}
    for metric_name in metric_names:
        train_value = train_metrics.get(metric_name)
        test_value = test_metrics.get(metric_name)

        if train_value is None or test_value is None:
            degradation[f"{metric_name}_test_minus_train"] = None
        else:
            degradation[f"{metric_name}_test_minus_train"] = float(test_value) - float(train_value)

    return degradation


def build_one_split_selection_report(
    split_index: int,
    train_start: str,
    train_end: str,
    test_start: str,
    test_end: str,
    optimizer_result: dict[str, Any],
    selected_train_evaluation: dict[str, Any],
    selected_test_evaluation: dict[str, Any],
    test_common_metrics: dict[str, dict[str, float | int | None]],
    test_common_start: str,
    test_common_end: str,
    test_common_observation_count: int,
    transaction_cost_bps: float,
    risk_free_rate: float,
    selection_metric: str,
) -> dict[str, Any]:
    """Build train->test optimizer selection report."""
    return {
        "evaluation_type": "one_split_optimizer_train_test_selection",
        "protocol": (
            "NSGA-II is fit only on the train window. A single candidate is "
            "selected using a fixed train metric before test evaluation. "
            "The selected candidate is then evaluated on the OOS test window."
        ),
        "split_index": split_index,
        "train_start": train_start,
        "train_end": train_end,
        "test_start": test_start,
        "test_end": test_end,
        "transaction_cost_bps": transaction_cost_bps,
        "risk_free_rate": risk_free_rate,
        "selection_rule": {
            "metric": selection_metric,
            "direction": "maximize",
            "candidate_pool": "all_valid_train_evaluations",
            "test_data_used_for_selection": False,
        },
        "optimizer_summary": {
            "objective_names": optimizer_result["objective_names"],
            "population_size": optimizer_result["population_size"],
            "generations": optimizer_result["generations"],
            "seed": optimizer_result["seed"],
            "evaluation_count": optimizer_result["evaluation_count"],
            "valid_evaluation_count": optimizer_result["valid_evaluation_count"],
            "invalid_evaluation_count": optimizer_result["invalid_evaluation_count"],
            "pareto_candidate_count": optimizer_result["pareto_candidate_count"],
        },
        "selected_train_evaluation": {
            key: value
            for key, value in selected_train_evaluation.items()
            if key != "optimizer_vector"
        },
        "selected_test_evaluation": {
            key: value for key, value in selected_test_evaluation.items() if key != "net_returns"
        },
        "selected_metric_degradation": calculate_selected_degradation(
            train_metrics=selected_train_evaluation["metrics"],
            test_metrics=selected_test_evaluation["metrics"],
        ),
        "test_common_window": {
            "start": test_common_start,
            "end": test_common_end,
            "observation_count": test_common_observation_count,
        },
        "test_common_metrics": test_common_metrics,
        "test_common_metric_leaders": find_test_metric_leaders(test_common_metrics),
        "pareto_front": optimizer_result["pareto_front"],
        "interpretation_rule": (
            "This is a one-split OOS smoke evaluation, not final walk-forward "
            "evidence. Final conclusions require repeating the protocol across "
            "all splits and comparing against the full baseline suite."
        ),
    }


def build_one_split_selection_summary(report: dict[str, Any]) -> str:
    """Build Markdown summary for one-split train->test selection."""
    selected_train = report["selected_train_evaluation"]
    selected_test = report["selected_test_evaluation"]
    degradation = report["selected_metric_degradation"]

    lines = [
        "# One-Split Optimizer Train-to-Test Selection",
        "",
        "## Protocol",
        "",
        "- Evaluation type: `one_split_optimizer_train_test_selection`.",
        "- NSGA-II is fit only on the train window.",
        "- Selection rule is fixed before test evaluation.",
        "- Test data is not used for candidate selection.",
        "- This is one OOS split only, not final walk-forward evidence.",
        f"- Split index: `{report['split_index']}`.",
        f"- Train window: `{report['train_start']}` to `{report['train_end']}`.",
        f"- Test window: `{report['test_start']}` to `{report['test_end']}`.",
        f"- Selection metric: `{report['selection_rule']['metric']}`.",
        f"- Transaction cost for selected strategy: " f"`{report['transaction_cost_bps']}` bps.",
        "",
        "## Selected Candidate",
        "",
        f"- Candidate ID: `{selected_train['candidate_id']}`.",
        f"- Strategy: `{selected_train['strategy_name']}`.",
        f"- Train CAGR: {format_percent(selected_train['metrics'].get('cagr'))}.",
        f"- Train Sharpe: {format_float(selected_train['metrics'].get('sharpe'))}.",
        f"- Train Max Drawdown: "
        f"{format_percent(selected_train['metrics'].get('max_drawdown'))}.",
        "",
        "## Selected Candidate OOS Test Metrics",
        "",
        f"- Test valid: `{selected_test['valid']}`.",
        f"- Test CAGR: {format_percent(selected_test['metrics'].get('cagr'))}.",
        f"- Test Sharpe: {format_float(selected_test['metrics'].get('sharpe'))}.",
        f"- Test Max Drawdown: " f"{format_percent(selected_test['metrics'].get('max_drawdown'))}.",
        f"- Test observations: `{selected_test['return_observation_count']}`.",
        "",
        "## Train-to-Test Degradation",
        "",
        f"- CAGR test-minus-train: " f"{format_percent(degradation.get('cagr_test_minus_train'))}.",
        f"- Sharpe test-minus-train: "
        f"{format_float(degradation.get('sharpe_test_minus_train'))}.",
        f"- MaxDD test-minus-train: "
        f"{format_percent(degradation.get('max_drawdown_test_minus_train'))}.",
        "",
        "## Common Test-Window Comparison",
        "",
        f"- Common window: `{report['test_common_window']['start']}` to "
        f"`{report['test_common_window']['end']}`.",
        f"- Common observations: " f"`{report['test_common_window']['observation_count']}`.",
        "",
        "| Strategy | CAGR | Sharpe | Max Drawdown | Calmar | Final Equity |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for strategy_name, metrics in report["test_common_metrics"].items():
        lines.append(
            "| "
            f"`{strategy_name}` | "
            f"{format_percent(metrics.get('cagr'))} | "
            f"{format_float(metrics.get('sharpe'))} | "
            f"{format_percent(metrics.get('max_drawdown'))} | "
            f"{format_float(metrics.get('calmar'))} | "
            f"{format_float(metrics.get('final_equity'))} |"
        )

    lines.extend(
        [
            "",
            "## Test Metric Leaders",
            "",
        ]
    )

    for leader_name, leader in report["test_common_metric_leaders"].items():
        if leader is None:
            lines.append(f"- {leader_name}: n/a")
        else:
            lines.append(
                f"- {leader_name}: `{leader['strategy_name']}`, " f"value `{leader['value']:.6f}`"
            )

    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "This is one-split OOS evidence only. It can reveal obvious "
            "overfitting or degradation, but it must not be treated as final "
            "strategy performance. Final conclusions require full walk-forward "
            "optimizer selection across all available splits and comparison "
            "against the complete baseline suite.",
            "",
        ]
    )

    return "\n".join(lines)


def run_one_split_optimizer_selection(
    prices_path: Path,
    universe_config_path: Path,
    split_report_path: Path,
    split_index: int,
    output_path: Path,
    summary_output_path: Path,
    population_size: int,
    generations: int,
    seed: int,
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_train_return_observations: int,
    min_test_return_observations: int,
    selection_metric: str,
    benchmark_ticker: str,
) -> dict[str, Any]:
    """Run one-split train->test optimizer selection."""
    split_window = load_train_test_window_from_split_report(
        split_report_path=split_report_path,
        split_index=split_index,
    )
    price_matrix = load_universe_price_matrix(
        prices_path=prices_path,
        universe_config_path=universe_config_path,
    )
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
            "Selected candidate failed OOS test evaluation: "
            f"{selected_test_evaluation['invalid_reason']}"
        )

    baseline_returns = build_simple_test_baseline_returns(
        price_matrix=price_matrix,
        test_start=split_window["test_start"],
        test_end=split_window["test_end"],
        benchmark_ticker=benchmark_ticker,
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

    report = build_one_split_selection_report(
        split_index=split_index,
        train_start=split_window["train_start"],
        train_end=split_window["train_end"],
        test_start=split_window["test_start"],
        test_end=split_window["test_end"],
        optimizer_result=optimizer_result,
        selected_train_evaluation=selected_train_evaluation,
        selected_test_evaluation=selected_test_evaluation,
        test_common_metrics=test_common_metrics,
        test_common_start=str(common_index.min().date()),
        test_common_end=str(common_index.max().date()),
        test_common_observation_count=int(len(common_index)),
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        selection_metric=selection_metric,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_output_path.write_text(
        build_one_split_selection_summary(report),
        encoding="utf-8",
    )

    print(f"Saved one-split optimizer selection report to: {output_path}")
    print(f"Saved one-split optimizer selection summary to: {summary_output_path}")
    print("Train window: " f"{split_window['train_start']} -> {split_window['train_end']}")
    print("Test window: " f"{split_window['test_start']} -> {split_window['test_end']}")
    print(f"Selection metric: {selection_metric}")
    print(f"Selected candidate: {selected_train_evaluation['candidate_id']}")
    print(f"Selected strategy: {selected_train_evaluation['strategy_name']}")
    print(f"Train Sharpe: {selected_train_evaluation['metrics'].get('sharpe')}")
    print(f"Test Sharpe: {selected_test_evaluation['metrics'].get('sharpe')}")
    print(f"Test common leaders: {report['test_common_metric_leaders']}")

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one-split train->test optimizer selection.")
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
    parser.add_argument("--split-index", type=int, default=0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/one_split_optimizer_selection.json"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("reports/one_split_optimizer_selection_summary.md"),
    )
    parser.add_argument("--population-size", type=int, default=12)
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--min-train-return-observations", type=int, default=1000)
    parser.add_argument("--min-test-return-observations", type=int, default=100)
    parser.add_argument("--selection-metric", type=str, default="sharpe")
    parser.add_argument("--benchmark-ticker", type=str, default="SPY")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_one_split_optimizer_selection(
        prices_path=args.prices,
        universe_config_path=args.universe_config,
        split_report_path=args.split_report,
        split_index=args.split_index,
        output_path=args.output,
        summary_output_path=args.summary_output,
        population_size=args.population_size,
        generations=args.generations,
        seed=args.seed,
        transaction_cost_bps=args.transaction_cost_bps,
        risk_free_rate=args.risk_free_rate,
        min_train_return_observations=args.min_train_return_observations,
        min_test_return_observations=args.min_test_return_observations,
        selection_metric=args.selection_metric,
        benchmark_ticker=args.benchmark_ticker,
    )


if __name__ == "__main__":
    main()
