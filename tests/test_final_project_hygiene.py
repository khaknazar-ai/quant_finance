from pathlib import Path

from scripts.check_final_project_hygiene import run_checks


def test_final_project_hygiene_checks_pass() -> None:
    checks = run_checks(Path("."))

    failed = [check for check in checks if not check.passed]
    assert not failed


def test_final_project_hygiene_includes_core_checks() -> None:
    checks = run_checks(Path("."))
    names = {check.name for check in checks}

    assert "no_unresolved_template_fragments" in names
    assert "no_cv_or_resume_sections" in names
    assert "no_misleading_outperformance_claims" in names
    assert "readme_required_final_phrases" in names
    assert "artifact_inventory_complete" in names
    assert "final_metric_interpretation_consistent" in names
