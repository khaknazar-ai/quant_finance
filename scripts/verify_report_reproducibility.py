from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CRITICAL_REPORTS: dict[str, Path] = {
    "baseline_metrics": Path("reports/baseline_metrics.json"),
    "walk_forward_baseline_metrics": Path("reports/walk_forward_baseline_metrics.json"),
    "stitched_oos_equity_summary": Path("reports/walk_forward_baseline_oos_equity_summary.json"),
}


@dataclass(frozen=True)
class Difference:
    """One reproducibility difference."""

    path: str
    reference: Any
    current: Any
    message: str


def load_json(path: Path) -> Any:
    """Load JSON file."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing JSON report: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def load_current_snapshot(project_root: Path) -> dict[str, Any]:
    """Load current critical report contents."""
    return {
        report_name: load_json(project_root / report_path)
        for report_name, report_path in CRITICAL_REPORTS.items()
    }


def is_number(value: Any) -> bool:
    """Return True for numeric values but not booleans."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def compare_values(
    reference: Any,
    current: Any,
    path: str,
    tolerance: float,
) -> list[Difference]:
    """Recursively compare two JSON-compatible values."""
    differences: list[Difference] = []

    if is_number(reference) and is_number(current):
        absolute_difference = abs(float(reference) - float(current))
        if absolute_difference > tolerance:
            differences.append(
                Difference(
                    path=path,
                    reference=reference,
                    current=current,
                    message=f"Numeric difference exceeds tolerance {tolerance}.",
                )
            )
        return differences

    if isinstance(reference, dict) and isinstance(current, dict):
        reference_keys = set(reference)
        current_keys = set(current)

        missing_keys = sorted(reference_keys.difference(current_keys))
        extra_keys = sorted(current_keys.difference(reference_keys))

        for key in missing_keys:
            differences.append(
                Difference(
                    path=f"{path}.{key}",
                    reference=reference[key],
                    current=None,
                    message="Missing key in current report.",
                )
            )

        for key in extra_keys:
            differences.append(
                Difference(
                    path=f"{path}.{key}",
                    reference=None,
                    current=current[key],
                    message="Extra key in current report.",
                )
            )

        for key in sorted(reference_keys.intersection(current_keys)):
            child_path = f"{path}.{key}"
            differences.extend(
                compare_values(
                    reference=reference[key],
                    current=current[key],
                    path=child_path,
                    tolerance=tolerance,
                )
            )

        return differences

    if isinstance(reference, list) and isinstance(current, list):
        if len(reference) != len(current):
            differences.append(
                Difference(
                    path=path,
                    reference=len(reference),
                    current=len(current),
                    message="List length differs.",
                )
            )
            return differences

        for index, (reference_item, current_item) in enumerate(
            zip(reference, current, strict=True)
        ):
            differences.extend(
                compare_values(
                    reference=reference_item,
                    current=current_item,
                    path=f"{path}[{index}]",
                    tolerance=tolerance,
                )
            )

        return differences

    if reference != current:
        differences.append(
            Difference(
                path=path,
                reference=reference,
                current=current,
                message="Value differs.",
            )
        )

    return differences


def write_snapshot(project_root: Path, output_path: Path) -> None:
    """Write current critical report snapshot."""
    snapshot = load_current_snapshot(project_root=project_root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    print(f"Saved reproducibility reference snapshot to: {output_path}")
    print(f"Report count: {len(snapshot)}")


def compare_against_reference(
    project_root: Path,
    reference_path: Path,
    output_path: Path,
    tolerance: float,
) -> None:
    """Compare current critical reports against a reference snapshot."""
    reference = load_json(reference_path)
    current = load_current_snapshot(project_root=project_root)

    differences = compare_values(
        reference=reference,
        current=current,
        path="reports",
        tolerance=tolerance,
    )

    output = {
        "passed": len(differences) == 0,
        "tolerance": tolerance,
        "difference_count": len(differences),
        "differences": [asdict(difference) for difference in differences],
        "checked_reports": sorted(CRITICAL_REPORTS),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Saved reproducibility comparison to: {output_path}")
    print(f"Difference count: {len(differences)}")

    if differences:
        preview = differences[:10]
        for difference in preview:
            print(
                f"[DIFF] {difference.path}: "
                f"reference={difference.reference}, current={difference.current}"
            )
        raise ValueError("Reproducibility comparison failed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify report reproducibility.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Project root directory.",
    )
    parser.add_argument(
        "--mode",
        choices=["snapshot", "compare"],
        required=True,
        help="Whether to write a reference snapshot or compare current reports.",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("reports/recovery_reproducibility_reference.json"),
        help="Reference snapshot path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/recovery_reproducibility_check.json"),
        help="Comparison output path.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-12,
        help="Absolute tolerance for numeric JSON values.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode == "snapshot":
        write_snapshot(project_root=args.project_root, output_path=args.reference)
        return

    compare_against_reference(
        project_root=args.project_root,
        reference_path=args.reference,
        output_path=args.output,
        tolerance=args.tolerance,
    )


if __name__ == "__main__":
    main()
