from pathlib import Path

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


def test_final_research_notebook_builder_has_no_resume_section() -> None:
    builder_text = Path("scripts/build_final_results_notebook.py").read_text(encoding="utf-8")

    assert "## CV Bullets" not in builder_text
    assert "CV Bullets" not in builder_text
