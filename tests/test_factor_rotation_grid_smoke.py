import json

import pandas as pd
from scripts.evaluate_factor_rotation_grid_smoke import (
    build_grid_smoke_report,
    build_grid_smoke_summary,
    build_smoke_parameter_grid,
    find_leader,
    load_train_window_from_split_report,
)
from src.strategies.factor_rotation import FactorRotationParameters


def make_price_matrix() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=420)
    return pd.DataFrame(
        {
            "SPY": [100.0 * (1.0004**index) for index in range(len(dates))],
            "QQQ": [100.0 * (1.0007**index) for index in range(len(dates))],
            "IEF": [100.0 * (1.0001**index) for index in range(len(dates))],
            "GLD": [100.0 * (1.0003**index) for index in range(len(dates))],
        },
        index=dates,
    )


def test_smoke_parameter_grid_has_unique_strategy_names() -> None:
    parameter_grid = build_smoke_parameter_grid()
    strategy_names = [parameters.strategy_name() for parameters in parameter_grid]

    assert len(parameter_grid) == 8
    assert len(strategy_names) == len(set(strategy_names))


def test_build_grid_smoke_report_counts_candidates() -> None:
    price_matrix = make_price_matrix()
    parameter_grid = [
        FactorRotationParameters(
            momentum_window=21,
            volatility_window=21,
            drawdown_window=21,
            momentum_weight=1.0,
            volatility_weight=0.0,
            drawdown_weight=0.0,
            top_k=2,
            max_asset_weight=0.5,
            rebalance_frequency="ME",
        ),
        FactorRotationParameters(
            momentum_window=42,
            volatility_window=21,
            drawdown_window=42,
            momentum_weight=1.0,
            volatility_weight=0.5,
            drawdown_weight=0.5,
            top_k=2,
            max_asset_weight=0.5,
            rebalance_frequency="ME",
        ),
    ]

    report = build_grid_smoke_report(
        price_matrix=price_matrix,
        train_start=str(price_matrix.index[0].date()),
        train_end=str(price_matrix.index[-1].date()),
        parameter_grid=parameter_grid,
        min_return_observations=100,
    )

    assert report["candidate_count"] == 2
    assert report["valid_count"] == 2
    assert report["invalid_count"] == 0
    assert report["leaders"]["highest_train_sharpe"] is not None


def test_build_grid_smoke_summary_mentions_train_only_protocol() -> None:
    price_matrix = make_price_matrix()
    report = build_grid_smoke_report(
        price_matrix=price_matrix,
        train_start=str(price_matrix.index[0].date()),
        train_end=str(price_matrix.index[-1].date()),
        parameter_grid=[
            FactorRotationParameters(
                momentum_window=21,
                volatility_window=21,
                drawdown_window=21,
                top_k=2,
                max_asset_weight=0.5,
            )
        ],
        min_return_observations=100,
    )

    summary = build_grid_smoke_summary(report)

    assert "train-window only" in summary
    assert "not evolutionary optimization" in summary
    assert "must not be used to claim outperformance" in summary


def test_find_leader_ignores_invalid_candidates() -> None:
    candidates = [
        {
            "candidate_id": "candidate_000",
            "strategy_name": "bad",
            "valid": False,
            "metrics": {"sharpe": 999.0},
            "turnover_summary": {"average_turnover": 999.0},
        },
        {
            "candidate_id": "candidate_001",
            "strategy_name": "good",
            "valid": True,
            "metrics": {"sharpe": 1.0},
            "turnover_summary": {"average_turnover": 0.1},
        },
    ]

    leader = find_leader(
        candidates=candidates,
        metric_path=("metrics", "sharpe"),
        maximize=True,
    )

    assert leader is not None
    assert leader["candidate_id"] == "candidate_001"


def test_load_train_window_from_split_report_supports_current_keys(tmp_path) -> None:
    split_report = {
        "splits": [
            {
                "train_start": "2020-01-01",
                "train_end": "2020-12-31",
            }
        ]
    }
    split_path = tmp_path / "walk_forward_splits.json"
    split_path.write_text(json.dumps(split_report), encoding="utf-8")

    train_start, train_end = load_train_window_from_split_report(
        split_report_path=split_path,
        split_index=0,
    )

    assert train_start == "2020-01-01"
    assert train_end == "2020-12-31"
