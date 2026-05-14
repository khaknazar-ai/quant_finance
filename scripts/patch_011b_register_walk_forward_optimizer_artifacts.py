from __future__ import annotations

from pathlib import Path

WALK_FORWARD_OPTIMIZER_ARTIFACTS = [
    "reports/walk_forward_optimizer_selection.json",
    "reports/walk_forward_optimizer_selection_summary.md",
    "reports/walk_forward_optimizer_selection_run.log",
]


def register_walk_forward_optimizer_artifacts(project_root: Path) -> None:
    """Register full walk-forward optimizer selection artifacts."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    if all(f'path="{artifact}"' in text for artifact in WALK_FORWARD_OPTIMIZER_ARTIFACTS):
        return

    anchor = (
        "    RequiredArtifact(\n"
        '        path="reports/one_split_optimizer_selection_run.log",\n'
        '        category="one_split_optimizer_selection",\n'
        '        description="Run log for one-split optimizer selection.",\n'
        "    ),"
    )

    insertion = (
        anchor
        + "\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/walk_forward_optimizer_selection.json",\n'
        + '        category="walk_forward_optimizer_selection",\n'
        + '        description="Full walk-forward optimizer selection JSON report.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/walk_forward_optimizer_selection_summary.md",\n'
        + '        category="walk_forward_optimizer_selection",\n'
        + '        description="Markdown summary for full walk-forward optimizer selection.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/walk_forward_optimizer_selection_run.log",\n'
        + '        category="walk_forward_optimizer_selection",\n'
        + '        description="Run log for full walk-forward optimizer selection.",\n'
        + "    ),"
    )

    if anchor not in text:
        raise ValueError("Could not find one-split optimizer artifact anchor.")

    path.write_text(text.replace(anchor, insertion), encoding="utf-8")


def update_artifact_checker_tests(project_root: Path) -> None:
    """Update hard-coded artifact-count expectations from 24 to 27."""
    path = project_root / "tests" / "test_check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "artifact_count'] == 24": "artifact_count'] == 27",
        'artifact_count"] == 24': 'artifact_count"] == 27',
        "Required artifact count: 24": "Required artifact count: 27",
        "artifact_count: 24": "artifact_count: 27",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def update_report_index(project_root: Path) -> None:
    """Document full walk-forward optimizer artifacts."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    if "reports/walk_forward_optimizer_selection.json" in text:
        return

    section = (
        "\n## Walk-Forward Optimizer Selection\n\n"
        "- `reports/walk_forward_optimizer_selection.json` — full "
        "walk-forward optimizer-selection JSON report across all OOS splits.\n"
        "- `reports/walk_forward_optimizer_selection_summary.md` — Markdown "
        "summary with aggregate OOS metrics, split winner counts, and "
        "train-to-test degradation.\n"
        "- `reports/walk_forward_optimizer_selection_run.log` — command output "
        "for the full walk-forward optimizer-selection run.\n\n"
        "Interpretation rule: this is the main walk-forward OOS optimizer "
        "evidence. The current result should be framed as a risk-control "
        "trade-off: optimizer selected net improved mean max drawdown versus "
        "SPY, but underperformed SPY on mean CAGR and mean Sharpe.\n"
    )

    path.write_text(text.rstrip() + "\n" + section + "\n", encoding="utf-8")


def update_readme(project_root: Path) -> None:
    """Link full walk-forward optimizer summary from README report section."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")

    if "reports/walk_forward_optimizer_selection_summary.md" in text:
        return

    anchor = "reports/one_split_optimizer_selection_summary.md"
    anchor_position = text.find(anchor)

    if anchor_position == -1:
        return

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        return

    insertion = (
        "- `reports/walk_forward_optimizer_selection_summary.md` — full "
        "walk-forward optimizer-selection report across all OOS splits. "
        "Main optimizer evidence; risk-control trade-off, not broad "
        "outperformance.\n"
    )

    text = text[: line_end + 1] + insertion + text[line_end + 1 :]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    register_walk_forward_optimizer_artifacts(project_root)
    update_artifact_checker_tests(project_root)
    update_report_index(project_root)
    update_readme(project_root)


if __name__ == "__main__":
    main()
