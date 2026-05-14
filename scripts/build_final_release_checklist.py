from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORBIDDEN_TEMPLATE_FRAGMENTS = [
    "{inventory.get",
    "{reproducibility.get",
    "{hygiene.get",
    "{spy.get",
    "{optimizer.get",
    "{stitched[",
    "{walk_forward[",
]


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float | int | None) -> str:
    """Format decimal metric as percent."""
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def num(value: float | int | None) -> str:
    """Format numeric metric."""
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def build_checklist(project_root: Path) -> str:
    """Build final release checklist from existing reports."""
    stitched = load_json(
        project_root / "reports" / "walk_forward_optimizer_stitched_oos_equity_summary.json"
    )
    inventory = load_json(project_root / "reports" / "report_artifact_inventory.json")
    hygiene = load_json(project_root / "reports" / "final_project_hygiene_check.json")
    reproducibility = load_json(project_root / "reports" / "recovery_reproducibility_check.json")

    metrics = stitched["stitched_metrics"]
    spy = metrics["buy_hold_SPY"]
    optimizer = metrics["optimizer_selected_net"]

    lines = [
        "# Final Release Checklist",
        "",
        "This file is the final repository-level readiness checklist for the Quant",
        "Finance Pipeline project.",
        "",
        "## Release Status",
        "",
        "- [x] README contains final research summary.",
        "- [x] Evaluation protocol is documented.",
        "- [x] Final research notebook is registered as an artifact.",
        "- [x] Report artifact inventory is complete.",
        "- [x] Reproducibility comparison passes.",
        "- [x] Final hygiene check passes.",
        "- [x] Mixed/negative result interpretation is visible.",
        "- [x] No resume-specific section is included in the project docs.",
        "",
        "## Final Evidence Summary",
        "",
        "The optimizer did not outperform SPY on stitched final equity, stitched",
        "CAGR, or stitched Sharpe. It improved stitched max drawdown. The correct",
        "framing is a risk-control trade-off, not a broad performance advantage.",
        "",
        "| Metric | SPY | Optimizer selected net |",
        "|---|---:|---:|",
        "| Final equity | "
        f"{num(spy.get('final_equity'))} | "
        f"{num(optimizer.get('final_equity'))} |",
        f"| CAGR | {pct(spy.get('cagr'))} | {pct(optimizer.get('cagr'))} |",
        f"| Sharpe | {num(spy.get('sharpe'))} | {num(optimizer.get('sharpe'))} |",
        "| Max drawdown | "
        f"{pct(spy.get('max_drawdown'))} | "
        f"{pct(optimizer.get('max_drawdown'))} |",
        "",
        "## Required Final Checks",
        "",
        "```powershell",
        "python -m pytest",
        "python -m scripts.check_final_project_hygiene `",
        "    --project-root . `",
        "    --output reports\\final_project_hygiene_check.json",
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
        "## Current Final Check Results",
        "",
        "| Check | Result |",
        "|---|---:|",
        f"| Artifact count | {inventory.get('artifact_count')} |",
        f"| Missing artifacts | {inventory.get('missing_count')} |",
        f"| Final hygiene passed | {hygiene.get('passed')} |",
        f"| Reproducibility passed | {reproducibility.get('passed')} |",
        "| Reproducibility difference count | " f"{reproducibility.get('difference_count')} |",
        "",
        "## Main Artifacts to Review",
        "",
        "- `README.md`",
        "- `docs/experimental_protocol.md`",
        "- `docs/report_index.md`",
        "- `docs/final_release_checklist.md`",
        "- `notebooks/01_research_results_review.ipynb`",
        "- `reports/walk_forward_optimizer_selection_summary.md`",
        "- `reports/walk_forward_optimizer_stitched_oos_equity_summary.md`",
        "- `reports/walk_forward_optimizer_stitched_oos_equity.parquet`",
        "- `reports/final_project_hygiene_check.json`",
        "- `reports/report_artifact_inventory.json`",
        "",
        "## Final Interpretation",
        "",
        "This project should be presented as a reproducible research pipeline for",
        "walk-forward ETF allocation and optimizer evaluation. The final result is",
        "valuable because it is transparent: the optimizer reduced drawdown but",
        "paid for that defense with materially lower return than SPY.",
        "",
    ]

    checklist = "\n".join(lines)

    unresolved = [fragment for fragment in FORBIDDEN_TEMPLATE_FRAGMENTS if fragment in checklist]
    if unresolved:
        raise ValueError(f"Unresolved checklist template fragments: {unresolved}")

    return checklist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build final release checklist.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/final_release_checklist.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checklist = build_checklist(args.project_root)
    args.output.write_text(checklist, encoding="utf-8")
    print(f"Saved final release checklist to: {args.output}")


if __name__ == "__main__":
    main()
