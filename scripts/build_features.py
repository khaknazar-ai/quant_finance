from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.config.settings import load_features_config
from src.features.technical import build_technical_features, get_feature_columns
from src.validation.schemas import validate_price_frame


def build_feature_quality_report(
    features: pd.DataFrame,
    feature_columns: list[str],
    leakage_shift_days: int,
) -> dict[str, Any]:
    """Build a compact quality report for generated feature data."""
    complete_feature_mask = features[feature_columns].notna().all(axis=1)
    complete_feature_dates = features.loc[complete_feature_mask, "date"]

    first_complete_date = None
    if not complete_feature_dates.empty:
        first_complete_date = str(complete_feature_dates.min().date())

    return {
        "rows": int(len(features)),
        "tickers": sorted(features["ticker"].unique().tolist()),
        "ticker_count": int(features["ticker"].nunique()),
        "min_date": str(features["date"].min().date()),
        "max_date": str(features["date"].max().date()),
        "feature_count": int(len(feature_columns)),
        "feature_columns": feature_columns,
        "leakage_shift_days": int(leakage_shift_days),
        "complete_feature_rows": int(complete_feature_mask.sum()),
        "first_complete_feature_date": first_complete_date,
        "missing_values_by_feature": {
            column: int(value)
            for column, value in features[feature_columns].isna().sum().to_dict().items()
        },
        "non_null_ratio_by_feature": {
            column: float(value)
            for column, value in features[feature_columns].notna().mean().round(6).to_dict().items()
        },
    }


def run_build_features(
    input_path: Path,
    config_path: Path,
    output_path: Path,
    report_path: Path,
) -> None:
    """Read validated prices, build technical features, and save parquet output."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    prices = pd.read_parquet(input_path)
    validated_prices = validate_price_frame(prices)

    feature_config = load_features_config(config_path).features
    features = build_technical_features(prices=validated_prices, config=feature_config)
    feature_columns = get_feature_columns(features)

    features.to_parquet(output_path, index=False)

    report = build_feature_quality_report(
        features=features,
        feature_columns=feature_columns,
        leakage_shift_days=feature_config.leakage_control.shift_features_by_days,
    )
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved technical features to: {output_path}")
    print(f"Saved feature quality report to: {report_path}")
    print(f"Rows: {report['rows']}")
    print(f"Tickers: {report['ticker_count']}")
    print(f"Features: {report['feature_count']}")
    print(f"Complete feature rows: {report['complete_feature_rows']}")
    print(f"First complete feature date: {report['first_complete_feature_date']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build leakage-safe technical features.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
        help="Input validated OHLCV parquet path.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/features.yaml"),
        help="Feature config YAML path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/features/technical_features.parquet"),
        help="Output feature parquet path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/feature_quality_report.json"),
        help="Output feature quality report JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_build_features(
        input_path=args.input,
        config_path=args.config,
        output_path=args.output,
        report_path=args.report,
    )


if __name__ == "__main__":
    main()
