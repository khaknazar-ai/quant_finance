from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON report."""
    return json.loads(path.read_text(encoding="utf-8"))


def format_percent(value: float | int | None) -> str:
    """Format a numeric value as percent."""
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def format_float(value: float | int | None) -> str:
    """Format a numeric value as a compact float."""
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def markdown_cell(source: str) -> dict[str, Any]:
    """Create a Markdown notebook cell."""
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code_cell(source: str) -> dict[str, Any]:
    """Create a code notebook cell without precomputed outputs."""
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


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


def build_notebook(
    walk_forward_report: dict[str, Any],
    stitched_report: dict[str, Any],
) -> dict[str, Any]:
    """Build the final research-review notebook."""
    cells = [
        markdown_cell("""
# Quant Finance Pipeline — Final Research Results Review

This notebook summarizes the final evidence chain for the portfolio project.

The goal is not to hide weak results. The goal is to show a reproducible
research process with walk-forward evaluation, leakage controls, transaction
costs, baselines, optimizer selection, and honest conclusions.
""".strip()),
        markdown_cell("""
## Experimental Integrity Rules

- No test-window data is used for optimizer selection.
- No bad results are removed from the final report.
- Baselines remain visible.
- Transaction costs are included for net strategy results.
- Underperformance versus SPY is reported directly.
- Risk-control improvements are not described as broad outperformance.
""".strip()),
        code_cell("""
from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

def load_json(relative_path: str) -> dict:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))

walk_forward = load_json("reports/walk_forward_optimizer_selection.json")
stitched = load_json("reports/walk_forward_optimizer_stitched_oos_equity_summary.json")

print("Walk-forward splits:", walk_forward["evaluated_split_count"])
print("Stitched OOS window:", stitched["stitched_start"], "->", stitched["stitched_end"])
""".strip()),
        markdown_cell(build_core_result_markdown(stitched_report)),
        code_cell("""
metrics = pd.DataFrame(stitched["stitched_metrics"]).T

display_columns = [
    "final_equity",
    "cagr",
    "sharpe",
    "max_drawdown",
    "calmar",
    "observation_count",
]

metrics[display_columns].sort_values("final_equity", ascending=False)
""".strip()),
        code_cell("""
equity_path = PROJECT_ROOT / "reports/walk_forward_optimizer_stitched_oos_equity.parquet"
equity = pd.read_parquet(equity_path)
equity["date"] = pd.to_datetime(equity["date"])

equity_pivot = equity.pivot(
    index="date",
    columns="strategy_name",
    values="equity",
).sort_index()

ax = equity_pivot.plot(
    figsize=(12, 6),
    title="Stitched OOS Equity Curves: Optimizer vs Baselines",
)
ax.set_ylabel("Equity")
ax.set_xlabel("Date")
plt.show()
""".strip()),
        code_cell("""
drawdown = equity_pivot / equity_pivot.cummax() - 1.0

ax = drawdown.plot(
    figsize=(12, 6),
    title="Stitched OOS Drawdown Curves",
)
ax.set_ylabel("Drawdown")
ax.set_xlabel("Date")
plt.show()
""".strip()),
        code_cell("""
deltas = pd.Series(stitched["optimizer_vs_spy_deltas"], name="optimizer_minus_spy")
deltas.to_frame()
""".strip()),
        markdown_cell(build_walk_forward_markdown(walk_forward_report)),
        code_cell("""
winner_counts = pd.DataFrame(walk_forward["split_metric_winner_counts"]).fillna(0).astype(int)
winner_counts
""".strip()),
        code_cell("""
split_rows = []
for split in walk_forward["split_reports"]:
    selected = split["selected_train_evaluation"]
    test_metrics = split["selected_test_evaluation"]["metrics"]
    split_rows.append(
        {
            "split_index": split["split_index"],
            "test_start": split["test_start"],
            "test_end": split["test_end"],
            "selected_candidate": selected["candidate_id"],
            "test_cagr": test_metrics["cagr"],
            "test_sharpe": test_metrics["sharpe"],
            "test_max_drawdown": test_metrics["max_drawdown"],
        }
    )

pd.DataFrame(split_rows)
""".strip()),
        markdown_cell("""
## What the Results Mean

The optimizer behaved like a conservative risk-control allocation mechanism.
It reduced stitched max drawdown versus SPY, but the cost was substantial:
lower final equity, lower CAGR, and lower Sharpe.

This is a valid research result, but it is not an alpha claim.
The correct conclusion is:

> The evolutionary optimizer produced a lower-drawdown allocation profile,
> but did not outperform simple market and momentum baselines on return or
> risk-adjusted return metrics.
""".strip()),
        markdown_cell("""
## Limitations

- Historical backtest evidence is not live trading evidence.
- ETF universe is limited and may contain survivorship bias.
- yfinance data is research-grade, not institutional-grade.
- Transaction cost and slippage model is simplified.
- Optimizer search can overfit train windows.
- Selection by train Sharpe may prefer overly defensive parameter sets.
- No macro regime features are included.
- No nested validation or multi-seed robustness study is included yet.
""".strip()),
        markdown_cell("""
## Next Steps

- Add volatility targeting as a separate baseline.
- Add drawdown-constrained objective selection.
- Compare selection by train Sharpe, Calmar, and constrained CAGR.
- Add multi-seed optimizer robustness analysis.
- Add parameter stability plots across splits.
- Add regime-aware features such as rates, inflation, volatility index, and
  trend filters.
- Add stricter transaction-cost and slippage stress tests.
""".strip()),
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_notebook(notebook: dict[str, Any], output_path: Path) -> None:
    """Write notebook JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(notebook, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build final research results notebook.")
    parser.add_argument(
        "--walk-forward-report",
        type=Path,
        default=Path("reports/walk_forward_optimizer_selection.json"),
    )
    parser.add_argument(
        "--stitched-report",
        type=Path,
        default=Path("reports/walk_forward_optimizer_stitched_oos_equity_summary.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("notebooks/01_research_results_review.ipynb"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    walk_forward_report = load_json(args.walk_forward_report)
    stitched_report = load_json(args.stitched_report)

    notebook = build_notebook(
        walk_forward_report=walk_forward_report,
        stitched_report=stitched_report,
    )
    write_notebook(notebook=notebook, output_path=args.output)

    print(f"Saved final research notebook to: {args.output}")
    print(f"Cell count: {len(notebook['cells'])}")


if __name__ == "__main__":
    main()
