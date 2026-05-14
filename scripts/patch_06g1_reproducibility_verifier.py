from __future__ import annotations

from pathlib import Path


def patch_verifier_zip_strict(project_root: Path) -> None:
    """Add explicit strict=True to zip after list-length equality check."""
    path = project_root / "scripts" / "verify_report_reproducibility.py"
    text = path.read_text(encoding="utf-8")

    old = "enumerate(zip(reference, current))"
    new = "enumerate(zip(reference, current, strict=True))"

    if old not in text:
        raise ValueError(f"Expected verifier fragment not found: {old}")

    path.write_text(text.replace(old, new), encoding="utf-8")


def patch_test_helper_mkdir(project_root: Path) -> None:
    """Make test report helper idempotent."""
    path = project_root / "tests" / "test_verify_report_reproducibility.py"
    text = path.read_text(encoding="utf-8")

    old = "reports_dir.mkdir(parents=True)"
    new = "reports_dir.mkdir(parents=True, exist_ok=True)"

    if old not in text:
        raise ValueError(f"Expected test fragment not found: {old}")

    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    patch_verifier_zip_strict(project_root)
    patch_test_helper_mkdir(project_root)


if __name__ == "__main__":
    main()
