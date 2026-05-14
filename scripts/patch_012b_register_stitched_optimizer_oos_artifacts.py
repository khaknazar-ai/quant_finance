from __future__ import annotations

from pathlib import Path

STITCHED_OPTIMIZER_ARTIFACTS = [
    "reports/walk_forward_optimizer_stitched_oos_equity.parquet",
    "reports/walk_forward_optimizer_stitched_oos_equity_summary.json",
    "reports/walk_forward_optimizer_stitched_oos_equity_summary.md",
    "reports/build_walk_forward_optimizer_stitched_oos_equity_run.log",
]


def register_stitched_optimizer_artifacts(project_root: Path) -> None:
    """Register stitched optimizer OOS equity artifacts."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    if all(f'path="{artifact}"' in text for artifact in STITCHED_OPTIMIZER_ARTIFACTS):
        return

    anchor = (
        "    RequiredArtifact(\n"
        '        path="reports/walk_forward_optimizer_selection_run.log",\n'
        '        category="walk_forward_optimizer_selection",\n'
        '        description="Run log for full walk-forward optimizer selection.",\n'
        "    ),"
    )

    insertion = (
        anchor
        + "\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/walk_forward_optimizer_stitched_oos_equity.parquet",\n'
        + '        category="walk_forward_optimizer_stitched_oos",\n'
        + '        description="Stitched OOS equity curves for optimizer and baselines.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/walk_forward_optimizer_stitched_oos_equity_summary.json",\n'
        + '        category="walk_forward_optimizer_stitched_oos",\n'
        + '        description="JSON summary for stitched optimizer OOS equity.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/walk_forward_optimizer_stitched_oos_equity_summary.md",\n'
        + '        category="walk_forward_optimizer_stitched_oos",\n'
        + '        description="Markdown summary for stitched optimizer OOS equity.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/build_walk_forward_optimizer_stitched_oos_equity_run.log",\n'
        + '        category="walk_forward_optimizer_stitched_oos",\n'
        + '        description="Run log for stitched optimizer OOS equity generation.",\n'
        + "    ),"
    )

    if anchor not in text:
        raise ValueError("Could not find walk-forward optimizer artifact anchor.")

    path.write_text(text.replace(anchor, insertion), encoding="utf-8")


def update_artifact_checker_tests(project_root: Path) -> None:
    """Update hard-coded artifact-count expectations from 27 to 31."""
    path = project_root / "tests" / "test_check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "artifact_count'] == 27": "artifact_count'] == 31",
        'artifact_count"] == 27': 'artifact_count"] == 31',
        "Required artifact count: 27": "Required artifact count: 31",
        "artifact_count: 27": "artifact_count: 31",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def update_report_index(project_root: Path) -> None:
    """Document stitched optimizer OOS artifacts."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    if "reports/walk_forward_optimizer_stitched_oos_equity.parquet" in text:
        return

    section = (
        "\n## Stitched Optimizer OOS Equity\n\n"
        "- `reports/walk_forward_optimizer_stitched_oos_equity.parquet` — "
        "daily stitched OOS equity curves for optimizer and baselines.\n"
        "- `reports/walk_forward_optimizer_stitched_oos_equity_summary.json` — "
        "machine-readable stitched OOS equity summary.\n"
        "- `reports/walk_forward_optimizer_stitched_oos_equity_summary.md` — "
        "Markdown report with stitched CAGR, Sharpe, MaxDD, Calmar, final "
        "equity, and optimizer-vs-SPY deltas.\n"
        "- `reports/build_walk_forward_optimizer_stitched_oos_equity_run.log` — "
        "command output for stitched optimizer OOS equity generation.\n\n"
        "Interpretation rule: stitched OOS confirms a risk-control trade-off. "
        "SPY leads final equity and CAGR, while optimizer selected net has "
        "less severe max drawdown.\n"
    )

    path.write_text(text.rstrip() + "\n" + section + "\n", encoding="utf-8")


def update_readme(project_root: Path) -> None:
    """Link stitched optimizer OOS summary from README."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")

    if "reports/walk_forward_optimizer_stitched_oos_equity_summary.md" in text:
        return

    anchor = "reports/walk_forward_optimizer_selection_summary.md"
    anchor_position = text.find(anchor)

    if anchor_position == -1:
        return

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        return

    insertion = (
        "- `reports/walk_forward_optimizer_stitched_oos_equity_summary.md` — "
        "stitched 2017-2025 OOS equity report. SPY leads CAGR/final equity; "
        "optimizer improves max drawdown, so the result is a risk-control "
        "trade-off.\n"
    )

    text = text[: line_end + 1] + insertion + text[line_end + 1 :]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    register_stitched_optimizer_artifacts(project_root)
    update_artifact_checker_tests(project_root)
    update_report_index(project_root)
    update_readme(project_root)


if __name__ == "__main__":
    main()
