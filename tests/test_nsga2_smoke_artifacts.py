from pathlib import Path

NSGA2_ARTIFACTS = [
    "reports/nsga2_train_smoke.json",
    "reports/nsga2_train_smoke_summary.md",
    "reports/nsga2_train_smoke_run.log",
]


def test_nsga2_smoke_artifacts_are_registered_in_artifact_checker() -> None:
    checker_text = Path("scripts/check_report_artifacts.py").read_text(encoding="utf-8")

    for artifact in NSGA2_ARTIFACTS:
        assert f'path="{artifact}"' in checker_text

    assert 'category="nsga2_train_smoke"' in checker_text


def test_nsga2_smoke_artifacts_are_documented_in_report_index() -> None:
    report_index = Path("docs/report_index.md").read_text(encoding="utf-8")

    for artifact in NSGA2_ARTIFACTS:
        assert artifact in report_index

    assert "NSGA-II Train-Only Smoke Optimization" in report_index
    assert "not out-of-sample performance evidence" in report_index


def test_nsga2_smoke_summary_is_linked_from_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "reports/nsga2_train_smoke_summary.md" in readme
    assert "not OOS evidence" in readme
