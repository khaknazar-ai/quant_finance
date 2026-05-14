from pathlib import Path

SMOKE_ARTIFACTS = [
    "reports/factor_rotation_grid_smoke.json",
    "reports/factor_rotation_grid_smoke_summary.md",
    "reports/factor_rotation_grid_smoke_run.log",
]


def test_smoke_artifacts_are_registered_in_artifact_checker() -> None:
    checker_text = Path("scripts/check_report_artifacts.py").read_text(encoding="utf-8")

    for artifact in SMOKE_ARTIFACTS:
        assert artifact in checker_text


def test_smoke_artifacts_are_documented_in_report_index() -> None:
    report_index = Path("docs/report_index.md").read_text(encoding="utf-8")

    for artifact in SMOKE_ARTIFACTS:
        assert artifact in report_index

    assert "train-only smoke evidence" in report_index
    assert "not out-of-sample performance evidence" in report_index


def test_smoke_summary_is_linked_from_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "reports/factor_rotation_grid_smoke_summary.md" in readme
    assert "Not OOS evidence" in readme
