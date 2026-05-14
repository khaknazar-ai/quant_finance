from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentationCheck:
    """A documentation integrity check."""

    name: str
    passed: bool
    message: str


def read_text(path: Path) -> str:
    """Read text as UTF-8."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing documentation file: {path}")

    return path.read_text(encoding="utf-8")


def check_no_mojibake(project_root: Path, relative_paths: list[str]) -> DocumentationCheck:
    """Ensure common mojibake fragments are absent."""
    bad_fragments = ["\u0432\u0402", "\ufffd"]

    offenders: list[str] = []
    for relative_path in relative_paths:
        text = read_text(project_root / relative_path)
        if any(fragment in text for fragment in bad_fragments):
            offenders.append(relative_path)

    return DocumentationCheck(
        name="no_mojibake",
        passed=not offenders,
        message=(
            "No mojibake fragments found."
            if not offenders
            else f"Mojibake fragments found in: {', '.join(offenders)}"
        ),
    )


def check_protocol_current_baseline_section(project_root: Path) -> DocumentationCheck:
    """Ensure protocol has the current baseline evidence section."""
    text = read_text(project_root / "docs/experimental_protocol.md")

    required_fragments = [
        "## Current Baseline Evidence",
        "momentum_top_5_252d_net_10bps",
        "Transaction cost assumption: 10 bps",
        "net_return = gross_return - turnover * bps / 10000",
        "risk-return trade-off",
        "Mean split CAGR and stitched OOS CAGR are different quantities",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in text]

    return DocumentationCheck(
        name="protocol_current_baseline_section",
        passed=not missing,
        message=(
            "Experimental protocol contains current baseline evidence section."
            if not missing
            else f"Missing protocol fragments: {missing}"
        ),
    )


def check_no_stale_cost_claims(project_root: Path) -> DocumentationCheck:
    """Ensure docs do not claim that baseline costs are absent."""
    relative_paths = [
        "README.md",
        "docs/report_index.md",
        "docs/experimental_protocol.md",
    ]
    stale_fragments = [
        "no costs yet",
        "No transaction costs yet",
        "full-period baseline excludes costs",
        "Full-period baseline excludes costs",
    ]

    offenders: list[str] = []
    for relative_path in relative_paths:
        text = read_text(project_root / relative_path)
        if any(fragment in text for fragment in stale_fragments):
            offenders.append(relative_path)

    return DocumentationCheck(
        name="no_stale_cost_claims",
        passed=not offenders,
        message=(
            "No stale transaction-cost claims found."
            if not offenders
            else f"Stale transaction-cost claims found in: {', '.join(offenders)}"
        ),
    )


def check_report_index_links(project_root: Path) -> DocumentationCheck:
    """Ensure report index mentions the core generated artifacts."""
    text = read_text(project_root / "docs/report_index.md")

    required_fragments = [
        "reports/baseline_metrics_summary.md",
        "reports/walk_forward_baseline_summary.md",
        "reports/walk_forward_baseline_oos_equity_summary.md",
        "reports/report_artifact_inventory.json",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in text]

    return DocumentationCheck(
        name="report_index_links",
        passed=not missing,
        message=(
            "Report index includes core generated artifacts."
            if not missing
            else f"Missing report index fragments: {missing}"
        ),
    )


def run_checks(project_root: Path) -> list[DocumentationCheck]:
    """Run all documentation integrity checks."""
    relative_paths = [
        "README.md",
        "docs/report_index.md",
        "docs/experimental_protocol.md",
    ]

    return [
        check_no_mojibake(project_root=project_root, relative_paths=relative_paths),
        check_protocol_current_baseline_section(project_root=project_root),
        check_no_stale_cost_claims(project_root=project_root),
        check_report_index_links(project_root=project_root),
    ]


def run_check(project_root: Path) -> None:
    """Run checks and fail if any documentation integrity check fails."""
    checks = run_checks(project_root=project_root)
    failed_checks = [check for check in checks if not check.passed]

    for check in checks:
        status = "OK" if check.passed else "FAILED"
        print(f"[{status}] {check.name}: {check.message}")

    if failed_checks:
        names = ", ".join(check.name for check in failed_checks)
        raise ValueError(f"Documentation integrity checks failed: {names}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check documentation integrity.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Project root directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_check(project_root=args.project_root)


if __name__ == "__main__":
    main()
