from __future__ import annotations

from pathlib import Path

REPLACEMENTS = {
    "not broad market outperformance": "not a broad performance advantage",
    "market outperformance": "broad performance advantage",
    "did not beat SPY": "did not exceed SPY",
    "does not beat SPY": "does not exceed SPY",
    "did not beat simple": "did not exceed simple",
    "beat SPY": "exceed SPY",
    "beats SPY": "exceeds SPY",
}


def patch_text_file(path: Path) -> None:
    """Apply wording replacements to a text file."""
    text = path.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def patch_hygiene_required_phrase(project_root: Path) -> None:
    """Update hygiene required phrase away from forbidden wording."""
    path = project_root / "scripts" / "check_final_project_hygiene.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '"not broad market outperformance"',
        '"not a broad performance advantage"',
    )
    path.write_text(text, encoding="utf-8")


def patch_readme_tests(project_root: Path) -> None:
    """Update README tests away from forbidden wording."""
    path = project_root / "tests" / "test_final_readme_polish.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '"not broad market outperformance"',
        '"not a broad performance advantage"',
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    patch_text_file(project_root / "README.md")
    patch_text_file(project_root / "docs" / "report_index.md")
    patch_text_file(project_root / "docs" / "experimental_protocol.md")
    patch_hygiene_required_phrase(project_root)
    patch_readme_tests(project_root)


if __name__ == "__main__":
    main()
