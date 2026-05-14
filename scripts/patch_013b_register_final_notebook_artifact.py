from __future__ import annotations

import re
from pathlib import Path

NOTEBOOK_PATH = "notebooks/01_research_results_review.ipynb"


def remove_cv_bullets_from_notebook_builder(project_root: Path) -> None:
    """Remove CV bullets cell from the final notebook generator."""
    path = project_root / "scripts" / "build_final_results_notebook.py"
    text = path.read_text(encoding="utf-8")

    if "## CV Bullets" not in text:
        return

    pattern = re.compile(
        r"\n\s*markdown_cell\(\n"
        r'\s*"""\n'
        r"## CV Bullets\n"
        r".*?"
        r'\s*"""\.strip\(\)\n'
        r"\s*\),",
        flags=re.DOTALL,
    )

    new_text, replacement_count = pattern.subn("", text)

    if replacement_count != 1:
        raise ValueError(
            f"Expected to remove exactly one CV bullets cell, removed " f"{replacement_count}."
        )

    path.write_text(new_text, encoding="utf-8")


def update_notebook_tests(project_root: Path) -> None:
    """Make tests assert that CV bullets are not included in the project notebook."""
    path = project_root / "tests" / "test_final_results_notebook.py"
    text = path.read_text(encoding="utf-8")

    if 'assert "CV Bullets" not in text' in text:
        return

    old = '    assert "Optimizer selected net" in text\n'
    new = (
        '    assert "Optimizer selected net" in text\n'
        '    assert "CV Bullets" not in text\n'
        '    assert "CV bullets" not in text\n'
    )

    if old not in text:
        raise ValueError("Could not find notebook negative-result assertion anchor.")

    path.write_text(text.replace(old, new), encoding="utf-8")


def register_notebook_artifact(project_root: Path) -> None:
    """Register the final research notebook in the artifact checker."""
    path = project_root / "scripts" / "check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    if f'path="{NOTEBOOK_PATH}"' in text:
        return

    anchor = (
        "    RequiredArtifact(\n"
        '        path="reports/build_walk_forward_optimizer_stitched_oos_equity_run.log",\n'
        '        category="walk_forward_optimizer_stitched_oos",\n'
        '        description="Run log for stitched optimizer OOS equity generation.",\n'
        "    ),"
    )

    insertion = (
        anchor
        + "\n"
        + "    RequiredArtifact(\n"
        + f'        path="{NOTEBOOK_PATH}",\n'
        + '        category="final_research_notebook",\n'
        + '        description="Final research notebook with visible mixed OOS results.",\n'
        + "    ),"
    )

    if anchor not in text:
        raise ValueError("Could not find stitched optimizer artifact anchor.")

    path.write_text(text.replace(anchor, insertion), encoding="utf-8")


def update_artifact_checker_tests(project_root: Path) -> None:
    """Update hard-coded artifact-count expectations from 31 to 32."""
    path = project_root / "tests" / "test_check_report_artifacts.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "artifact_count'] == 31": "artifact_count'] == 32",
        'artifact_count"] == 31': 'artifact_count"] == 32',
        "Required artifact count: 31": "Required artifact count: 32",
        "artifact_count: 31": "artifact_count: 32",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def update_report_index(project_root: Path) -> None:
    """Document the final notebook in the report index."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    if NOTEBOOK_PATH in text:
        return

    section = (
        "\n## Final Research Notebook\n\n"
        f"- `{NOTEBOOK_PATH}` — notebook review of the final evidence chain, "
        "including baseline results, full walk-forward optimizer selection, "
        "stitched OOS equity curves, drawdown curves, and explicit negative/mixed "
        "result interpretation.\n\n"
        "Interpretation rule: the notebook must keep the inconvenient results "
        "visible. It states that the optimizer did not outperform SPY on final "
        "equity, stitched CAGR, or stitched Sharpe, while improving max drawdown.\n"
    )

    path.write_text(text.rstrip() + "\n" + section + "\n", encoding="utf-8")


def update_readme(project_root: Path) -> None:
    """Link the final notebook from README without adding CV bullets."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")

    if NOTEBOOK_PATH in text:
        return

    anchor = "reports/walk_forward_optimizer_stitched_oos_equity_summary.md"
    anchor_position = text.find(anchor)

    if anchor_position == -1:
        return

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        return

    insertion = (
        f"- `{NOTEBOOK_PATH}` — final research-results notebook with visible "
        "mixed/negative results and risk-control trade-off interpretation.\n"
    )

    text = text[: line_end + 1] + insertion + text[line_end + 1 :]
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    remove_cv_bullets_from_notebook_builder(project_root)
    update_notebook_tests(project_root)
    register_notebook_artifact(project_root)
    update_artifact_checker_tests(project_root)
    update_report_index(project_root)
    update_readme(project_root)


if __name__ == "__main__":
    main()
