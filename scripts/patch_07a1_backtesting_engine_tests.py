from __future__ import annotations

from pathlib import Path


def patch_backtesting_engine_tests(project_root: Path) -> None:
    """Use sliced DatetimeIndex in expected Series to preserve freq metadata."""
    path = project_root / "tests" / "test_backtesting_engine.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "index=[dates[1], dates[2], dates[3], dates[4]],": "index=dates[1:],",
    }

    for old, new in replacements.items():
        if old not in text:
            raise ValueError(f"Expected test fragment not found: {old}")

        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_backtesting_engine_tests(project_root=Path("."))


if __name__ == "__main__":
    main()
