from __future__ import annotations

from pathlib import Path


def patch_baselines_error_messages(project_root: Path) -> None:
    """Restore error-message compatibility expected by existing tests."""
    path = project_root / "src" / "strategies" / "baselines.py"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "raise ValueError(f\"Ticker '{ticker}' is not present in asset_returns.\")": (
            'raise ValueError(f"Ticker not found: {ticker}")'
        ),
        'raise ValueError("top_k must be less than or equal to the number of assets.")': (
            'raise ValueError("top_k cannot exceed the number of assets.")'
        ),
    }

    for old, new in replacements.items():
        if old not in text:
            raise ValueError(f"Expected baselines.py fragment not found: {old}")
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def patch_experimental_protocol(project_root: Path) -> None:
    """Remove stale transaction-cost claims from the experimental protocol."""
    path = project_root / "docs" / "experimental_protocol.md"
    text = path.read_text(encoding="utf-8")

    replacements = {
        "no costs yet": ("transaction costs are included for the momentum net baseline at 10 bps"),
        "No transaction costs yet": (
            "Transaction costs are included for the momentum net baseline at 10 bps"
        ),
        "full-period baseline excludes costs": (
            "full-period baseline includes gross momentum and 10 bps net momentum"
        ),
        "Full-period baseline excludes costs": (
            "Full-period baseline includes gross momentum and 10 bps net momentum"
        ),
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    stale_fragments = [
        "no costs yet",
        "No transaction costs yet",
        "full-period baseline excludes costs",
        "Full-period baseline excludes costs",
    ]
    remaining = [fragment for fragment in stale_fragments if fragment in text]
    if remaining:
        raise ValueError(f"Stale protocol fragments still present: {remaining}")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    project_root = Path(".")
    patch_baselines_error_messages(project_root)
    patch_experimental_protocol(project_root)


if __name__ == "__main__":
    main()
