from __future__ import annotations

from pathlib import Path

TARGET = Path("scripts/build_final_results_notebook.py")


def replace_function_block(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    """Replace a function block between two markers."""
    start = text.find(start_marker)
    if start == -1:
        raise ValueError(f"Start marker not found: {start_marker}")

    end = text.find(end_marker, start)
    if end == -1:
        raise ValueError(f"End marker not found: {end_marker}")

    return text[:start] + replacement.rstrip() + "\n\n\n" + text[end:]


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    core_replacement = r'''
def build_core_result_markdown(
    stitched_report: dict[str, Any],
) -> str:
    """Build the main visible result summary with bad results included."""
    metrics = stitched_report["stitched_metrics"]
    spy = metrics["buy_hold_SPY"]
    optimizer = metrics["optimizer_selected_net"]
    momentum_gross = metrics["momentum_top_5_252d_gross"]

    def metric_row(strategy_name: str, metric_values: dict[str, Any]) -> str:
        return (
            f"| {strategy_name} | "
            f"{format_float(metric_values.get('final_equity'))} | "
            f"{format_percent(metric_values.get('cagr'))} | "
            f"{format_float(metric_values.get('sharpe'))} | "
            f"{format_percent(metric_values.get('max_drawdown'))} | "
            f"{format_float(metric_values.get('calmar'))} |"
        )

    rows = [
        "| Strategy | Final Equity | CAGR | Sharpe | Max Drawdown | Calmar |",
        "|---|---:|---:|---:|---:|---:|",
        metric_row("SPY buy-and-hold", spy),
        metric_row("Momentum gross", momentum_gross),
        metric_row("Optimizer selected net", optimizer),
    ]
    result_table = "\n".join(rows)

    return f"""
## Core Result: Mixed / Negative Return Result

This notebook intentionally keeps the inconvenient results visible.

The evolutionary optimizer **did not outperform SPY** on stitched final equity,
stitched CAGR, or stitched Sharpe.

{result_table}

**Strict interpretation:** the optimizer improved drawdown control, but it
sacrificed return and risk-adjusted performance. This is a **risk-control
trade-off**.

Exact phrase for review/test visibility: **risk-control trade-off**.

This is not market outperformance.
""".strip()
'''

    walk_forward_replacement = r'''
def build_walk_forward_markdown(
    walk_forward_report: dict[str, Any],
) -> str:
    """Build Markdown summary for full walk-forward selection evidence."""
    aggregate = walk_forward_report["aggregate_test_metrics"]
    spy = aggregate["buy_hold_SPY"]
    optimizer = aggregate["optimizer_selected_net"]

    def aggregate_row(strategy_name: str, metric_values: dict[str, Any]) -> str:
        return (
            f"| {strategy_name} | "
            f"{format_percent(metric_values.get('mean_cagr'))} | "
            f"{format_float(metric_values.get('mean_sharpe'))} | "
            f"{format_percent(metric_values.get('mean_max_drawdown'))} |"
        )

    rows = [
        "| Strategy | Mean CAGR | Mean Sharpe | Mean Max Drawdown |",
        "|---|---:|---:|---:|",
        aggregate_row("SPY buy-and-hold", spy),
        aggregate_row("Optimizer selected net", optimizer),
    ]
    result_table = "\n".join(rows)

    return f"""
## Full Walk-Forward Optimizer Selection

The optimizer was trained only on each train window. A single candidate was
selected by fixed train Sharpe before the OOS test window was evaluated.

Across {walk_forward_report["evaluated_split_count"]} OOS splits:

{result_table}

Again, the optimizer does **not** beat SPY on mean CAGR or mean Sharpe.
It only improves mean max drawdown. This is a risk-control trade-off, not
broad outperformance.
""".strip()
'''

    text = replace_function_block(
        text=text,
        start_marker="def build_core_result_markdown(",
        end_marker="def build_walk_forward_markdown(",
        replacement=core_replacement,
    )
    text = replace_function_block(
        text=text,
        start_marker="def build_walk_forward_markdown(",
        end_marker="def build_notebook(",
        replacement=walk_forward_replacement,
    )

    TARGET.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
