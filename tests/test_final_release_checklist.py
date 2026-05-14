from pathlib import Path


def release_checklist_text() -> str:
    return Path("docs/final_release_checklist.md").read_text(encoding="utf-8")


def test_final_release_checklist_exists_and_has_core_sections() -> None:
    text = release_checklist_text()

    assert "# Final Release Checklist" in text
    assert "## Release Status" in text
    assert "## Final Evidence Summary" in text
    assert "## Required Final Checks" in text
    assert "## Current Final Check Results" in text
    assert "## Final Interpretation" in text


def test_final_release_checklist_keeps_mixed_result_visible() -> None:
    text = release_checklist_text()

    assert "did not outperform SPY" in text
    assert "risk-control trade-off" in text
    assert "broad performance advantage" in text
    assert "Max drawdown" in text


def test_final_release_checklist_renders_current_check_values() -> None:
    text = release_checklist_text()

    assert "| Artifact count | 32 |" in text or "| Artifact count | 34 |" in text
    assert "| Missing artifacts | 0 |" in text
    assert "| Final hygiene passed | True |" in text
    assert "| Reproducibility passed | True |" in text
    assert "| Reproducibility difference count | 0 |" in text


def test_final_release_checklist_has_no_unresolved_template_fragments() -> None:
    text = release_checklist_text()

    forbidden = [
        "{inventory.get",
        "{reproducibility.get",
        "{hygiene.get",
        "{spy.get",
        "{optimizer.get",
        "{stitched[",
        "{walk_forward[",
    ]

    for fragment in forbidden:
        assert fragment not in text


def test_final_release_artifacts_are_registered_and_indexed() -> None:
    checker = Path("scripts/check_report_artifacts.py").read_text(encoding="utf-8")
    index = Path("docs/report_index.md").read_text(encoding="utf-8")

    assert "reports/final_project_hygiene_check.json" in checker
    assert "docs/final_release_checklist.md" in checker
    assert "reports/final_project_hygiene_check.json" in index
    assert "docs/final_release_checklist.md" in index


def test_final_release_checklist_has_no_forbidden_sections() -> None:
    text = release_checklist_text()

    assert "## CV Bullets" not in text
    assert "Resume bullets" not in text
    assert "{walk_forward[" not in text
    assert "{stitched[" not in text
