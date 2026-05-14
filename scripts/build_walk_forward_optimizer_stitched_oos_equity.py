from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.optimization.objective import build_metric_dict
from src.strategies.factor_rotation import FactorRotationParameters

from scripts.evaluate_factor_rotation_grid_smoke import (
    format_float,
    format_percent,
    load_universe_price_matrix,
)
from scripts.run_one_split_optimizer_selection import (
    align_return_series_to_common_index,
    evaluate_selected_factor_rotation_on_test_window,
)
from scripts.run_walk_forward_optimizer_selection import build_test_baseline_returns


def load_walk_forward_optimizer_report(path: Path) -> dict[str, Any]:
    """Load the frozen walk-forward optimizer-selection report."""
    report = json.loads(path.read_text(encoding="utf-8"))

    if report.get("evaluation_type") != "walk_forward_optimizer_selection_oos":
        raise ValueError("Input report is not a walk-forward optimizer-selection report.")

    if not report.get("split_reports"):
        raise ValueError("Input report does not contain split_reports.")

    return report


def selected_parameters_from_split_report(
    split_report: dict[str, Any],
) -> FactorRotationParameters:
    """Extract selected factor-rotation parameters from a split report."""
    parameters = split_report["selected_train_evaluation"]["parameters"]
    return FactorRotationParameters(**parameters)


def build_stitched_oos_return_frame(
    price_matrix: pd.DataFrame,
    optimizer_report: dict[str, Any],
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_test_return_observations: int,
    benchmark_ticker: str,
    momentum_lookback_days: int,
    momentum_top_k: int,
    momentum_rebalance_frequency: str,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Rebuild selected optimizer and baseline OOS returns and stitch them.

    Each split uses the exact common date intersection across strategies.
    This keeps the comparison fair, but it can exclude early test-window
    days when lagged/rebalanced strategies do not yet have valid returns.
    """
    records: list[dict[str, Any]] = []
    split_windows: list[dict[str, Any]] = []

    for split_report in optimizer_report["split_reports"]:
        split_index = int(split_report["split_index"])
        test_start = str(split_report["test_start"])
        test_end = str(split_report["test_end"])
        selected_parameters = selected_parameters_from_split_report(split_report)

        selected_test_evaluation = evaluate_selected_factor_rotation_on_test_window(
            price_matrix=price_matrix,
            parameters=selected_parameters,
            test_start=test_start,
            test_end=test_end,
            transaction_cost_bps=transaction_cost_bps,
            risk_free_rate=risk_free_rate,
            min_test_return_observations=min_test_return_observations,
        )

        if not selected_test_evaluation["valid"]:
            raise ValueError(
                f"Selected optimizer strategy is invalid on split {split_index}: "
                f"{selected_test_evaluation['invalid_reason']}"
            )

        baseline_returns = build_test_baseline_returns(
            price_matrix=price_matrix,
            test_start=test_start,
            test_end=test_end,
            benchmark_ticker=benchmark_ticker,
            transaction_cost_bps=transaction_cost_bps,
            momentum_lookback_days=momentum_lookback_days,
            momentum_top_k=momentum_top_k,
            momentum_rebalance_frequency=momentum_rebalance_frequency,
        )

        return_series = {
            "optimizer_selected_net": selected_test_evaluation["net_returns"],
            **baseline_returns,
        }
        aligned_returns, common_index = align_return_series_to_common_index(return_series)

        split_windows.append(
            {
                "split_index": split_index,
                "test_start": test_start,
                "test_end": test_end,
                "common_start": str(common_index.min().date()),
                "common_end": str(common_index.max().date()),
                "common_observation_count": int(len(common_index)),
                "selected_candidate_id": split_report["selected_train_evaluation"]["candidate_id"],
            }
        )

        for strategy_name, returns in aligned_returns.items():
            for date, daily_return in returns.items():
                records.append(
                    {
                        "date": pd.Timestamp(date),
                        "split_index": split_index,
                        "strategy_name": strategy_name,
                        "daily_return": float(daily_return),
                    }
                )

    if not records:
        raise ValueError("No stitched OOS return records were generated.")

    return_frame = pd.DataFrame.from_records(records)
    return return_frame.sort_values(["strategy_name", "date"]), split_windows


def build_stitched_equity_frame(return_frame: pd.DataFrame) -> pd.DataFrame:
    """Compound stitched daily returns into equity curves per strategy."""
    required_columns = {"date", "split_index", "strategy_name", "daily_return"}
    missing_columns = required_columns.difference(return_frame.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    equity_frame = return_frame.copy()
    equity_frame["date"] = pd.to_datetime(equity_frame["date"])
    equity_frame = equity_frame.sort_values(["strategy_name", "date"])

    if equity_frame.duplicated(["strategy_name", "date"]).any():
        raise ValueError("Duplicate strategy/date rows found in stitched return frame.")

    equity_frame["equity"] = equity_frame.groupby("strategy_name")["daily_return"].transform(
        lambda series: (1.0 + series).cumprod()
    )

    return equity_frame


def calculate_stitched_metrics(
    equity_frame: pd.DataFrame,
    risk_free_rate: float,
) -> dict[str, dict[str, float | int | None]]:
    """Calculate stitched OOS metrics for each strategy."""
    metrics: dict[str, dict[str, float | int | None]] = {}

    for strategy_name, group in equity_frame.groupby("strategy_name"):
        returns = group.sort_values("date").set_index("date")["daily_return"].astype("float64")
        strategy_metrics = build_metric_dict(
            net_returns=returns,
            risk_free_rate=risk_free_rate,
        )
        strategy_metrics["observation_count"] = int(len(returns))
        metrics[strategy_name] = strategy_metrics

    return metrics


def find_stitched_metric_leaders(
    stitched_metrics: dict[str, dict[str, float | int | None]],
) -> dict[str, dict[str, Any] | None]:
    """Find stitched OOS metric leaders."""
    leader_specs = {
        "highest_stitched_cagr": ("cagr", True),
        "highest_stitched_sharpe": ("sharpe", True),
        "least_severe_stitched_max_drawdown": ("max_drawdown", True),
        "highest_stitched_calmar": ("calmar", True),
        "highest_final_equity": ("final_equity", True),
    }

    leaders: dict[str, dict[str, Any] | None] = {}

    for leader_name, (metric_name, maximize) in leader_specs.items():
        scored: list[tuple[float, str]] = []

        for strategy_name, metrics in stitched_metrics.items():
            value = metrics.get(metric_name)
            if value is not None:
                scored.append((float(value), strategy_name))

        if not scored:
            leaders[leader_name] = None
            continue

        scored = sorted(scored, key=lambda item: item[0], reverse=maximize)
        best_value, best_strategy = scored[0]
        leaders[leader_name] = {
            "strategy_name": best_strategy,
            "metric": metric_name,
            "value": best_value,
        }

    return leaders


def build_optimizer_vs_spy_deltas(
    stitched_metrics: dict[str, dict[str, float | int | None]],
) -> dict[str, float | None]:
    """Calculate optimizer minus SPY stitched metric deltas."""
    optimizer = stitched_metrics.get("optimizer_selected_net", {})
    spy = stitched_metrics.get("buy_hold_SPY", {})

    deltas: dict[str, float | None] = {}
    for metric_name in ["cagr", "sharpe", "max_drawdown", "calmar", "final_equity"]:
        optimizer_value = optimizer.get(metric_name)
        spy_value = spy.get(metric_name)

        if optimizer_value is None or spy_value is None:
            deltas[f"{metric_name}_optimizer_minus_spy"] = None
        else:
            deltas[f"{metric_name}_optimizer_minus_spy"] = float(optimizer_value) - float(spy_value)

    return deltas


def build_stitched_report(
    optimizer_report_path: Path,
    equity_output_path: Path,
    equity_frame: pd.DataFrame,
    split_windows: list[dict[str, Any]],
    stitched_metrics: dict[str, dict[str, float | int | None]],
    transaction_cost_bps: float,
    risk_free_rate: float,
) -> dict[str, Any]:
    """Build stitched OOS equity report."""
    return {
        "evaluation_type": "walk_forward_optimizer_stitched_oos_equity",
        "protocol": (
            "Uses selected candidates from the frozen walk-forward optimizer "
            "report. No re-optimization is performed. For each split, selected "
            "optimizer and baselines are aligned to the exact common OOS date "
            "intersection, then returns are stitched into continuous equity curves."
        ),
        "source_optimizer_report": str(optimizer_report_path),
        "equity_curve_path": str(equity_output_path),
        "transaction_cost_bps": transaction_cost_bps,
        "risk_free_rate": risk_free_rate,
        "evaluated_split_count": len(split_windows),
        "strategy_count": int(equity_frame["strategy_name"].nunique()),
        "stitched_start": str(equity_frame["date"].min().date()),
        "stitched_end": str(equity_frame["date"].max().date()),
        "row_count": int(len(equity_frame)),
        "split_common_windows": split_windows,
        "stitched_metrics": stitched_metrics,
        "stitched_metric_leaders": find_stitched_metric_leaders(stitched_metrics),
        "optimizer_vs_spy_deltas": build_optimizer_vs_spy_deltas(stitched_metrics),
        "interpretation_rule": (
            "This is stitched OOS backtest evidence. If optimizer has lower "
            "CAGR/final equity than SPY but better drawdown, report it as a "
            "risk-control trade-off, not broad outperformance."
        ),
    }


def build_stitched_summary(report: dict[str, Any]) -> str:
    """Build Markdown summary for stitched OOS equity report."""
    lines = [
        "# Stitched Walk-Forward OOS Equity Report",
        "",
        "## Protocol",
        "",
        "- Uses selected candidates from the frozen walk-forward optimizer report.",
        "- No re-optimization is performed in this step.",
        "- Each split is aligned to the exact common OOS date intersection.",
        "- Daily OOS returns are stitched into continuous equity curves.",
        f"- Evaluated splits: `{report['evaluated_split_count']}`.",
        f"- Stitched window: `{report['stitched_start']}` to " f"`{report['stitched_end']}`.",
        f"- Transaction cost: `{report['transaction_cost_bps']}` bps.",
        "",
        "## Stitched OOS Metrics",
        "",
        "| Strategy | Stitched CAGR | Sharpe | Max Drawdown | Calmar | "
        "Final Equity | Observations |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for strategy_name, metrics in sorted(report["stitched_metrics"].items()):
        lines.append(
            "| "
            f"`{strategy_name}` | "
            f"{format_percent(metrics.get('cagr'))} | "
            f"{format_float(metrics.get('sharpe'))} | "
            f"{format_percent(metrics.get('max_drawdown'))} | "
            f"{format_float(metrics.get('calmar'))} | "
            f"{format_float(metrics.get('final_equity'))} | "
            f"{metrics.get('observation_count')} |"
        )

    lines.extend(["", "## Stitched Metric Leaders", ""])

    for leader_name, leader in report["stitched_metric_leaders"].items():
        if leader is None:
            lines.append(f"- {leader_name}: n/a")
        else:
            lines.append(
                f"- {leader_name}: `{leader['strategy_name']}`, " f"value `{leader['value']:.6f}`"
            )

    lines.extend(["", "## Optimizer vs SPY Deltas", ""])

    for key, value in report["optimizer_vs_spy_deltas"].items():
        if value is None:
            lines.append(f"- {key}: n/a")
        elif "cagr" in key or "drawdown" in key:
            lines.append(f"- {key}: {format_percent(value)}")
        else:
            lines.append(f"- {key}: {format_float(value)}")

    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "This report should not be framed as broad optimizer "
            "outperformance unless the optimizer wins the relevant return and "
            "risk-adjusted metrics. If it mainly improves drawdown while losing "
            "CAGR or final equity versus SPY, the correct interpretation is a "
            "risk-control trade-off.",
            "",
        ]
    )

    return "\n".join(lines)


def run_walk_forward_optimizer_stitched_oos_equity(
    prices_path: Path,
    universe_config_path: Path,
    optimizer_report_path: Path,
    equity_output_path: Path,
    summary_json_output_path: Path,
    summary_md_output_path: Path,
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_test_return_observations: int,
    benchmark_ticker: str,
    momentum_lookback_days: int,
    momentum_top_k: int,
    momentum_rebalance_frequency: str,
) -> dict[str, Any]:
    """Build stitched OOS equity for optimizer and baselines."""
    optimizer_report = load_walk_forward_optimizer_report(optimizer_report_path)
    price_matrix = load_universe_price_matrix(
        prices_path=prices_path,
        universe_config_path=universe_config_path,
    )

    return_frame, split_windows = build_stitched_oos_return_frame(
        price_matrix=price_matrix,
        optimizer_report=optimizer_report,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        min_test_return_observations=min_test_return_observations,
        benchmark_ticker=benchmark_ticker,
        momentum_lookback_days=momentum_lookback_days,
        momentum_top_k=momentum_top_k,
        momentum_rebalance_frequency=momentum_rebalance_frequency,
    )
    equity_frame = build_stitched_equity_frame(return_frame)
    stitched_metrics = calculate_stitched_metrics(
        equity_frame=equity_frame,
        risk_free_rate=risk_free_rate,
    )

    report = build_stitched_report(
        optimizer_report_path=optimizer_report_path,
        equity_output_path=equity_output_path,
        equity_frame=equity_frame,
        split_windows=split_windows,
        stitched_metrics=stitched_metrics,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
    )

    equity_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_output_path.parent.mkdir(parents=True, exist_ok=True)

    equity_frame.to_parquet(equity_output_path, index=False)
    summary_json_output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_md_output_path.write_text(build_stitched_summary(report), encoding="utf-8")

    print(f"Saved stitched OOS equity to: {equity_output_path}")
    print(f"Saved stitched OOS summary JSON to: {summary_json_output_path}")
    print(f"Saved stitched OOS summary Markdown to: {summary_md_output_path}")
    print(f"Evaluated splits: {report['evaluated_split_count']}")
    print(f"Stitched window: {report['stitched_start']} -> {report['stitched_end']}")
    print(f"Stitched metric leaders: {report['stitched_metric_leaders']}")
    print(f"Optimizer vs SPY deltas: {report['optimizer_vs_spy_deltas']}")

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build stitched OOS equity for optimizer and baselines."
    )
    parser.add_argument(
        "--prices",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
    )
    parser.add_argument(
        "--universe-config",
        type=Path,
        default=Path("configs/universe_etf.yaml"),
    )
    parser.add_argument(
        "--optimizer-report",
        type=Path,
        default=Path("reports/walk_forward_optimizer_selection.json"),
    )
    parser.add_argument(
        "--equity-output",
        type=Path,
        default=Path("reports/walk_forward_optimizer_stitched_oos_equity.parquet"),
    )
    parser.add_argument(
        "--summary-json-output",
        type=Path,
        default=Path("reports/walk_forward_optimizer_stitched_oos_equity_summary.json"),
    )
    parser.add_argument(
        "--summary-md-output",
        type=Path,
        default=Path("reports/walk_forward_optimizer_stitched_oos_equity_summary.md"),
    )
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--min-test-return-observations", type=int, default=100)
    parser.add_argument("--benchmark-ticker", type=str, default="SPY")
    parser.add_argument("--momentum-lookback-days", type=int, default=252)
    parser.add_argument("--momentum-top-k", type=int, default=5)
    parser.add_argument("--momentum-rebalance-frequency", type=str, default="ME")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_walk_forward_optimizer_stitched_oos_equity(
        prices_path=args.prices,
        universe_config_path=args.universe_config,
        optimizer_report_path=args.optimizer_report,
        equity_output_path=args.equity_output,
        summary_json_output_path=args.summary_json_output,
        summary_md_output_path=args.summary_md_output,
        transaction_cost_bps=args.transaction_cost_bps,
        risk_free_rate=args.risk_free_rate,
        min_test_return_observations=args.min_test_return_observations,
        benchmark_ticker=args.benchmark_ticker,
        momentum_lookback_days=args.momentum_lookback_days,
        momentum_top_k=args.momentum_top_k,
        momentum_rebalance_frequency=args.momentum_rebalance_frequency,
    )


if __name__ == "__main__":
    main()
