from __future__ import annotations

from pathlib import Path

NOTEBOOK_PATH = "notebooks/01_research_results_review.ipynb"


def remove_cv_cell_from_builder(project_root: Path) -> None:
    """Remove the CV Bullets markdown_cell block from the notebook builder."""
    path = project_root / "scripts" / "build_final_results_notebook.py"
    text = path.read_text(encoding="utf-8")

    marker = "## CV Bullets"
    if marker not in text:
        return

    marker_index = text.find(marker)
    start = text.rfind("        markdown_cell(", 0, marker_index)
    if start == -1:
        raise ValueError("Could not find markdown_cell start before CV marker.")

    end_marker = "\n        ),"
    end = text.find(end_marker, marker_index)
    if end == -1:
        raise ValueError("Could not find markdown_cell end after CV marker.")

    end = end + len(end_marker)

    new_text = text[:start] + text[end:]
    if marker in new_text:
        raise ValueError("CV marker still present after removal.")

    path.write_text(new_text, encoding="utf-8")


def update_final_notebook_tests(project_root: Path) -> None:
    """Ensure final notebook tests reject CV sections."""
    path = project_root / "tests" / "test_final_results_notebook.py"
    text = path.read_text(encoding="utf-8")

    if 'assert "## CV Bullets" not in text' not in text:
        anchor = '    assert "Optimizer selected net" in text\n'
        if anchor not in text:
            raise ValueError("Could not find notebook test assertion anchor.")
        text = text.replace(
            anchor,
            anchor
            + '    assert "## CV Bullets" not in text\n'
            + '    assert "CV Bullets" not in text\n',
        )

    path.write_text(text, encoding="utf-8")


def register_notebook_artifact(project_root: Path) -> None:
    """Register final research notebook in artifact checker."""
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

    if anchor not in text:
        raise ValueError("Could not find stitched optimizer artifact anchor.")

    insertion = (
        anchor
        + "\n"
        + "    RequiredArtifact(\n"
        + f'        path="{NOTEBOOK_PATH}",\n'
        + '        category="final_research_notebook",\n'
        + '        description="Final research notebook with visible mixed OOS results.",\n'
        + "    ),"
    )

    path.write_text(text.replace(anchor, insertion), encoding="utf-8")


def update_artifact_count_tests(project_root: Path) -> None:
    """Update expected artifact count to 32."""
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
    """Document final notebook in report index."""
    path = project_root / "docs" / "report_index.md"
    text = path.read_text(encoding="utf-8")

    if NOTEBOOK_PATH in text:
        return

    section = (
        "\n## Final Research Notebook\n\n"
        f"- `{NOTEBOOK_PATH}` — notebook review of the final evidence chain, "
        "including baseline results, full walk-forward optimizer selection, "
        "stitched OOS equity curves, drawdown curves, and explicit mixed-result "
        "interpretation.\n\n"
        "Interpretation rule: the notebook keeps inconvenient results visible. "
        "It states that the optimizer did not outperform SPY on final equity, "
        "stitched CAGR, or stitched Sharpe, while improving max drawdown.\n"
    )

    path.write_text(text.rstrip() + "\n" + section + "\n", encoding="utf-8")


def update_readme(project_root: Path) -> None:
    """Link final notebook from README."""
    path = project_root / "README.md"
    text = path.read_text(encoding="utf-8")

    if NOTEBOOK_PATH in text:
        return

    anchor = "reports/walk_forward_optimizer_stitched_oos_equity_summary.md"
    anchor_position = text.find(anchor)

    if anchor_position == -1:
        raise ValueError("Could not find README stitched OOS summary anchor.")

    line_end = text.find("\n", anchor_position)
    if line_end == -1:
        raise ValueError("Could not find README anchor line ending.")

    insertion = (
        f"- `{NOTEBOOK_PATH}` — final research-results notebook with visible "
        "mixed/negative results and risk-control trade-off interpretation.\n"
    )

    text = text[: line_end + 1] + insertion + text[line_end + 1 :]
    path.write_text(text, encoding="utf-8")


def overwrite_notebook_artifact_tests(project_root: Path) -> None:
    """Write explicit tests for notebook artifact registration."""
    path = project_root / "tests" / "test_final_research_notebook_artifact.py"
    text = """from pathlib import Path


NOTEBOOK_PATH = "notebooks/01_research_results_review.ipynb"


def test_final_research_notebook_is_registered() -> None:
    checker_text = Path("scripts/check_report_artifacts.py").read_text(encoding="utf-8")

    assert f'path="{NOTEBOOK_PATH}"' in checker_text
    assert 'category="final_research_notebook"' in checker_text


def test_final_research_notebook_is_documented() -> None:
    report_index = Path("docs/report_index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert NOTEBOOK_PATH in report_index
    assert NOTEBOOK_PATH in readme
    assert "Final Research Notebook" in report_index
    assert "did not outperform SPY" in report_index


def test_final_research_notebook_builder_has_no_cv_section() -> None:
    builder_text = Path("scripts/build_final_results_notebook.py").read_text(
        encoding="utf-8"
    )

    assert "## CV Bullets" not in builder_text
    assert "CV Bullets" not in builder_text
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    remove_cv_cell_from_builder(project_root)
    update_final_notebook_tests(project_root)
    register_notebook_artifact(project_root)
    update_artifact_count_tests(project_root)
    update_report_index(project_root)
    update_readme(project_root)
    overwrite_notebook_artifact_tests(project_root)


if __name__ == "__main__":
    main()
