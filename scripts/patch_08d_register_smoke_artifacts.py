from __future__ import annotations

from pathlib import Path

NEW_ARTIFACTS = [
    "reports/factor_rotation_grid_smoke.json",
    "reports/factor_rotation_grid_smoke_summary.md",
    "reports/factor_rotation_grid_smoke_run.log",
]


def register_artifacts(project_root: Path) -> None:
    """Add factor-rotation smoke artifacts to check_report_artifacts.py."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    if all(artifact in text for artifact in NEW_ARTIFACTS):
        return

    anchor = "reports/build_walk_forward_oos_equity_run.log"
    anchor_position = text.find(anchor)
    if anchor_position == -1:
        raise ValueError("Could not find artifact insertion anchor.")

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        raise ValueError("Could not find end of anchor line.")

    insertion = "".join(f'    "{artifact}",\n' for artifact in NEW_ARTIFACTS)
    text = text[: line_end + 1] + insertion + text[line_end + 1 :]

    path.write_text(text, encoding="utf-8")


def update_tests(project_root: Path) -> None:
    """Update old hard-coded artifact-count expectations if present."""
    path = project_root / "tests" / "test_check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "artifact_count'] == 15": "artifact_count'] == 18",
        'artifact_count"] == 15': 'artifact_count"] == 18',
        "Required artifact count: 15": "Required artifact count: 18",
        "artifact_count: 15": "artifact_count: 18",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def update_report_index(project_root: Path) -> None:
    """Document the factor-rotation smoke artifacts in docs/report_index.md."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    section = (
        "\n## Factor Rotation Smoke Evaluation\n\n"
        "- `reports/factor_rotation_grid_smoke.json` — deterministic "
        "train-window factor-rotation parameter grid smoke report.\n"
        "- `reports/factor_rotation_grid_smoke_summary.md` — Markdown "
        "summary of candidate metrics and leaders.\n"
        "- `reports/factor_rotation_grid_smoke_run.log` — command output "
        "for the smoke evaluation run.\n\n"
        "Interpretation rule: this is train-only smoke evidence. It verifies "
        "that the objective function works on real ETF data, but it is not "
        "optimizer search and not out-of-sample performance evidence.\n"
    )

    if "reports/factor_rotation_grid_smoke.json" not in text:
        text = text.rstrip() + "\n" + section + "\n"

    path.write_text(text, encoding="utf-8")


def update_readme(project_root: Path) -> None:
    """Add a concise smoke-evaluation note to README if the report block exists."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")

    if "reports/factor_rotation_grid_smoke_summary.md" in text:
        return

    anchor = "reports/walk_forward_baseline_oos_equity_summary.md"
    anchor_position = text.find(anchor)

    if anchor_position == -1:
        return

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        return

    insertion = (
        "- `reports/factor_rotation_grid_smoke_summary.md` — train-only "
        "deterministic smoke check for the optimizer-ready factor-rotation "
        "objective. Not OOS evidence.\n"
    )
    text = text[: line_end + 1] + insertion + text[line_end + 1 :]

    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    register_artifacts(project_root)
    update_tests(project_root)
    update_report_index(project_root)
    update_readme(project_root)


if __name__ == "__main__":
    main()
