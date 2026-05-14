from pathlib import Path


def readme_text() -> str:
    return Path("README.md").read_text(encoding="utf-8")


def test_readme_contains_final_research_summary() -> None:
    text = readme_text()

    assert "<!-- FINAL_README_POLISH_START -->" in text
    assert "## Final Research Summary" in text
    assert "### Architecture" in text
    assert "### Evaluation Protocol" in text
    assert "### Final Stitched OOS Results" in text
    assert "### Limitations" in text
    assert "### Next Steps" in text


def test_readme_preserves_mixed_negative_result() -> None:
    text = readme_text()

    assert "did not outperform SPY" in text
    assert "risk-control trade-off" in text
    assert "not a broad performance advantage" in text
    assert "Optimizer selected net" in text
    assert "SPY buy-and-hold" in text


def test_readme_links_final_artifacts() -> None:
    text = readme_text()

    assert "notebooks/01_research_results_review.ipynb" in text
    assert "reports/walk_forward_optimizer_stitched_oos_equity_summary.md" in text
    assert "reports/report_artifact_inventory.json" in text


def test_readme_has_no_unresolved_python_template_fragments() -> None:
    text = readme_text()

    assert "{walk_forward[" not in text
    assert "{stitched[" not in text
    assert "{inventory[" not in text
    assert "{aggregate[" not in text
    assert "{metrics[" not in text


def test_readme_does_not_add_resume_section() -> None:
    text = readme_text()

    assert "## CV Bullets" not in text
    assert "### CV Bullets" not in text
    assert "Resume bullets" not in text
