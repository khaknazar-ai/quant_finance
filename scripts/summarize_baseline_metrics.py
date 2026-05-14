from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def format_percent(value: float | int | None, decimals: int = 2) -> str:
    """Format a decimal return/risk metric as a percentage."""
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.{decimals}f}%"


def format_float(value: float | int | None, decimals: int = 3) -> str:
    """Format a numeric metric."""
    if value is None:
        return "n/a"
    return f"{float(value):.{decimals}f}"


def find_best_strategy(
    metrics_by_strategy: dict[str, dict[str, Any]],
    metric_name: str,
    higher_is_better: bool = True,
) -> str:
    """Find the best strategy for a single metric."""
    candidates = {
        strategy_name: metrics.get(metric_name)
        for strategy_name, metrics in metrics_by_strategy.items()
        if metrics.get(metric_name) is not None
    }

    if not candidates:
        return "n/a"

    if higher_is_better:
        return max(candidates, key=lambda strategy_name: float(candidates[strategy_name]))

    return min(candidates, key=lambda strategy_name: float(candidates[strategy_name]))


def build_baseline_summary(report: dict[str, Any]) -> str:
    """Build a Markdown summary from baseline_metrics.json content."""
    metrics_by_strategy = report["metrics"]

    best_cagr = find_best_strategy(metrics_by_strategy, "cagr", higher_is_better=True)
    best_sharpe = find_best_strategy(metrics_by_strategy, "sharpe", higher_is_better=True)
    lowest_drawdown = find_best_strategy(
        metrics_by_strategy,
        "max_drawdown",
        higher_is_better=True,
    )
    best_calmar = find_best_strategy(metrics_by_strategy, "calmar", higher_is_better=True)

    lines: list[str] = [
        "# Baseline Metrics Summary",
        "",
        "This report is generated from `reports/baseline_metrics.json`.",
        "Do not manually edit metric values in this file.",
        "",
        "## Evaluation protocol",
        "",
        f"- Benchmark: `{report['benchmark_ticker']}`",
        f"- Strategy count: {report['strategy_count']}",
        f"- Return alignment: `{report['return_alignment']}`",
        f"- Common date range: {report['common_start_date']} -> {report['common_end_date']}",
        f"- Common observations: {report['common_observation_count']}",
        f"- Price column: `{report['price_column']}`",
        f"- Risk-free rate: {format_percent(report['risk_free_rate'])}",
        f"- Momentum lookback: {report['momentum_lookback_days']} trading days",
        f"- Momentum top-K: {report['momentum_top_k']}",
        f"- Momentum rebalance frequency: `{report['momentum_rebalance_frequency']}`",
        "",
        "## Metrics",
        "",
        (
            "| Strategy | CAGR | Sharpe | Max Drawdown | Calmar | Ann. Volatility | "
            "Monthly Win Rate | Cumulative Return | Observations |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for strategy_name, metrics in metrics_by_strategy.items():
        lines.append(
            "| "
            f"{strategy_name} | "
            f"{format_percent(metrics['cagr'])} | "
            f"{format_float(metrics['sharpe'])} | "
            f"{format_percent(metrics['max_drawdown'])} | "
            f"{format_float(metrics['calmar'])} | "
            f"{format_percent(metrics['annualized_volatility'])} | "
            f"{format_percent(metrics['monthly_win_rate'])} | "
            f"{format_percent(metrics['cumulative_return'])} | "
            f"{metrics['observation_count']} |"
        )

    lines.extend(
        [
            "",
            "## Single-metric leaders",
            "",
            f"- Highest CAGR: `{best_cagr}`",
            f"- Highest Sharpe: `{best_sharpe}`",
            f"- Least severe max drawdown: `{lowest_drawdown}`",
            f"- Highest Calmar: `{best_calmar}`",
            "",
            "## Interpretation rule",
            "",
            "A single-metric leader is not automatically the best overall strategy.",
            (
                "If one strategy has higher CAGR but another has lower drawdown, "
                "report it as a risk-return trade-off."
            ),
            (
                "Do not describe a lower-return strategy as outperforming unless "
                "the metric being discussed is explicitly named."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def run_summary(input_path: Path, output_path: Path) -> None:
    """Read baseline metrics JSON and write a Markdown summary."""
    report = json.loads(input_path.read_text(encoding="utf-8"))
    summary = build_baseline_summary(report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")

    print(f"Saved baseline summary to: {output_path}")
    print(f"Source report: {input_path}")
    print(f"Strategy count: {report['strategy_count']}")
    print(f"Return alignment: {report['return_alignment']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize baseline metrics as Markdown.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports/baseline_metrics.json"),
        help="Input baseline metrics JSON path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/baseline_metrics_summary.md"),
        help="Output Markdown summary path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_summary(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
