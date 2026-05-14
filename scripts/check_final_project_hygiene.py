from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

TEXT_FILES = [
    "README.md",
    "docs/experimental_protocol.md",
    "docs/report_index.md",
]


FORBIDDEN_PLACEHOLDER_PATTERNS = [
    r"\{walk_forward\[",
    r"\{stitched\[",
    r"\{inventory\[",
    r"\{aggregate\[",
    r"\{metrics\[",
    r"\{[^}\n]*_report\[",
]


FORBIDDEN_CV_PATTERNS = [
    r"## CV Bullets",
    r"### CV Bullets",
    r"Resume bullets",
]


FORBIDDEN_MISLEADING_CLAIMS = [
    r"\boutperforms SPY\b",
    r"\boutperformed SPY\b",
    r"\bbeats SPY\b",
    r"\bbeat SPY\b",
    r"\bmarket outperformance\b",
    r"\balpha claim\b",
]


REQUIRED_README_PHRASES = [
    "did not outperform SPY",
    "risk-control trade-off",
    "not a broad performance advantage",
    "Final Research Summary",
    "Final Stitched OOS Results",
    "Limitations",
    "Next Steps",
]


REQUIRED_NOTEBOOK_PHRASES = [
    "did not outperform SPY",
    "risk-control trade-off",
    "No bad results are removed",
]


@dataclass(frozen=True)
class HygieneCheck:
    name: str
    passed: bool
    details: str


def read_text(path: Path) -> str:
    """Read UTF-8 text."""
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict:
    """Read JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def check_no_forbidden_patterns(
    project_root: Path,
    name: str,
    file_paths: list[str],
    patterns: list[str],
) -> HygieneCheck:
    """Check that text files do not contain forbidden regex patterns."""
    violations: list[str] = []

    for relative_path in file_paths:
        path = project_root / relative_path
        text = read_text(path)
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append(f"{relative_path}: {pattern}")

    return HygieneCheck(
        name=name,
        passed=not violations,
        details="No violations." if not violations else "; ".join(violations),
    )


def check_required_phrases(
    project_root: Path,
    relative_path: str,
    phrases: list[str],
    name: str,
) -> HygieneCheck:
    """Check that required phrases are present."""
    text = read_text(project_root / relative_path)
    missing = [phrase for phrase in phrases if phrase not in text]

    return HygieneCheck(
        name=name,
        passed=not missing,
        details="All required phrases found." if not missing else f"Missing: {missing}",
    )


def check_notebook_content(project_root: Path) -> HygieneCheck:
    """Check generated final notebook has visible mixed-result interpretation."""
    path = project_root / "notebooks" / "01_research_results_review.ipynb"
    notebook = load_json(path)
    text = "".join("".join(cell.get("source", [])) for cell in notebook["cells"])

    missing = [phrase for phrase in REQUIRED_NOTEBOOK_PHRASES if phrase not in text]
    forbidden = [phrase for phrase in ["## CV Bullets", "CV Bullets"] if phrase in text]

    details: list[str] = []
    if missing:
        details.append(f"missing={missing}")
    if forbidden:
        details.append(f"forbidden={forbidden}")
    details.append(f"cell_count={len(notebook['cells'])}")

    return HygieneCheck(
        name="final_notebook_content",
        passed=not missing and not forbidden and len(notebook["cells"]) >= 12,
        details="; ".join(details),
    )


def check_artifact_inventory(project_root: Path) -> HygieneCheck:
    """Check artifact inventory is complete and includes the notebook."""
    inventory = load_json(project_root / "reports" / "report_artifact_inventory.json")
    artifact_count = inventory.get("artifact_count")
    missing_count = inventory.get("missing_count")
    artifacts = inventory.get("artifacts", [])

    notebook_present = any(
        item.get("path") == "notebooks/01_research_results_review.ipynb" for item in artifacts
    )

    final_hygiene_present = any(
        item.get("path") == "reports/final_project_hygiene_check.json" for item in artifacts
    )
    final_release_checklist_present = any(
        item.get("path") == "docs/final_release_checklist.md" for item in artifacts
    )

    passed = (
        artifact_count == 34
        and missing_count == 0
        and notebook_present
        and final_hygiene_present
        and final_release_checklist_present
    )
    details = (
        f"artifact_count={artifact_count}; "
        f"missing_count={missing_count}; "
        f"notebook_present={notebook_present}; "
        f"final_hygiene_present={final_hygiene_present}; "
        f"final_release_checklist_present={final_release_checklist_present}"
    )

    return HygieneCheck(
        name="artifact_inventory_complete",
        passed=passed,
        details=details,
    )


def check_final_metric_consistency(project_root: Path) -> HygieneCheck:
    """Check final stitched metrics match the intended interpretation."""
    stitched = load_json(
        project_root / "reports" / "walk_forward_optimizer_stitched_oos_equity_summary.json"
    )

    metrics = stitched["stitched_metrics"]
    spy = metrics["buy_hold_SPY"]
    optimizer = metrics["optimizer_selected_net"]

    optimizer_loses_return = optimizer["cagr"] < spy["cagr"]
    optimizer_loses_final_equity = optimizer["final_equity"] < spy["final_equity"]
    optimizer_improves_drawdown = optimizer["max_drawdown"] > spy["max_drawdown"]

    passed = optimizer_loses_return and optimizer_loses_final_equity and optimizer_improves_drawdown

    details = (
        f"optimizer_cagr={optimizer['cagr']}; spy_cagr={spy['cagr']}; "
        f"optimizer_final_equity={optimizer['final_equity']}; "
        f"spy_final_equity={spy['final_equity']}; "
        f"optimizer_max_dd={optimizer['max_drawdown']}; "
        f"spy_max_dd={spy['max_drawdown']}"
    )

    return HygieneCheck(
        name="final_metric_interpretation_consistent",
        passed=passed,
        details=details,
    )


def run_checks(project_root: Path) -> list[HygieneCheck]:
    """Run final project hygiene checks."""
    return [
        check_no_forbidden_patterns(
            project_root=project_root,
            name="no_unresolved_template_fragments",
            file_paths=TEXT_FILES,
            patterns=FORBIDDEN_PLACEHOLDER_PATTERNS,
        ),
        check_no_forbidden_patterns(
            project_root=project_root,
            name="no_cv_or_resume_sections",
            file_paths=TEXT_FILES + ["scripts/build_final_results_notebook.py"],
            patterns=FORBIDDEN_CV_PATTERNS,
        ),
        check_no_forbidden_patterns(
            project_root=project_root,
            name="no_misleading_outperformance_claims",
            file_paths=TEXT_FILES,
            patterns=FORBIDDEN_MISLEADING_CLAIMS,
        ),
        check_required_phrases(
            project_root=project_root,
            relative_path="README.md",
            phrases=REQUIRED_README_PHRASES,
            name="readme_required_final_phrases",
        ),
        check_notebook_content(project_root),
        check_artifact_inventory(project_root),
        check_final_metric_consistency(project_root),
    ]


def write_report(checks: list[HygieneCheck], output_path: Path) -> None:
    """Write machine-readable hygiene report."""
    output = {
        "passed": all(check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check final project hygiene.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/final_project_hygiene_check.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checks = run_checks(args.project_root)
    write_report(checks, args.output)

    for check in checks:
        status = "OK" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.details}")

    if not all(check.passed for check in checks):
        raise SystemExit(1)

    print(f"Saved final hygiene report to: {args.output}")


if __name__ == "__main__":
    main()
