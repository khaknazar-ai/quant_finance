from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RequiredArtifact:
    """Required report artifact metadata."""

    path: str
    category: str
    description: str


@dataclass(frozen=True)
class ArtifactStatus:
    """Observed artifact status."""

    path: str
    category: str
    description: str
    exists: bool
    size_bytes: int | None


REQUIRED_REPORT_ARTIFACTS: tuple[RequiredArtifact, ...] = (
    RequiredArtifact(
        path="docs/experimental_protocol.md",
        category="protocol",
        description="Experimental integrity protocol and interpretation rules.",
    ),
    RequiredArtifact(
        path="docs/report_index.md",
        category="documentation",
        description="Human-readable index of reports and generated artifacts.",
    ),
    RequiredArtifact(
        path="reports/data_quality_prices.json",
        category="data_quality",
        description="Raw OHLCV data quality report.",
    ),
    RequiredArtifact(
        path="reports/feature_quality_report.json",
        category="features",
        description="Technical feature generation quality report.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_splits.json",
        category="walk_forward",
        description="Complete walk-forward split definition.",
    ),
    RequiredArtifact(
        path="reports/baseline_metrics.json",
        category="baseline_full_period",
        description="Machine-readable full-period baseline metrics.",
    ),
    RequiredArtifact(
        path="reports/baseline_metrics_summary.md",
        category="baseline_full_period",
        description="Generated Markdown summary of full-period baseline metrics.",
    ),
    RequiredArtifact(
        path="reports/evaluate_baselines_run.log",
        category="baseline_full_period",
        description="Run log for full-period baseline evaluation.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_baseline_metrics.json",
        category="baseline_walk_forward",
        description="Machine-readable walk-forward OOS baseline metrics.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_baseline_summary.md",
        category="baseline_walk_forward",
        description="Generated Markdown summary of walk-forward OOS baseline metrics.",
    ),
    RequiredArtifact(
        path="reports/evaluate_walk_forward_baselines_run.log",
        category="baseline_walk_forward",
        description="Run log for walk-forward baseline evaluation.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_baseline_oos_equity.parquet",
        category="stitched_oos_equity",
        description="Stitched OOS equity curves for baseline strategies.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_baseline_oos_equity_summary.json",
        category="stitched_oos_equity",
        description="Machine-readable stitched OOS equity summary.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_baseline_oos_equity_summary.md",
        category="stitched_oos_equity",
        description="Generated Markdown summary of stitched OOS equity metrics.",
    ),
    RequiredArtifact(
        path="reports/build_walk_forward_oos_equity_run.log",
        category="stitched_oos_equity",
        description="Run log for stitched OOS equity generation.",
    ),
    RequiredArtifact(
        path="reports/factor_rotation_grid_smoke.json",
        category="factor_rotation_smoke",
        description="Train-only deterministic factor-rotation grid smoke JSON report.",
    ),
    RequiredArtifact(
        path="reports/factor_rotation_grid_smoke_summary.md",
        category="factor_rotation_smoke",
        description="Markdown summary for factor-rotation grid smoke evaluation.",
    ),
    RequiredArtifact(
        path="reports/factor_rotation_grid_smoke_run.log",
        category="factor_rotation_smoke",
        description="Run log for factor-rotation grid smoke evaluation.",
    ),
    RequiredArtifact(
        path="reports/nsga2_train_smoke.json",
        category="nsga2_train_smoke",
        description="Train-only NSGA-II optimizer smoke JSON report.",
    ),
    RequiredArtifact(
        path="reports/nsga2_train_smoke_summary.md",
        category="nsga2_train_smoke",
        description="Markdown summary for train-only NSGA-II smoke.",
    ),
    RequiredArtifact(
        path="reports/nsga2_train_smoke_run.log",
        category="nsga2_train_smoke",
        description="Run log for train-only NSGA-II smoke.",
    ),
    RequiredArtifact(
        path="reports/one_split_optimizer_selection.json",
        category="one_split_optimizer_selection",
        description="One-split train-to-test optimizer selection JSON report.",
    ),
    RequiredArtifact(
        path="reports/one_split_optimizer_selection_summary.md",
        category="one_split_optimizer_selection",
        description="Markdown summary for one-split optimizer selection.",
    ),
    RequiredArtifact(
        path="reports/one_split_optimizer_selection_run.log",
        category="one_split_optimizer_selection",
        description="Run log for one-split optimizer selection.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_optimizer_selection.json",
        category="walk_forward_optimizer_selection",
        description="Full walk-forward optimizer selection JSON report.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_optimizer_selection_summary.md",
        category="walk_forward_optimizer_selection",
        description="Markdown summary for full walk-forward optimizer selection.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_optimizer_selection_run.log",
        category="walk_forward_optimizer_selection",
        description="Run log for full walk-forward optimizer selection.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_optimizer_stitched_oos_equity.parquet",
        category="walk_forward_optimizer_stitched_oos",
        description="Stitched OOS equity curves for optimizer and baselines.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_optimizer_stitched_oos_equity_summary.json",
        category="walk_forward_optimizer_stitched_oos",
        description="JSON summary for stitched optimizer OOS equity.",
    ),
    RequiredArtifact(
        path="reports/walk_forward_optimizer_stitched_oos_equity_summary.md",
        category="walk_forward_optimizer_stitched_oos",
        description="Markdown summary for stitched optimizer OOS equity.",
    ),
    RequiredArtifact(
        path="reports/build_walk_forward_optimizer_stitched_oos_equity_run.log",
        category="walk_forward_optimizer_stitched_oos",
        description="Run log for stitched optimizer OOS equity generation.",
    ),
    RequiredArtifact(
        path="notebooks/01_research_results_review.ipynb",
        category="final_research_notebook",
        description="Final research notebook with visible mixed OOS results.",
    ),
    RequiredArtifact(
        path="reports/final_project_hygiene_check.json",
        category="final_quality_gate",
        description="Final repository hygiene check report.",
    ),
    RequiredArtifact(
        path="docs/final_release_checklist.md",
        category="final_quality_gate",
        description="Final release checklist for GitHub readiness.",
    ),
)


def check_artifacts(
    project_root: Path,
    artifacts: tuple[RequiredArtifact, ...] = REQUIRED_REPORT_ARTIFACTS,
) -> list[ArtifactStatus]:
    """Check whether required artifacts exist and record their file sizes."""
    statuses: list[ArtifactStatus] = []

    for artifact in artifacts:
        artifact_path = project_root / artifact.path
        exists = artifact_path.is_file()
        size_bytes = artifact_path.stat().st_size if exists else None

        statuses.append(
            ArtifactStatus(
                path=artifact.path,
                category=artifact.category,
                description=artifact.description,
                exists=exists,
                size_bytes=size_bytes,
            )
        )

    return statuses


def missing_artifacts(statuses: list[ArtifactStatus]) -> list[ArtifactStatus]:
    """Return missing artifact statuses."""
    return [status for status in statuses if not status.exists]


def write_inventory(statuses: list[ArtifactStatus], output_path: Path) -> None:
    """Write artifact inventory JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "artifact_count": len(statuses),
        "missing_count": len(missing_artifacts(statuses)),
        "artifacts": [asdict(status) for status in statuses],
    }
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")


def run_check(project_root: Path, output_path: Path | None = None) -> None:
    """Check artifacts, optionally write inventory, and fail if any are missing."""
    statuses = check_artifacts(project_root=project_root)

    if output_path is not None:
        write_inventory(statuses=statuses, output_path=output_path)

    missing = missing_artifacts(statuses)

    print(f"Required artifact count: {len(statuses)}")
    print(f"Missing artifact count: {len(missing)}")

    for status in statuses:
        size = "missing" if status.size_bytes is None else f"{status.size_bytes} bytes"
        print(f"[{'OK' if status.exists else 'MISSING'}] {status.path} ({size})")

    if missing:
        missing_paths = ", ".join(status.path for status in missing)
        raise FileNotFoundError(f"Missing required artifacts: {missing_paths}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check required report artifacts.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Project root directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/report_artifact_inventory.json"),
        help="Output artifact inventory JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_check(project_root=args.project_root, output_path=args.output)


if __name__ == "__main__":
    main()
