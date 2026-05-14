from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.summarize_baseline_metrics import format_float, format_percent


def get_aggregate_stat(
    report: dict[str, Any],
    strategy_name: str,
    metric_name: str,
    stat_name: str = "mean",
) -> float | int | None:
    """Read a nested aggregate metric value."""
    return (
        report.get("aggregate_metrics", {})
        .get(strategy_name, {})
        .get("metrics", {})
        .get(metric_name, {})
        .get(stat_name)
    )


def find_best_aggregate_strategy(
    report: dict[str, Any],
    metric_name: str,
    stat_name: str = "mean",
    higher_is_better: bool = True,
) -> str:
    """Find the best strategy by an aggregate metric statistic."""
    candidates: dict[str, float] = {}

    for strategy_name in report["strategies"]:
        value = get_aggregate_stat(
            report=report,
            strategy_name=strategy_name,
            metric_name=metric_name,
            stat_name=stat_name,
        )
        if value is not None:
            candidates[strategy_name] = float(value)

    if not candidates:
        return "n/a"

    if higher_is_better:
        return max(candidates, key=candidates.get)

    return min(candidates, key=candidates.get)


def find_split_cagr_leader(split_report: dict[str, Any]) -> str:
    """Find the highest-CAGR strategy inside one split."""
    candidates = {
        strategy_name: metrics["cagr"]
        for strategy_name, metrics in split_report["metrics"].items()
        if metrics.get("cagr") is not None
    }

    if not candidates:
        return "n/a"

    return max(candidates, key=candidates.get)


def build_walk_forward_summary(report: dict[str, Any]) -> str:
    """Build a Markdown summary from walk_forward_baseline_metrics.json."""
    best_mean_cagr = find_best_aggregate_strategy(report, "cagr")
    best_mean_sharpe = find_best_aggregate_strategy(report, "sharpe")
    lowest_mean_drawdown = find_best_aggregate_strategy(report, "max_drawdown")
    best_mean_calmar = find_best_aggregate_strategy(report, "calmar")

    lines: list[str] = [
        "# Walk-Forward Baseline Summary",
        "",
        "This report is generated from `reports/walk_forward_baseline_metrics.json`.",
        "Do not manually edit metric values in this file.",
        "",
        "## Evaluation protocol",
        "",
        f"- Evaluation type: `{report['evaluation_type']}`",
        f"- Benchmark: `{report['benchmark_ticker']}`",
        f"- Strategy count: {report['strategy_count']}",
        f"- Evaluated split count: {report['evaluated_split_count']}",
        f"- Return alignment: `{report['return_alignment']}`",
        f"- Transaction cost bps: {format_float(report['transaction_cost_bps'], 1)}",
        f"- Cost model: `{report['cost_model']}`",
        f"- Turnover convention: `{report['turnover_convention']}`",
        f"- Momentum lookback: {report['momentum_lookback_days']} trading days",
        f"- Momentum top-K: {report['momentum_top_k']}",
        f"- Momentum rebalance frequency: `{report['momentum_rebalance_frequency']}`",
        "",
        "## Aggregate OOS metrics",
        "",
        (
            "| Strategy | Mean CAGR | Mean Sharpe | Mean MaxDD | Mean Calmar | "
            "Positive CAGR Splits | Worst CAGR Split | Best CAGR Split |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for strategy_name in report["strategies"]:
        aggregate = report["aggregate_metrics"][strategy_name]
        metrics = aggregate["metrics"]

        lines.append(
            "| "
            f"{strategy_name} | "
            f"{format_percent(metrics['cagr']['mean'])} | "
            f"{format_float(metrics['sharpe']['mean'])} | "
            f"{format_percent(metrics['max_drawdown']['mean'])} | "
            f"{format_float(metrics['calmar']['mean'])} | "
            f"{format_percent(aggregate.get('positive_cagr_split_fraction'))} | "
            f"{aggregate.get('worst_cagr_split_id', 'n/a')} | "
            f"{aggregate.get('best_cagr_split_id', 'n/a')} |"
        )

    lines.extend(
        [
            "",
            "## Aggregate single-metric leaders",
            "",
            f"- Highest mean CAGR: `{best_mean_cagr}`",
            f"- Highest mean Sharpe: `{best_mean_sharpe}`",
            f"- Least severe mean max drawdown: `{lowest_mean_drawdown}`",
            f"- Highest mean Calmar: `{best_mean_calmar}`",
            "",
            "## Split-level CAGR leaders",
            "",
            "| Split | Test Window | Highest-CAGR Strategy |",
            "|---:|---|---|",
        ]
    )

    for split_report in report["splits"]:
        leader = find_split_cagr_leader(split_report)
        lines.append(
            "| "
            f"{split_report['split_id']} | "
            f"{split_report['test_start']} -> {split_report['test_end']} | "
            f"{leader} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            "Mean split CAGR is the arithmetic average of annual OOS split CAGRs.",
            "It is not the same as CAGR from one stitched equity curve.",
            (
                "A strategy with lower mean CAGR but lower drawdown should be described "
                "as a risk-return trade-off, not as overall outperformance."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def run_summary(input_path: Path, output_path: Path) -> None:
    """Read walk-forward baseline JSON and write a Markdown summary."""
    report = json.loads(input_path.read_text(encoding="utf-8"))
    summary = build_walk_forward_summary(report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")

    print(f"Saved walk-forward baseline summary to: {output_path}")
    print(f"Source report: {input_path}")
    print(f"Evaluation type: {report['evaluation_type']}")
    print(f"Evaluated splits: {report['evaluated_split_count']}")
    print(f"Strategy count: {report['strategy_count']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize walk-forward baseline metrics as Markdown."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports/walk_forward_baseline_metrics.json"),
        help="Input walk-forward baseline metrics JSON path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/walk_forward_baseline_summary.md"),
        help="Output Markdown summary path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_summary(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
