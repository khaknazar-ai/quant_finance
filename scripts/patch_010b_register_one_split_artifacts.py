from __future__ import annotations

from pathlib import Path

ONE_SPLIT_ARTIFACTS = [
    "reports/one_split_optimizer_selection.json",
    "reports/one_split_optimizer_selection_summary.md",
    "reports/one_split_optimizer_selection_run.log",
]


def register_one_split_artifacts(project_root: Path) -> None:
    """Register one-split optimizer selection artifacts."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    if all(f'path="{artifact}"' in text for artifact in ONE_SPLIT_ARTIFACTS):
        return

    anchor = (
        "    RequiredArtifact(\n"
        '        path="reports/nsga2_train_smoke_run.log",\n'
        '        category="nsga2_train_smoke",\n'
        '        description="Run log for train-only NSGA-II smoke.",\n'
        "    ),"
    )

    insertion = (
        anchor
        + "\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/one_split_optimizer_selection.json",\n'
        + '        category="one_split_optimizer_selection",\n'
        + '        description="One-split train-to-test optimizer selection JSON report.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/one_split_optimizer_selection_summary.md",\n'
        + '        category="one_split_optimizer_selection",\n'
        + '        description="Markdown summary for one-split optimizer selection.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/one_split_optimizer_selection_run.log",\n'
        + '        category="one_split_optimizer_selection",\n'
        + '        description="Run log for one-split optimizer selection.",\n'
        + "    ),"
    )

    if anchor not in text:
        raise ValueError("Could not find NSGA-II smoke artifact anchor.")

    path.write_text(text.replace(anchor, insertion), encoding="utf-8")


def update_artifact_checker_tests(project_root: Path) -> None:
    """Update hard-coded artifact-count expectations from 21 to 24."""
    path = project_root / "tests" / "test_check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "artifact_count'] == 21": "artifact_count'] == 24",
        'artifact_count"] == 21': 'artifact_count"] == 24',
        "Required artifact count: 21": "Required artifact count: 24",
        "artifact_count: 21": "artifact_count: 24",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def update_report_index(project_root: Path) -> None:
    """Document one-split optimizer selection artifacts."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    if "reports/one_split_optimizer_selection.json" in text:
        return

    section = (
        "\n## One-Split Optimizer Train-to-Test Selection\n\n"
        "- `reports/one_split_optimizer_selection.json` — one-split "
        "train-to-test optimizer selection JSON report.\n"
        "- `reports/one_split_optimizer_selection_summary.md` — Markdown "
        "summary with selected candidate, OOS test metrics, degradation, "
        "and baseline comparison.\n"
        "- `reports/one_split_optimizer_selection_run.log` — command output "
        "for the one-split optimizer selection run.\n\n"
        "Interpretation rule: this is one OOS split only. It is useful for "
        "checking train-to-test degradation, but it is not final "
        "walk-forward evidence and not an overall outperformance claim.\n"
    )

    path.write_text(text.rstrip() + "\n" + section + "\n", encoding="utf-8")


def update_readme(project_root: Path) -> None:
    """Link one-split optimizer summary from README report section."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")

    if "reports/one_split_optimizer_selection_summary.md" in text:
        return

    anchor = "reports/nsga2_train_smoke_summary.md"
    anchor_position = text.find(anchor)

    if anchor_position == -1:
        return

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        return

    insertion = (
        "- `reports/one_split_optimizer_selection_summary.md` — first "
        "one-split train-to-test optimizer selection report. OOS smoke only; "
        "not final walk-forward evidence.\n"
    )

    text = text[: line_end + 1] + insertion + text[line_end + 1 :]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    register_one_split_artifacts(project_root)
    update_artifact_checker_tests(project_root)
    update_report_index(project_root)
    update_readme(project_root)


if __name__ == "__main__":
    main()
