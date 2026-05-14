from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.ingestion.yfinance_loader import download_price_history_from_config
from src.validation.schemas import validate_price_frame


def build_quality_report(df: pd.DataFrame) -> dict[str, Any]:
    """Build a compact data quality report for validated OHLCV data."""
    return {
        "rows": int(len(df)),
        "tickers": sorted(df["ticker"].unique().tolist()),
        "ticker_count": int(df["ticker"].nunique()),
        "min_date": str(df["date"].min().date()),
        "max_date": str(df["date"].max().date()),
        "rows_per_ticker": {
            ticker: int(count)
            for ticker, count in df.groupby("ticker", observed=True).size().to_dict().items()
        },
        "missing_values_by_column": {
            column: int(value) for column, value in df.isna().sum().to_dict().items()
        },
    }


def run_download(config_path: Path, output_path: Path, report_path: Path) -> None:
    """Download, validate, and save canonical OHLCV price data."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    raw_prices = download_price_history_from_config(config_path)
    validated_prices = validate_price_frame(raw_prices)

    validated_prices.to_parquet(output_path, index=False)

    report = build_quality_report(validated_prices)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved validated prices to: {output_path}")
    print(f"Saved data quality report to: {report_path}")
    print(f"Rows: {report['rows']}")
    print(f"Tickers: {report['ticker_count']}")
    print(f"Date range: {report['min_date']} -> {report['max_date']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and validate ETF OHLCV data.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/universe_etf.yaml"),
        help="Path to universe config YAML.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
        help="Output parquet path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/data_quality_prices.json"),
        help="Output JSON data quality report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_download(config_path=args.config, output_path=args.output, report_path=args.report)


if __name__ == "__main__":
    main()
