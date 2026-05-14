from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.backtesting.walk_forward import generate_walk_forward_splits
from src.config.settings import load_walk_forward_config
from src.features.technical import get_feature_columns


def build_walk_forward_report(
    features: pd.DataFrame,
    config_path: Path,
    require_complete_features: bool = True,
) -> dict[str, Any]:
    """Build walk-forward split report from a feature dataframe."""
    if "date" not in features.columns:
        raise ValueError("features dataframe must contain a date column.")

    feature_columns = get_feature_columns(features)
    if require_complete_features and not feature_columns:
        raise ValueError("No feature columns found for complete-feature filtering.")

    if require_complete_features:
        complete_mask = features[feature_columns].notna().all(axis=1)
        eligible_dates = features.loc[complete_mask, "date"]
    else:
        eligible_dates = features["date"]

    eligible_dates = pd.Series(pd.to_datetime(eligible_dates).dropna().unique()).sort_values()

    if eligible_dates.empty:
        raise ValueError("No eligible dates available for walk-forward splitting.")

    walk_forward_config = load_walk_forward_config(config_path).walk_forward
    splits = generate_walk_forward_splits(dates=eligible_dates, config=walk_forward_config)

    return {
        "input_rows": int(len(features)),
        "require_complete_features": bool(require_complete_features),
        "feature_count": int(len(feature_columns)),
        "eligible_date_count": int(len(eligible_dates)),
        "eligible_min_date": str(eligible_dates.min().date()),
        "eligible_max_date": str(eligible_dates.max().date()),
        "train_years": int(walk_forward_config.train_years),
        "test_years": int(walk_forward_config.test_years),
        "step_years": int(walk_forward_config.step_years),
        "min_train_observations": int(walk_forward_config.min_train_observations),
        "split_count": int(len(splits)),
        "splits": [split.to_dict() for split in splits],
    }


def run_generate_splits(
    input_path: Path,
    config_path: Path,
    output_path: Path,
) -> None:
    """Read feature data, generate walk-forward splits, and save JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    features = pd.read_parquet(input_path)
    report = build_walk_forward_report(
        features=features,
        config_path=config_path,
        require_complete_features=True,
    )

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved walk-forward splits to: {output_path}")
    print(f"Input rows: {report['input_rows']}")
    print(f"Eligible dates: {report['eligible_date_count']}")
    print(f"Eligible date range: {report['eligible_min_date']} -> {report['eligible_max_date']}")
    print(f"Split count: {report['split_count']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate walk-forward split report.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/features/technical_features.parquet"),
        help="Input technical feature parquet path.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/walk_forward.yaml"),
        help="Walk-forward config YAML path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/walk_forward_splits.json"),
        help="Output walk-forward split JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_generate_splits(
        input_path=args.input,
        config_path=args.config,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
