from __future__ import annotations

from pathlib import Path

NSGA2_ARTIFACTS = [
    "reports/nsga2_train_smoke.json",
    "reports/nsga2_train_smoke_summary.md",
    "reports/nsga2_train_smoke_run.log",
]


def register_nsga2_artifacts(project_root: Path) -> None:
    """Register NSGA-II smoke artifacts as RequiredArtifact objects."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    if all(f'path="{artifact}"' in text for artifact in NSGA2_ARTIFACTS):
        return

    anchor = (
        "    RequiredArtifact(\n"
        '        path="reports/factor_rotation_grid_smoke_run.log",\n'
        '        category="factor_rotation_smoke",\n'
        '        description="Run log for factor-rotation grid smoke evaluation.",\n'
        "    ),"
    )

    insertion = (
        anchor
        + "\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/nsga2_train_smoke.json",\n'
        + '        category="nsga2_train_smoke",\n'
        + '        description="Train-only NSGA-II optimizer smoke JSON report.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/nsga2_train_smoke_summary.md",\n'
        + '        category="nsga2_train_smoke",\n'
        + '        description="Markdown summary for train-only NSGA-II smoke.",\n'
        + "    ),\n"
        + "    RequiredArtifact(\n"
        + '        path="reports/nsga2_train_smoke_run.log",\n'
        + '        category="nsga2_train_smoke",\n'
        + '        description="Run log for train-only NSGA-II smoke.",\n'
        + "    ),"
    )

    if anchor not in text:
        raise ValueError("Could not find factor-rotation smoke artifact anchor.")

    path.write_text(text.replace(anchor, insertion), encoding="utf-8")


def update_artifact_checker_tests(project_root: Path) -> None:
    """Update hard-coded artifact-count expectations from 18 to 21."""
    path = project_root / "tests" / "test_check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "artifact_count'] == 18": "artifact_count'] == 21",
        'artifact_count"] == 18': 'artifact_count"] == 21',
        "Required artifact count: 18": "Required artifact count: 21",
        "artifact_count: 18": "artifact_count: 21",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def update_report_index(project_root: Path) -> None:
    """Document NSGA-II train-smoke artifacts in report index."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    if "reports/nsga2_train_smoke.json" in text:
        return

    section = (
        "\n## NSGA-II Train-Only Smoke Optimization\n\n"
        "- `reports/nsga2_train_smoke.json` — train-only NSGA-II "
        "optimizer smoke JSON report.\n"
        "- `reports/nsga2_train_smoke_summary.md` — Markdown summary "
        "with train leaders, top evaluations, and Pareto objectives.\n"
        "- `reports/nsga2_train_smoke_run.log` — command output for "
        "the NSGA-II smoke run.\n\n"
        "Interpretation rule: this validates optimizer plumbing on one "
        "train window. It is not walk-forward selection and not "
        "out-of-sample performance evidence.\n"
    )

    path.write_text(text.rstrip() + "\n" + section + "\n", encoding="utf-8")


def update_readme(project_root: Path) -> None:
    """Link NSGA-II smoke summary from README report section."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")

    if "reports/nsga2_train_smoke_summary.md" in text:
        return

    anchor = "reports/factor_rotation_grid_smoke_summary.md"
    anchor_position = text.find(anchor)

    if anchor_position == -1:
        return

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        return

    insertion = (
        "- `reports/nsga2_train_smoke_summary.md` — train-only NSGA-II "
        "optimizer smoke report. Validates optimizer plumbing; not OOS "
        "evidence.\n"
    )

    text = text[: line_end + 1] + insertion + text[line_end + 1 :]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    register_nsga2_artifacts(project_root)
    update_artifact_checker_tests(project_root)
    update_report_index(project_root)
    update_readme(project_root)


if __name__ == "__main__":
    main()
