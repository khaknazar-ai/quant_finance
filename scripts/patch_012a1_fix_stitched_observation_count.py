from __future__ import annotations

from pathlib import Path

TARGET = Path("scripts/build_walk_forward_optimizer_stitched_oos_equity.py")


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    old = """        metrics[strategy_name] = build_metric_dict(
            net_returns=returns,
            risk_free_rate=risk_free_rate,
        )
"""

    new = """        strategy_metrics = build_metric_dict(
            net_returns=returns,
            risk_free_rate=risk_free_rate,
        )
        strategy_metrics["observation_count"] = int(len(returns))
        metrics[strategy_name] = strategy_metrics
"""

    if new in text:
        return

    if old not in text:
        raise ValueError("Could not find stitched metric assignment block.")

    TARGET.write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
