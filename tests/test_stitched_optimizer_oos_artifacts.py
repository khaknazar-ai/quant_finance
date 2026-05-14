from pathlib import Path

STITCHED_OPTIMIZER_ARTIFACTS = [
    "reports/walk_forward_optimizer_stitched_oos_equity.parquet",
    "reports/walk_forward_optimizer_stitched_oos_equity_summary.json",
    "reports/walk_forward_optimizer_stitched_oos_equity_summary.md",
    "reports/build_walk_forward_optimizer_stitched_oos_equity_run.log",
]


def test_stitched_optimizer_artifacts_are_registered() -> None:
    checker_text = Path("scripts/check_report_artifacts.py").read_text(encoding="utf-8")

    for artifact in STITCHED_OPTIMIZER_ARTIFACTS:
        assert f'path="{artifact}"' in checker_text

    assert 'category="walk_forward_optimizer_stitched_oos"' in checker_text


def test_stitched_optimizer_artifacts_are_documented_in_report_index() -> None:
    report_index = Path("docs/report_index.md").read_text(encoding="utf-8")

    for artifact in STITCHED_OPTIMIZER_ARTIFACTS:
        assert artifact in report_index

    assert "Stitched Optimizer OOS Equity" in report_index
    assert "risk-control trade-off" in report_index


def test_stitched_optimizer_summary_is_linked_from_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "reports/walk_forward_optimizer_stitched_oos_equity_summary.md" in readme
    assert "risk-control trade-off" in readme
