from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.config.settings import load_universe_config
from src.optimization.objective import evaluate_factor_rotation_parameters_on_window
from src.strategies.baselines import build_price_matrix
from src.strategies.factor_rotation import FactorRotationParameters
from src.validation.schemas import validate_price_frame


def format_percent(value: float | int | None) -> str:
    """Format decimal value as percentage."""
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def format_float(value: float | int | None, digits: int = 3) -> str:
    """Format numeric value."""
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def build_smoke_parameter_grid() -> list[FactorRotationParameters]:
    """Build a small deterministic parameter grid for objective smoke testing."""
    return [
        FactorRotationParameters(
            momentum_window=63,
            volatility_window=21,
            drawdown_window=63,
            momentum_weight=1.0,
            volatility_weight=0.0,
            drawdown_weight=0.0,
            top_k=5,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=126,
            volatility_window=63,
            drawdown_window=126,
            momentum_weight=1.0,
            volatility_weight=0.5,
            drawdown_weight=0.5,
            top_k=5,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=252,
            volatility_window=63,
            drawdown_window=126,
            momentum_weight=1.0,
            volatility_weight=1.0,
            drawdown_weight=0.5,
            top_k=5,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=126,
            volatility_window=21,
            drawdown_window=63,
            momentum_weight=0.5,
            volatility_weight=1.0,
            drawdown_weight=1.0,
            top_k=5,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=63,
            volatility_window=63,
            drawdown_window=63,
            momentum_weight=1.0,
            volatility_weight=0.5,
            drawdown_weight=0.0,
            top_k=3,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=126,
            volatility_window=126,
            drawdown_window=126,
            momentum_weight=1.0,
            volatility_weight=1.0,
            drawdown_weight=1.0,
            top_k=3,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=252,
            volatility_window=126,
            drawdown_window=252,
            momentum_weight=1.0,
            volatility_weight=0.5,
            drawdown_weight=1.0,
            top_k=3,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=126,
            volatility_window=63,
            drawdown_window=126,
            momentum_weight=1.0,
            volatility_weight=0.5,
            drawdown_weight=0.5,
            top_k=2,
            max_asset_weight=0.4,
            rebalance_frequency="ME",
        ),
    ]


def get_split_value(split: dict[str, Any], candidate_keys: list[str]) -> str:
    """Read a split date using a flexible key list."""
    for key in candidate_keys:
        if key in split:
            return str(split[key])

    raise KeyError(f"None of these split keys were found: {candidate_keys}")


def load_train_window_from_split_report(
    split_report_path: Path,
    split_index: int,
) -> tuple[str, str]:
    """Load train window boundaries from an existing walk-forward split report."""
    report = json.loads(split_report_path.read_text(encoding="utf-8"))
    splits = report["splits"]

    if split_index < 0 or split_index >= len(splits):
        raise IndexError(f"split_index out of range: {split_index}")

    split = splits[split_index]
    train_start = get_split_value(split, ["train_start", "train_start_date"])
    train_end = get_split_value(split, ["train_end", "train_end_date"])

    return train_start, train_end


def load_universe_price_matrix(
    prices_path: Path,
    universe_config_path: Path,
    price_column: str = "adjusted_close",
) -> pd.DataFrame:
    """Load validated ETF price matrix for the configured universe."""
    prices = pd.read_parquet(prices_path)
    prices = validate_price_frame(prices)

    universe_config = load_universe_config(universe_config_path)
    universe_tickers = universe_config.universe.tickers

    price_matrix = build_price_matrix(
        prices=prices,
        price_column=price_column,
    )

    missing_tickers = sorted(set(universe_tickers).difference(price_matrix.columns))
    if missing_tickers:
        raise ValueError(f"Missing configured universe tickers in prices: {missing_tickers}")

    return price_matrix[universe_tickers]


def candidate_id(index: int) -> str:
    """Return stable candidate identifier."""
    return f"candidate_{index:03d}"


def find_leader(
    candidates: list[dict[str, Any]],
    metric_path: tuple[str, str],
    maximize: bool,
) -> dict[str, Any] | None:
    """Find best valid candidate by a nested numeric metric."""
    valid_candidates = [candidate for candidate in candidates if candidate["valid"]]
    scored_candidates = []

    section, metric = metric_path
    for candidate in valid_candidates:
        value = candidate[section].get(metric)
        if value is not None:
            scored_candidates.append((float(value), candidate))

    if not scored_candidates:
        return None

    best_value, best_candidate = sorted(
        scored_candidates,
        key=lambda item: item[0],
        reverse=maximize,
    )[0]

    return {
        "candidate_id": best_candidate["candidate_id"],
        "strategy_name": best_candidate["strategy_name"],
        "value": best_value,
    }


def build_leaders(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    """Build leader summary for smoke evaluation."""
    return {
        "highest_train_sharpe": find_leader(
            candidates=candidates,
            metric_path=("metrics", "sharpe"),
            maximize=True,
        ),
        "highest_train_cagr": find_leader(
            candidates=candidates,
            metric_path=("metrics", "cagr"),
            maximize=True,
        ),
        "least_severe_train_max_drawdown": find_leader(
            candidates=candidates,
            metric_path=("metrics", "max_drawdown"),
            maximize=True,
        ),
        "lowest_average_turnover": find_leader(
            candidates=candidates,
            metric_path=("turnover_summary", "average_turnover"),
            maximize=False,
        ),
    }


def build_grid_smoke_report(
    price_matrix: pd.DataFrame,
    train_start: str,
    train_end: str,
    parameter_grid: list[FactorRotationParameters],
    transaction_cost_bps: float = 10.0,
    risk_free_rate: float = 0.0,
    min_return_observations: int = 1000,
    penalty_value: float = 1_000_000.0,
) -> dict[str, Any]:
    """Evaluate deterministic parameter grid on one train window."""
    strategy_names = [parameters.strategy_name() for parameters in parameter_grid]
    if len(strategy_names) != len(set(strategy_names)):
        raise ValueError("Parameter grid contains duplicate strategy names.")

    candidates: list[dict[str, Any]] = []

    for index, parameters in enumerate(parameter_grid):
        evaluation = evaluate_factor_rotation_parameters_on_window(
            price_matrix=price_matrix,
            parameters=parameters,
            train_start=train_start,
            train_end=train_end,
            transaction_cost_bps=transaction_cost_bps,
            risk_free_rate=risk_free_rate,
            min_return_observations=min_return_observations,
            penalty_value=penalty_value,
        )
        payload = evaluation.to_dict()
        payload["candidate_id"] = candidate_id(index)
        candidates.append(payload)

    valid_count = sum(1 for candidate in candidates if candidate["valid"])
    invalid_count = len(candidates) - valid_count

    return {
        "evaluation_type": "factor_rotation_grid_smoke_train_only",
        "protocol": (
            "Deterministic smoke grid evaluated only on the selected train window. "
            "This is not optimizer search and not out-of-sample evidence."
        ),
        "train_start": train_start,
        "train_end": train_end,
        "transaction_cost_bps": transaction_cost_bps,
        "risk_free_rate": risk_free_rate,
        "min_return_observations": min_return_observations,
        "penalty_value": penalty_value,
        "candidate_count": len(candidates),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "ranking_note": (
            "Higher Sharpe/CAGR are better; less severe max drawdown is closer to zero; "
            "lower turnover is better."
        ),
        "leaders": build_leaders(candidates),
        "candidates": candidates,
    }


def build_grid_smoke_summary(report: dict[str, Any]) -> str:
    """Build Markdown summary for deterministic grid smoke evaluation."""
    lines = [
        "# Factor Rotation Grid Smoke Evaluation",
        "",
        "## Protocol",
        "",
        "- Evaluation type: `factor_rotation_grid_smoke_train_only`.",
        "- This is a deterministic smoke grid, not evolutionary optimization.",
        "- Results are train-window only and must not be reported as OOS performance.",
        f"- Train window: `{report['train_start']}` to `{report['train_end']}`.",
        f"- Transaction cost: `{report['transaction_cost_bps']}` bps.",
        f"- Candidate count: `{report['candidate_count']}`.",
        f"- Valid candidates: `{report['valid_count']}`.",
        f"- Invalid candidates: `{report['invalid_count']}`.",
        "",
        "## Leaders",
        "",
    ]

    for label, leader in report["leaders"].items():
        if leader is None:
            lines.append(f"- {label}: n/a")
        else:
            lines.append(
                f"- {label}: `{leader['candidate_id']}` "
                f"(`{leader['strategy_name']}`), value `{leader['value']:.6f}`"
            )

    lines.extend(
        [
            "",
            "## Candidate Metrics",
            "",
            (
                "| Candidate | Valid | CAGR | Sharpe | Max Drawdown | "
                "Avg Turnover | Top-K | Windows | Factor Weights |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )

    sorted_candidates = sorted(
        report["candidates"],
        key=lambda candidate: (
            not candidate["valid"],
            (
                -float(candidate["metrics"]["sharpe"])
                if candidate["metrics"].get("sharpe") is not None
                else float("inf")
            ),
        ),
    )

    for candidate in sorted_candidates:
        parameters = candidate["parameters"]
        metrics = candidate["metrics"]
        turnover = candidate["turnover_summary"]

        lines.append(
            "| "
            f"`{candidate['candidate_id']}` | "
            f"{candidate['valid']} | "
            f"{format_percent(metrics.get('cagr'))} | "
            f"{format_float(metrics.get('sharpe'))} | "
            f"{format_percent(metrics.get('max_drawdown'))} | "
            f"{format_float(turnover.get('average_turnover'))} | "
            f"{parameters['top_k']} | "
            f"m={parameters['momentum_window']}, "
            f"v={parameters['volatility_window']}, "
            f"d={parameters['drawdown_window']} | "
            f"mw={parameters['momentum_weight']}, "
            f"vw={parameters['volatility_weight']}, "
            f"dw={parameters['drawdown_weight']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "This report only verifies that the objective function behaves sensibly on real data. "
            "It must not be used to claim outperformance. Final conclusions require "
            "walk-forward optimizer selection and out-of-sample evaluation against baselines.",
            "",
        ]
    )

    return "\n".join(lines)


def run_grid_smoke(
    prices_path: Path,
    universe_config_path: Path,
    split_report_path: Path,
    split_index: int,
    output_path: Path,
    summary_output_path: Path,
    transaction_cost_bps: float,
    risk_free_rate: float,
    min_return_observations: int,
) -> dict[str, Any]:
    """Run deterministic factor-rotation grid smoke evaluation."""
    train_start, train_end = load_train_window_from_split_report(
        split_report_path=split_report_path,
        split_index=split_index,
    )
    price_matrix = load_universe_price_matrix(
        prices_path=prices_path,
        universe_config_path=universe_config_path,
    )

    report = build_grid_smoke_report(
        price_matrix=price_matrix,
        train_start=train_start,
        train_end=train_end,
        parameter_grid=build_smoke_parameter_grid(),
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        min_return_observations=min_return_observations,
    )
    report["split_index"] = split_index

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_output_path.write_text(build_grid_smoke_summary(report), encoding="utf-8")

    print(f"Saved factor rotation grid smoke report to: {output_path}")
    print(f"Saved factor rotation grid smoke summary to: {summary_output_path}")
    print(f"Train window: {train_start} -> {train_end}")
    print(f"Candidate count: {report['candidate_count']}")
    print(f"Valid candidates: {report['valid_count']}")
    print(f"Invalid candidates: {report['invalid_count']}")
    print(f"Leaders: {report['leaders']}")

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate factor-rotation smoke grid.")
    parser.add_argument(
        "--prices",
        type=Path,
        default=Path("data/raw/prices_ohlcv.parquet"),
        help="Validated OHLCV parquet file.",
    )
    parser.add_argument(
        "--universe-config",
        type=Path,
        default=Path("configs/universe_etf.yaml"),
        help="Universe config path.",
    )
    parser.add_argument(
        "--split-report",
        type=Path,
        default=Path("reports/walk_forward_splits.json"),
        help="Walk-forward split report path.",
    )
    parser.add_argument(
        "--split-index",
        type=int,
        default=0,
        help="Walk-forward split index used for train-only smoke evaluation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/factor_rotation_grid_smoke.json"),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("reports/factor_rotation_grid_smoke_summary.md"),
        help="Output Markdown summary path.",
    )
    parser.add_argument(
        "--transaction-cost-bps",
        type=float,
        default=10.0,
        help="Transaction cost in basis points.",
    )
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.0,
        help="Annual risk-free rate.",
    )
    parser.add_argument(
        "--min-return-observations",
        type=int,
        default=1000,
        help="Minimum net return observations for valid train evaluation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_grid_smoke(
        prices_path=args.prices,
        universe_config_path=args.universe_config,
        split_report_path=args.split_report,
        split_index=args.split_index,
        output_path=args.output,
        summary_output_path=args.summary_output,
        transaction_cost_bps=args.transaction_cost_bps,
        risk_free_rate=args.risk_free_rate,
        min_return_observations=args.min_return_observations,
    )


if __name__ == "__main__":
    main()
