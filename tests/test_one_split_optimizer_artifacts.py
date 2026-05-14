from pathlib import Path

ONE_SPLIT_ARTIFACTS = [
    "reports/one_split_optimizer_selection.json",
    "reports/one_split_optimizer_selection_summary.md",
    "reports/one_split_optimizer_selection_run.log",
]


def test_one_split_artifacts_are_registered_in_artifact_checker() -> None:
    checker_text = Path("scripts/check_report_artifacts.py").read_text(encoding="utf-8")

    for artifact in ONE_SPLIT_ARTIFACTS:
        assert f'path="{artifact}"' in checker_text

    assert 'category="one_split_optimizer_selection"' in checker_text


def test_one_split_artifacts_are_documented_in_report_index() -> None:
    report_index = Path("docs/report_index.md").read_text(encoding="utf-8")

    for artifact in ONE_SPLIT_ARTIFACTS:
        assert artifact in report_index

    assert "One-Split Optimizer Train-to-Test Selection" in report_index
    assert "not final walk-forward evidence" in report_index


def test_one_split_summary_is_linked_from_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "reports/one_split_optimizer_selection_summary.md" in readme
    assert "not final walk-forward evidence" in readme
