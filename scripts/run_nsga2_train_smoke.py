from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.optimization.nsga2_optimizer import (
    NSGA2SearchSpace,
    run_nsga2_train_optimizer,
)

from scripts.evaluate_factor_rotation_grid_smoke import (
    build_leaders,
    format_float,
    format_percent,
    load_train_window_from_split_report,
    load_universe_price_matrix,
)


def build_nsga2_train_smoke_report(
    train_start: str,
    train_end: str,
    optimizer_result: dict[str, Any],
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_return_observations: int,
) -> dict[str, Any]:
    """Build report for train-only NSGA-II smoke optimization."""
    evaluations = optimizer_result["all_evaluations"]

    return {
        "evaluation_type": "nsga2_factor_rotation_train_smoke",
        "protocol": (
            "NSGA-II smoke optimization evaluated only on one train window. "
            "This is optimizer plumbing validation, not out-of-sample evidence."
        ),
        "train_start": train_start,
        "train_end": train_end,
        "transaction_cost_bps": transaction_cost_bps,
        "risk_free_rate": risk_free_rate,
        "min_return_observations": min_return_observations,
        "objective_names": optimizer_result["objective_names"],
        "population_size": optimizer_result["population_size"],
        "generations": optimizer_result["generations"],
        "seed": optimizer_result["seed"],
        "search_space": optimizer_result["search_space"],
        "evaluation_count": optimizer_result["evaluation_count"],
        "valid_evaluation_count": optimizer_result["valid_evaluation_count"],
        "invalid_evaluation_count": optimizer_result["invalid_evaluation_count"],
        "pareto_candidate_count": optimizer_result["pareto_candidate_count"],
        "leaders": build_leaders(evaluations),
        "pareto_front": optimizer_result["pareto_front"],
        "all_evaluations": evaluations,
    }


def sort_valid_evaluations_by_sharpe(
    evaluations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort valid evaluations by train Sharpe descending."""
    valid_evaluations = [
        evaluation
        for evaluation in evaluations
        if evaluation["valid"] and evaluation["metrics"].get("sharpe") is not None
    ]

    return sorted(
        valid_evaluations,
        key=lambda evaluation: float(evaluation["metrics"]["sharpe"]),
        reverse=True,
    )


def build_nsga2_train_smoke_summary(report: dict[str, Any]) -> str:
    """Build Markdown summary for train-only NSGA-II smoke optimization."""
    lines = [
        "# NSGA-II Train-Only Smoke Optimization",
        "",
        "## Protocol",
        "",
        "- Evaluation type: `nsga2_factor_rotation_train_smoke`.",
        "- This validates optimizer plumbing on one train window.",
        "- This is not walk-forward selection and not OOS evidence.",
        f"- Train window: `{report['train_start']}` to `{report['train_end']}`.",
        f"- Population size: `{report['population_size']}`.",
        f"- Generations: `{report['generations']}`.",
        f"- Seed: `{report['seed']}`.",
        f"- Transaction cost: `{report['transaction_cost_bps']}` bps.",
        f"- Evaluation count: `{report['evaluation_count']}`.",
        f"- Valid evaluations: `{report['valid_evaluation_count']}`.",
        f"- Invalid evaluations: `{report['invalid_evaluation_count']}`.",
        f"- Pareto candidates: `{report['pareto_candidate_count']}`.",
        "",
        "## Train Leaders",
        "",
    ]

    for label, leader in report["leaders"].items():
        if leader is None:
            lines.append(f"- {label}: n/a")
        else:
            lines.append(
                f"- {label}: `{leader['candidate_id']}` "
                f"(`{leader['strategy_name']}`), value `{leader['value']:.6f}`"
            )

    lines.extend(
        [
            "",
            "## Top Valid Evaluations by Train Sharpe",
            "",
            ("| Candidate | CAGR | Sharpe | Max Drawdown | Avg Turnover | " "Strategy |"),
            "|---|---:|---:|---:|---:|---|",
        ]
    )

    for evaluation in sort_valid_evaluations_by_sharpe(report["all_evaluations"])[:10]:
        metrics = evaluation["metrics"]
        turnover = evaluation["turnover_summary"]

        lines.append(
            "| "
            f"`{evaluation['candidate_id']}` | "
            f"{format_percent(metrics.get('cagr'))} | "
            f"{format_float(metrics.get('sharpe'))} | "
            f"{format_percent(metrics.get('max_drawdown'))} | "
            f"{format_float(turnover.get('average_turnover'))} | "
            f"`{evaluation['strategy_name']}` |"
        )

    lines.extend(
        [
            "",
            "## Pareto Front Objectives",
            "",
            (
                "| Pareto ID | Negative Sharpe | Negative CAGR | "
                "MaxDD Abs | Avg Turnover | Strategy |"
            ),
            "|---|---:|---:|---:|---:|---|",
        ]
    )

    for candidate in report["pareto_front"]:
        objectives = candidate["objectives"]
        lines.append(
            "| "
            f"`{candidate['pareto_id']}` | "
            f"{format_float(objectives.get('negative_sharpe'), digits=6)} | "
            f"{format_float(objectives.get('negative_cagr'), digits=6)} | "
            f"{format_float(objectives.get('max_drawdown_abs'), digits=6)} | "
            f"{format_float(objectives.get('average_turnover'), digits=6)} | "
            f"`{candidate['strategy_name']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "This report confirms that NSGA-II can search the factor-rotation "
            "parameter space and produce Pareto candidates on train data. "
            "It must not be used to claim strategy outperformance. Final "
            "evidence requires walk-forward train selection and out-of-sample "
            "test-window evaluation against baselines.",
            "",
        ]
    )

    return "\n".join(lines)


def run_nsga2_train_smoke(
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
    min_return_observations: int,
) -> dict[str, Any]:
    """Run train-only NSGA-II optimizer smoke."""
    train_start, train_end = load_train_window_from_split_report(
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
        train_start=train_start,
        train_end=train_end,
        search_space=search_space,
        population_size=population_size,
        generations=generations,
        seed=seed,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        min_return_observations=min_return_observations,
    )
    report = build_nsga2_train_smoke_report(
        train_start=train_start,
        train_end=train_end,
        optimizer_result=optimizer_result,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        min_return_observations=min_return_observations,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_output_path.write_text(
        build_nsga2_train_smoke_summary(report),
        encoding="utf-8",
    )

    print(f"Saved NSGA-II train smoke report to: {output_path}")
    print(f"Saved NSGA-II train smoke summary to: {summary_output_path}")
    print(f"Train window: {train_start} -> {train_end}")
    print(f"Evaluation count: {report['evaluation_count']}")
    print(f"Valid evaluations: {report['valid_evaluation_count']}")
    print(f"Invalid evaluations: {report['invalid_evaluation_count']}")
    print(f"Pareto candidates: {report['pareto_candidate_count']}")
    print(f"Leaders: {report['leaders']}")

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run train-only NSGA-II smoke.")
    parser.add_argument(
        "--prices",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
        help="Validated OHLCV parquet file.",
    )
    parser.add_argument(
        "--universe-config",
        type=Path,
        default=Path("configs/universe_etf.yaml"),
        help="Universe config path.",
    )
    parser.add_argument(
        "--split-report",
        type=Path,
        default=Path("reports/walk_forward_splits.json"),
        help="Walk-forward split report path.",
    )
    parser.add_argument(
        "--split-index",
        type=int,
        default=0,
        help="Walk-forward split index used for train-only smoke.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/nsga2_train_smoke.json"),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("reports/nsga2_train_smoke_summary.md"),
        help="Output Markdown summary path.",
    )
    parser.add_argument("--population-size", type=int, default=12)
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--min-return-observations", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_nsga2_train_smoke(
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
        min_return_observations=args.min_return_observations,
    )


if __name__ == "__main__":
    main()
