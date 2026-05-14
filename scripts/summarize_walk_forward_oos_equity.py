from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.summarize_baseline_metrics import format_float, format_percent


def get_strategy_metric(
    summary: dict[str, Any],
    strategy_name: str,
    metric_name: str,
) -> float | int | None:
    """Read a stitched OOS metric for one strategy."""
    return (
        summary.get("strategy_summary", {})
        .get(strategy_name, {})
        .get("metrics", {})
        .get(metric_name)
    )


def build_stitched_oos_equity_summary(summary: dict[str, Any]) -> str:
    """Build Markdown summary from stitched OOS equity summary JSON."""
    leaders = summary["leaders"]

    lines: list[str] = [
        "# Stitched Walk-Forward OOS Equity Summary",
        "",
        "This report is generated from `reports/walk_forward_baseline_oos_equity_summary.json`.",
        "Do not manually edit metric values in this file.",
        "",
        "## Evaluation protocol",
        "",
        f"- Evaluation type: `{summary['evaluation_type']}`",
        f"- Benchmark: `{summary['benchmark_ticker']}`",
        f"- Strategy count: {summary['strategy_count']}",
        f"- Evaluated split count: {summary['evaluated_split_count']}",
        f"- Return alignment: `{summary['return_alignment']}`",
        f"- Equity base: {format_float(summary['equity_base'], 1)}",
        f"- Transaction cost bps: {format_float(summary['transaction_cost_bps'], 1)}",
        f"- Cost model: `{summary['cost_model']}`",
        f"- Turnover convention: `{summary['turnover_convention']}`",
        f"- Momentum lookback: {summary['momentum_lookback_days']} trading days",
        f"- Momentum top-K: {summary['momentum_top_k']}",
        f"- Momentum rebalance frequency: `{summary['momentum_rebalance_frequency']}`",
        "",
        "## Stitched OOS metrics",
        "",
        (
            "| Strategy | Final Equity | CAGR | Sharpe | Max Drawdown | Calmar | "
            "Cumulative Return | Observations |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for strategy_name in summary["strategies"]:
        strategy_summary = summary["strategy_summary"][strategy_name]
        metrics = strategy_summary["metrics"]

        lines.append(
            "| "
            f"{strategy_name} | "
            f"{format_float(strategy_summary['final_equity'])} | "
            f"{format_percent(metrics['cagr'])} | "
            f"{format_float(metrics['sharpe'])} | "
            f"{format_percent(metrics['max_drawdown'])} | "
            f"{format_float(metrics['calmar'])} | "
            f"{format_percent(metrics['cumulative_return'])} | "
            f"{strategy_summary['observation_count']} |"
        )

    lines.extend(
        [
            "",
            "## Stitched OOS leaders",
            "",
            f"- Highest stitched CAGR: `{leaders['highest_stitched_cagr']}`",
            f"- Highest stitched Sharpe: `{leaders['highest_stitched_sharpe']}`",
            (
                "- Least severe stitched max drawdown: "
                f"`{leaders['least_severe_stitched_max_drawdown']}`"
            ),
            f"- Highest final equity: `{leaders['highest_final_equity']}`",
            "",
            "## OOS split windows",
            "",
            "| Split | Common OOS Window | Observations |",
            "|---:|---|---:|",
        ]
    )

    for split_window in summary["split_windows"]:
        lines.append(
            "| "
            f"{split_window['split_id']} | "
            f"{split_window['common_start_date']} -> {split_window['common_end_date']} | "
            f"{split_window['common_observation_count']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            (
                "This stitched equity report compounds all non-overlapping OOS test-window "
                "returns into one continuous OOS equity curve."
            ),
            (
                "It complements the split-level report, where mean split CAGR is the "
                "arithmetic average of annual OOS CAGRs."
            ),
            (
                "A strategy can have lower CAGR but higher Sharpe or lower drawdown. "
                "That must be described as a risk-return trade-off, not overall "
                "outperformance."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def run_summary(input_path: Path, output_path: Path) -> None:
    """Read stitched OOS equity JSON and write Markdown summary."""
    summary = json.loads(input_path.read_text(encoding="utf-8"))
    markdown = build_stitched_oos_equity_summary(summary)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Saved stitched OOS equity Markdown summary to: {output_path}")
    print(f"Source report: {input_path}")
    print(f"Evaluation type: {summary['evaluation_type']}")
    print(f"Evaluated splits: {summary['evaluated_split_count']}")
    print(f"Strategy count: {summary['strategy_count']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize stitched walk-forward OOS equity metrics as Markdown."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports/walk_forward_baseline_oos_equity_summary.json"),
        help="Input stitched OOS equity summary JSON path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/walk_forward_baseline_oos_equity_summary.md"),
        help="Output Markdown summary path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_summary(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
