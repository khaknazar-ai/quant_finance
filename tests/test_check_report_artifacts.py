import json

import pytest
from scripts.check_report_artifacts import (
    RequiredArtifact,
    check_artifacts,
    missing_artifacts,
    run_check,
    write_inventory,
)


def test_check_artifacts_records_existing_and_missing_files(tmp_path) -> None:
    existing_path = tmp_path / "reports" / "existing.json"
    existing_path.parent.mkdir(parents=True)
    existing_path.write_text("{}", encoding="utf-8")

    artifacts = (
        RequiredArtifact(
            path="reports/existing.json",
            category="test",
            description="Existing test artifact.",
        ),
        RequiredArtifact(
            path="reports/missing.json",
            category="test",
            description="Missing test artifact.",
        ),
    )

    statuses = check_artifacts(project_root=tmp_path, artifacts=artifacts)

    assert statuses[0].exists is True
    assert statuses[0].size_bytes == 2
    assert statuses[1].exists is False
    assert statuses[1].size_bytes is None


def test_missing_artifacts_filters_missing_statuses(tmp_path) -> None:
    artifacts = (
        RequiredArtifact(
            path="missing.txt",
            category="test",
            description="Missing test artifact.",
        ),
    )

    statuses = check_artifacts(project_root=tmp_path, artifacts=artifacts)

    assert [status.path for status in missing_artifacts(statuses)] == ["missing.txt"]


def test_write_inventory_writes_json(tmp_path) -> None:
    artifact_path = tmp_path / "artifact.txt"
    artifact_path.write_text("ok", encoding="utf-8")

    artifacts = (
        RequiredArtifact(
            path="artifact.txt",
            category="test",
            description="Test artifact.",
        ),
    )
    statuses = check_artifacts(project_root=tmp_path, artifacts=artifacts)
    output_path = tmp_path / "inventory.json"

    write_inventory(statuses=statuses, output_path=output_path)

    inventory = json.loads(output_path.read_text(encoding="utf-8"))

    assert inventory["artifact_count"] == 1
    assert inventory["missing_count"] == 0
    assert inventory["artifacts"][0]["path"] == "artifact.txt"


def test_run_check_raises_for_missing_default_artifacts(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing required artifacts"):
        run_check(project_root=tmp_path, output_path=None)
