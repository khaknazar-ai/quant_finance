from pathlib import Path

WALK_FORWARD_OPTIMIZER_ARTIFACTS = [
    "reports/walk_forward_optimizer_selection.json",
    "reports/walk_forward_optimizer_selection_summary.md",
    "reports/walk_forward_optimizer_selection_run.log",
]


def test_walk_forward_optimizer_artifacts_are_registered() -> None:
    checker_text = Path("scripts/check_report_artifacts.py").read_text(encoding="utf-8")

    for artifact in WALK_FORWARD_OPTIMIZER_ARTIFACTS:
        assert f'path="{artifact}"' in checker_text

    assert 'category="walk_forward_optimizer_selection"' in checker_text


def test_walk_forward_optimizer_artifacts_are_documented_in_report_index() -> None:
    report_index = Path("docs/report_index.md").read_text(encoding="utf-8")

    for artifact in WALK_FORWARD_OPTIMIZER_ARTIFACTS:
        assert artifact in report_index

    assert "Walk-Forward Optimizer Selection" in report_index
    assert "risk-control trade-off" in report_index


def test_walk_forward_optimizer_summary_is_linked_from_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "reports/walk_forward_optimizer_selection_summary.md" in readme
    assert "risk-control trade-off" in readme
