from __future__ import annotations

import json
from pathlib import Path
from typing import Any

START_MARKER = "<!-- FINAL_README_POLISH_START -->"
END_MARKER = "<!-- FINAL_README_POLISH_END -->"


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float | int | None) -> str:
    """Format a decimal metric as percent."""
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def num(value: float | int | None) -> str:
    """Format a numeric metric."""
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def stitched_row(strategy_name: str, metrics: dict[str, Any]) -> str:
    """Render one stitched OOS result table row."""
    return (
        f"| {strategy_name} | "
        f"{num(metrics.get('final_equity'))} | "
        f"{pct(metrics.get('cagr'))} | "
        f"{num(metrics.get('sharpe'))} | "
        f"{pct(metrics.get('max_drawdown'))} | "
        f"{num(metrics.get('calmar'))} |"
    )


def aggregate_row(strategy_name: str, metrics: dict[str, Any]) -> str:
    """Render one walk-forward aggregate table row."""
    return (
        f"| {strategy_name} | "
        f"{pct(metrics.get('mean_cagr'))} | "
        f"{num(metrics.get('mean_sharpe'))} | "
        f"{pct(metrics.get('mean_max_drawdown'))} |"
    )


def build_final_readme_section(project_root: Path) -> str:
    """Build fully rendered final README section."""
    stitched = load_json(
        project_root / "reports" / "walk_forward_optimizer_stitched_oos_equity_summary.json"
    )
    walk_forward = load_json(project_root / "reports" / "walk_forward_optimizer_selection.json")
    inventory = load_json(project_root / "reports" / "report_artifact_inventory.json")

    metrics = stitched["stitched_metrics"]
    spy = metrics["buy_hold_SPY"]
    equal_weight = metrics["equal_weight"]
    momentum_gross = metrics["momentum_top_5_252d_gross"]
    momentum_net = metrics["momentum_top_5_252d_net_10bps"]
    optimizer = metrics["optimizer_selected_net"]

    deltas = stitched["optimizer_vs_spy_deltas"]

    aggregate = walk_forward["aggregate_test_metrics"]
    aggregate_spy = aggregate["buy_hold_SPY"]
    aggregate_optimizer = aggregate["optimizer_selected_net"]

    lines: list[str] = []

    lines.extend(
        [
            START_MARKER,
            "",
            "## Final Research Summary",
            "",
            "This project is a reproducible quantitative finance research pipeline",
            "for walk-forward ETF allocation. It evaluates simple baselines,",
            "a factor-rotation strategy, and an NSGA-II evolutionary optimizer",
            "under a fixed out-of-sample protocol.",
            "",
            "The final result is intentionally reported as a mixed result.",
            "The optimizer did not outperform SPY on stitched final equity,",
            "stitched CAGR, or stitched Sharpe. It did reduce stitched max",
            "drawdown. The correct interpretation is a risk-control trade-off,",
            "not broad market outperformance.",
            "",
            "### Architecture",
            "",
            "```text",
            "configs/",
            "  universe, features, walk-forward protocol, optimizer search space",
            "",
            "src/",
            "  config/        pydantic configuration loading and validation",
            "  ingestion/     yfinance OHLCV download and canonicalization",
            "  validation/    pandera data-quality checks",
            "  features/      momentum, volatility, drawdown, cross-sectional ranks",
            "  backtesting/   execution lag, long-only weights, turnover, costs",
            "  strategies/    SPY, equal-weight, momentum, factor rotation",
            "  optimization/  NSGA-II train-window objective evaluation",
            "  risk/          CAGR, Sharpe, Sortino, MaxDD, Calmar",
            "  reporting/     generated report artifacts",
            "",
            "scripts/",
            "  report generation, optimizer selection, stitched OOS equity,",
            "  reproducibility checks, artifact inventory checks",
            "",
            "notebooks/",
            "  final research review notebook with visible mixed results",
            "```",
            "",
            "### Evaluation Protocol",
            "",
            "- Universe: ETF tactical allocation universe from",
            "  `configs/universe_etf.yaml`.",
            "- Walk-forward design: 6-year train windows and 1-year OOS test",
            "  windows.",
            f"- Evaluated OOS splits: {walk_forward['evaluated_split_count']}.",
            "- Stitched OOS window:",
            f"  {stitched['stitched_start']} to {stitched['stitched_end']}.",
            "- Optimization: NSGA-II is run only on train windows.",
            "- Selection rule: fixed train Sharpe selection before test evaluation.",
            "- Execution: one-day lag between target weights and realized returns.",
            "- Costs: transaction-cost-aware net returns for optimizer and net",
            "  momentum.",
            "- Comparison: strategies are aligned on exact common OOS dates.",
            "- Reproducibility: generated reports are compared against a reference",
            "  snapshot.",
            "",
            "### Final Stitched OOS Results",
            "",
            "| Strategy | Final Equity | CAGR | Sharpe | Max Drawdown | Calmar |",
            "|---|---:|---:|---:|---:|---:|",
            stitched_row("SPY buy-and-hold", spy),
            stitched_row("Equal weight", equal_weight),
            stitched_row("Momentum top-5 gross", momentum_gross),
            stitched_row("Momentum top-5 net 10 bps", momentum_net),
            stitched_row("Optimizer selected net", optimizer),
            "",
            "### Optimizer vs SPY",
            "",
            "| Metric | Optimizer - SPY |",
            "|---|---:|",
            f"| CAGR delta | {pct(deltas.get('cagr_optimizer_minus_spy'))} |",
            f"| Sharpe delta | {num(deltas.get('sharpe_optimizer_minus_spy'))} |",
            "| Max drawdown delta | " f"{pct(deltas.get('max_drawdown_optimizer_minus_spy'))} |",
            f"| Calmar delta | {num(deltas.get('calmar_optimizer_minus_spy'))} |",
            "| Final equity delta | " f"{num(deltas.get('final_equity_optimizer_minus_spy'))} |",
            "",
            "### Full Walk-Forward Selection Summary",
            "",
            "| Strategy | Mean OOS CAGR | Mean OOS Sharpe | Mean OOS Max Drawdown |",
            "|---|---:|---:|---:|",
            aggregate_row("SPY buy-and-hold", aggregate_spy),
            aggregate_row("Optimizer selected net", aggregate_optimizer),
            "",
            "### Interpretation",
            "",
            "The optimizer selected net strategy produced the least severe stitched",
            "max drawdown, but it did not beat SPY on final equity, CAGR, Sharpe,",
            "or Calmar. Momentum gross produced the best stitched Sharpe and",
            "Calmar. SPY produced the best stitched final equity and CAGR.",
            "",
            "This is a useful negative/mixed research result: the optimizer worked",
            "as a defensive allocation mechanism, but the defensive profile came",
            "with a large return sacrifice.",
            "",
            "### Key Artifacts",
            "",
            "| Artifact | Purpose |",
            "|---|---|",
            "| `docs/experimental_protocol.md` | Research-integrity rules |",
            "| `docs/report_index.md` | Index of generated evidence artifacts |",
            "| `reports/walk_forward_optimizer_selection_summary.md` | Full WF OOS |",
            "| `reports/walk_forward_optimizer_stitched_oos_equity_summary.md` |",
            "Final stitched OOS summary |",
            "| `reports/walk_forward_optimizer_stitched_oos_equity.parquet` |",
            "Daily stitched OOS equity curves |",
            "| `notebooks/01_research_results_review.ipynb` |",
            "Final notebook with visible mixed results |",
            "| `reports/report_artifact_inventory.json` | Artifact inventory |",
            "",
            f"Current artifact inventory: {inventory['artifact_count']} required",
            f"artifacts, {inventory['missing_count']} missing.",
            "",
            "### Reproducibility Commands",
            "",
            "```powershell",
            "python -m pytest",
            "python -m scripts.verify_report_reproducibility `",
            "    --mode compare `",
            "    --project-root . `",
            "    --reference reports\\recovery_reproducibility_reference.json `",
            "    --output reports\\recovery_reproducibility_check.json `",
            "    --tolerance 1e-12",
            "python -m scripts.check_documentation_integrity --project-root .",
            "python -m scripts.check_report_artifacts `",
            "    --project-root . `",
            "    --output reports\\report_artifact_inventory.json",
            "```",
            "",
            "### Limitations",
            "",
            "- Historical backtests are not live trading evidence.",
            "- ETF universe design can introduce instrument-selection and",
            "  survivorship bias.",
            "- yfinance data is suitable for research, not institutional execution.",
            "- Transaction costs are simplified; taxes, borrow costs, market impact,",
            "  and detailed slippage are not modeled.",
            "- The optimizer can overfit train windows.",
            "- Selection by train Sharpe may favor overly defensive portfolios.",
            "- Residual cash is treated as zero-return cash in the implemented",
            "  strategy.",
            "- No macro regime model, nested validation, or multi-seed optimizer",
            "  robustness study is included yet.",
            "",
            "### Next Steps",
            "",
            "- Add volatility-targeting and drawdown-constrained baselines.",
            "- Compare candidate selection by Sharpe, Calmar, constrained CAGR,",
            "  and turnover.",
            "- Add multi-seed NSGA-II robustness analysis.",
            "- Add parameter-stability plots across walk-forward splits.",
            "- Add regime-aware features such as rates, inflation, VIX, and trend",
            "  filters.",
            "- Add stricter transaction-cost and slippage stress tests.",
            "- Add Streamlit reporting dashboard for interactive inspection.",
            "",
            END_MARKER,
        ]
    )

    section = "\n".join(lines)

    forbidden_fragments = [
        "{walk_forward[",
        "{stitched[",
        "{inventory[",
        "{aggregate[",
        "{metrics[",
    ]
    for fragment in forbidden_fragments:
        if fragment in section:
            raise ValueError(f"Unresolved README template fragment: {fragment}")

    return section


def update_readme(project_root: Path) -> None:
    """Replace or append the final README section."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")
    section = build_final_readme_section(project_root)

    if START_MARKER in text and END_MARKER in text:
        start = text.index(START_MARKER)
        end = text.index(END_MARKER) + len(END_MARKER)
        text = text[:start].rstrip() + "\n\n" + section + "\n" + text[end:].lstrip()
    else:
        text = text.rstrip() + "\n\n" + section + "\n"

    path.write_text(text, encoding="utf-8")


def main() -> None:
    update_readme(Path("."))


if __name__ == "__main__":
    main()
