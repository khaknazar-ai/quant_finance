from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.config.settings import load_universe_config
from src.risk.metrics import calculate_performance_metrics
from src.validation.schemas import validate_price_frame

from scripts.evaluate_baselines import make_json_safe_metrics
from scripts.evaluate_walk_forward_baselines import (
    build_cost_aware_baseline_returns,
    filter_returns_to_test_window,
    load_walk_forward_splits_report,
)


def stitch_walk_forward_returns(
    return_series_by_strategy: dict[str, pd.Series],
    splits: list[dict[str, Any]],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Stitch non-overlapping OOS split returns into one long return table."""
    frames: list[pd.DataFrame] = []
    split_windows: list[dict[str, Any]] = []

    for split in splits:
        aligned_returns = filter_returns_to_test_window(
            return_series_by_strategy=return_series_by_strategy,
            test_start=split["test_start"],
            test_end=split["test_end"],
        )

        common_index = next(iter(aligned_returns.values())).index

        split_windows.append(
            {
                "split_id": split["split_id"],
                "test_start": split["test_start"],
                "test_end": split["test_end"],
                "common_start_date": str(common_index.min().date()),
                "common_end_date": str(common_index.max().date()),
                "common_observation_count": int(len(common_index)),
            }
        )

        for strategy_name, returns in aligned_returns.items():
            frames.append(
                pd.DataFrame(
                    {
                        "date": returns.index,
                        "split_id": split["split_id"],
                        "strategy": strategy_name,
                        "oos_return": returns.to_numpy(),
                    }
                )
            )

    if not frames:
        raise ValueError("No OOS return frames were created.")

    stitched_returns = pd.concat(frames, ignore_index=True)
    stitched_returns = stitched_returns.sort_values(["strategy", "date"]).reset_index(drop=True)

    duplicated_dates = stitched_returns.duplicated(subset=["strategy", "date"])
    if duplicated_dates.any():
        raise ValueError("Overlapping split dates detected for at least one strategy.")

    return stitched_returns, split_windows


def add_stitched_equity(stitched_returns: pd.DataFrame) -> pd.DataFrame:
    """Add compounded stitched OOS equity per strategy."""
    required_columns = {"date", "split_id", "strategy", "oos_return"}
    missing_columns = required_columns.difference(stitched_returns.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    if stitched_returns.empty:
        raise ValueError("stitched_returns must not be empty.")

    output = stitched_returns.copy()
    output["date"] = pd.to_datetime(output["date"])
    output["oos_return"] = pd.to_numeric(output["oos_return"], errors="coerce")

    if output["oos_return"].isna().any():
        raise ValueError("oos_return must not contain NaN values.")

    output = output.sort_values(["strategy", "date"]).reset_index(drop=True)
    output["equity"] = output.groupby("strategy")["oos_return"].transform(
        lambda returns: (1.0 + returns).cumprod()
    )

    return output


def find_leader(
    strategy_summary: dict[str, dict[str, Any]],
    metric_name: str,
    higher_is_better: bool = True,
) -> str:
    """Find the leader by a strategy summary metric."""
    candidates: dict[str, float] = {}

    for strategy_name, summary in strategy_summary.items():
        if metric_name == "final_equity":
            value = summary.get("final_equity")
        else:
            value = summary.get("metrics", {}).get(metric_name)

        if value is not None:
            candidates[strategy_name] = float(value)

    if not candidates:
        return "n/a"

    if higher_is_better:
        return max(candidates, key=candidates.get)

    return min(candidates, key=candidates.get)


def summarize_stitched_equity(
    oos_equity: pd.DataFrame,
    risk_free_rate: float = 0.0,
) -> dict[str, dict[str, Any]]:
    """Summarize stitched OOS equity by strategy."""
    strategy_summary: dict[str, dict[str, Any]] = {}

    for strategy_name, strategy_frame in oos_equity.groupby("strategy"):
        sorted_frame = strategy_frame.sort_values("date")
        returns = pd.Series(
            sorted_frame["oos_return"].to_numpy(),
            index=pd.DatetimeIndex(sorted_frame["date"]),
            name=strategy_name,
        )

        metrics = calculate_performance_metrics(
            returns=returns,
            risk_free_rate=risk_free_rate,
        )

        strategy_summary[strategy_name] = {
            "start_date": str(sorted_frame["date"].min().date()),
            "end_date": str(sorted_frame["date"].max().date()),
            "observation_count": int(len(sorted_frame)),
            "final_equity": float(sorted_frame["equity"].iloc[-1]),
            "metrics": make_json_safe_metrics(metrics.to_dict()),
        }

    return strategy_summary


def build_stitched_oos_equity_report(
    prices: pd.DataFrame,
    splits_report: dict[str, Any],
    benchmark_ticker: str,
    universe_tickers: list[str],
    price_column: str = "adjusted_close",
    risk_free_rate: float = 0.0,
    momentum_lookback_days: int = 252,
    momentum_top_k: int = 5,
    momentum_rebalance_frequency: str = "ME",
    transaction_cost_bps: float = 10.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build stitched OOS equity curves and summary metadata."""
    baseline_returns, _ = build_cost_aware_baseline_returns(
        prices=prices,
        benchmark_ticker=benchmark_ticker,
        universe_tickers=universe_tickers,
        price_column=price_column,
        momentum_lookback_days=momentum_lookback_days,
        momentum_top_k=momentum_top_k,
        momentum_rebalance_frequency=momentum_rebalance_frequency,
        transaction_cost_bps=transaction_cost_bps,
    )

    stitched_returns, split_windows = stitch_walk_forward_returns(
        return_series_by_strategy=baseline_returns,
        splits=splits_report["splits"],
    )
    oos_equity = add_stitched_equity(stitched_returns)
    strategy_summary = summarize_stitched_equity(
        oos_equity=oos_equity,
        risk_free_rate=risk_free_rate,
    )

    strategies = sorted(strategy_summary)

    summary = {
        "evaluation_type": "walk_forward_baseline_oos_stitched_equity",
        "benchmark_ticker": benchmark_ticker,
        "universe_tickers": universe_tickers,
        "price_column": price_column,
        "risk_free_rate": risk_free_rate,
        "return_alignment": "exact_common_date_intersection_per_split",
        "evaluated_split_count": len(split_windows),
        "strategy_count": len(strategies),
        "strategies": strategies,
        "equity_base": 1.0,
        "momentum_lookback_days": momentum_lookback_days,
        "momentum_top_k": momentum_top_k,
        "momentum_rebalance_frequency": momentum_rebalance_frequency,
        "transaction_cost_bps": transaction_cost_bps,
        "cost_model": "net_return = gross_return - turnover * bps / 10000",
        "turnover_convention": "sum_abs_weight_change",
        "split_windows": split_windows,
        "strategy_summary": strategy_summary,
        "leaders": {
            "highest_stitched_cagr": find_leader(strategy_summary, "cagr"),
            "highest_stitched_sharpe": find_leader(strategy_summary, "sharpe"),
            "least_severe_stitched_max_drawdown": find_leader(
                strategy_summary,
                "max_drawdown",
            ),
            "highest_final_equity": find_leader(strategy_summary, "final_equity"),
        },
    }

    return oos_equity, summary


def run_build_walk_forward_oos_equity(
    input_path: Path,
    universe_config_path: Path,
    splits_path: Path,
    output_equity_path: Path,
    output_summary_path: Path,
) -> None:
    """Build and save stitched walk-forward OOS equity artifacts."""
    output_equity_path.parent.mkdir(parents=True, exist_ok=True)
    output_summary_path.parent.mkdir(parents=True, exist_ok=True)

    prices = pd.read_parquet(input_path)
    validated_prices = validate_price_frame(prices)
    universe_config = load_universe_config(universe_config_path)
    splits_report = load_walk_forward_splits_report(splits_path)

    oos_equity, summary = build_stitched_oos_equity_report(
        prices=validated_prices,
        splits_report=splits_report,
        benchmark_ticker=universe_config.universe.benchmark,
        universe_tickers=universe_config.universe.tickers,
        price_column="adjusted_close",
        risk_free_rate=0.0,
        momentum_lookback_days=252,
        momentum_top_k=5,
        momentum_rebalance_frequency="ME",
        transaction_cost_bps=10.0,
    )

    oos_equity.to_parquet(output_equity_path, index=False)
    output_summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Saved stitched OOS equity to: {output_equity_path}")
    print(f"Saved stitched OOS summary to: {output_summary_path}")
    print(f"Evaluation type: {summary['evaluation_type']}")
    print(f"Evaluated splits: {summary['evaluated_split_count']}")
    print(f"Strategy count: {summary['strategy_count']}")
    print(f"Leaders: {summary['leaders']}")

    for strategy_name in summary["strategies"]:
        strategy_summary = summary["strategy_summary"][strategy_name]
        metrics = strategy_summary["metrics"]
        print(
            f"{strategy_name}: "
            f"final_equity={strategy_summary['final_equity']}, "
            f"CAGR={metrics['cagr']}, "
            f"Sharpe={metrics['sharpe']}, "
            f"MaxDD={metrics['max_drawdown']}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build stitched walk-forward OOS baseline equity curves."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
        help="Input validated OHLCV parquet path.",
    )
    parser.add_argument(
        "--universe-config",
        type=Path,
        default=Path("configs/universe_etf.yaml"),
        help="Universe config YAML path.",
    )
    parser.add_argument(
        "--splits",
        type=Path,
        default=Path("reports/walk_forward_splits.json"),
        help="Walk-forward split report JSON path.",
    )
    parser.add_argument(
        "--output-equity",
        type=Path,
        default=Path("reports/walk_forward_baseline_oos_equity.parquet"),
        help="Output stitched OOS equity parquet path.",
    )
    parser.add_argument(
        "--output-summary",
        type=Path,
        default=Path("reports/walk_forward_baseline_oos_equity_summary.json"),
        help="Output stitched OOS equity summary JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_build_walk_forward_oos_equity(
        input_path=args.input,
        universe_config_path=args.universe_config,
        splits_path=args.splits,
        output_equity_path=args.output_equity,
        output_summary_path=args.output_summary,
    )


if __name__ == "__main__":
    main()
