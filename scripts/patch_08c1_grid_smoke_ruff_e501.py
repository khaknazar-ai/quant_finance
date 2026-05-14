from __future__ import annotations

from pathlib import Path


def patch_grid_smoke_summary_header(project_root: Path) -> None:
    """Split long Markdown table header to satisfy Ruff E501."""
    path = project_root / "scripts" / "evaluate_factor_rotation_grid_smoke.py"
    text = path.read_text(encoding="utf-8")

    old = (
        '            "| Candidate | Valid | CAGR | Sharpe | Max Drawdown | '
        'Avg Turnover | Top-K | Windows | Factor Weights |",\n'
    )
    new = (
        "            (\n"
        '                "| Candidate | Valid | CAGR | Sharpe | Max Drawdown | "\n'
        '                "Avg Turnover | Top-K | Windows | Factor Weights |"\n'
        "            ),\n"
    )

    if old in text:
        path.write_text(text.replace(old, new), encoding="utf-8")
        return

    already_patched = (
        '"| Candidate | Valid | CAGR | Sharpe | Max Drawdown | "\n'
        '                "Avg Turnover | Top-K | Windows | Factor Weights |"'
    )
    if already_patched in text:
        return

    raise ValueError("Expected Markdown table header block not found.")


def main() -> None:
    patch_grid_smoke_summary_header(project_root=Path("."))


if __name__ == "__main__":
    main()
