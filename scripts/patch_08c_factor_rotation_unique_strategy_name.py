from __future__ import annotations

from pathlib import Path


def patch_strategy_name(project_root: Path) -> None:
    """Include factor weights in factor-rotation strategy names."""
    path = project_root / "src" / "strategies" / "factor_rotation.py"
    text = path.read_text(encoding="utf-8")

    old = """        return (
            f"factor_rotation_m{self.momentum_window}"
            f"_v{self.volatility_window}"
            f"_d{self.drawdown_window}"
            f"_top{self.top_k}"
            f"_maxw{self.max_asset_weight:g}"
        )
"""
    new = """        return (
            f"factor_rotation_m{self.momentum_window}"
            f"_v{self.volatility_window}"
            f"_d{self.drawdown_window}"
            f"_mw{self.momentum_weight:g}"
            f"_vw{self.volatility_weight:g}"
            f"_dw{self.drawdown_weight:g}"
            f"_top{self.top_k}"
            f"_maxw{self.max_asset_weight:g}"
        )
"""

    if old not in text:
        raise ValueError("Expected strategy_name block not found.")

    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    patch_strategy_name(project_root=Path("."))


if __name__ == "__main__":
    main()
