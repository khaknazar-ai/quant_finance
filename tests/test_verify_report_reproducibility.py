import json

import pytest
from scripts.verify_report_reproducibility import (
    compare_against_reference,
    compare_values,
    load_current_snapshot,
    write_snapshot,
)


def write_required_reports(project_root, value: float = 1.0) -> None:
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "baseline_metrics.json": {
            "strategy_count": 1,
            "metrics": {"strategy": {"cagr": value}},
        },
        "walk_forward_baseline_metrics.json": {
            "evaluated_split_count": 1,
            "aggregate_metrics": {"strategy": {"metrics": {"cagr": {"mean": value}}}},
        },
        "walk_forward_baseline_oos_equity_summary.json": {
            "strategy_count": 1,
            "strategy_summary": {"strategy": {"final_equity": value}},
        },
    }

    for filename, payload in payloads.items():
        (reports_dir / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_compare_values_allows_tiny_numeric_difference() -> None:
    differences = compare_values(
        reference={"metric": 1.0},
        current={"metric": 1.0 + 1e-13},
        path="root",
        tolerance=1e-12,
    )

    assert differences == []


def test_compare_values_detects_numeric_difference() -> None:
    differences = compare_values(
        reference={"metric": 1.0},
        current={"metric": 1.1},
        path="root",
        tolerance=1e-12,
    )

    assert len(differences) == 1
    assert differences[0].path == "root.metric"


def test_write_snapshot_and_compare_pass(tmp_path) -> None:
    write_required_reports(tmp_path, value=1.0)

    reference_path = tmp_path / "reference.json"
    output_path = tmp_path / "comparison.json"

    write_snapshot(project_root=tmp_path, output_path=reference_path)
    compare_against_reference(
        project_root=tmp_path,
        reference_path=reference_path,
        output_path=output_path,
        tolerance=1e-12,
    )

    comparison = json.loads(output_path.read_text(encoding="utf-8"))

    assert comparison["passed"] is True
    assert comparison["difference_count"] == 0


def test_compare_against_reference_fails_when_report_changes(tmp_path) -> None:
    write_required_reports(tmp_path, value=1.0)

    reference_path = tmp_path / "reference.json"
    output_path = tmp_path / "comparison.json"

    write_snapshot(project_root=tmp_path, output_path=reference_path)

    write_required_reports(tmp_path, value=2.0)

    with pytest.raises(ValueError, match="Reproducibility comparison failed"):
        compare_against_reference(
            project_root=tmp_path,
            reference_path=reference_path,
            output_path=output_path,
            tolerance=1e-12,
        )

    comparison = json.loads(output_path.read_text(encoding="utf-8"))

    assert comparison["passed"] is False
    assert comparison["difference_count"] > 0


def test_load_current_snapshot_requires_all_reports(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing JSON report"):
        load_current_snapshot(project_root=tmp_path)
