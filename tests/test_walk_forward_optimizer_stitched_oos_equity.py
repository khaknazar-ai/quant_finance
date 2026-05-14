import pandas as pd
import pytest
from scripts.build_walk_forward_optimizer_stitched_oos_equity import (
    build_optimizer_vs_spy_deltas,
    build_stitched_equity_frame,
    build_stitched_report,
    build_stitched_summary,
    calculate_stitched_metrics,
    find_stitched_metric_leaders,
    selected_parameters_from_split_report,
)


def test_selected_parameters_from_split_report_builds_factor_rotation_parameters() -> None:
    split_report = {
        "selected_train_evaluation": {
            "parameters": {
                "momentum_window": 126,
                "volatility_window": 63,
                "drawdown_window": 126,
                "momentum_weight": 1.0,
                "volatility_weight": 0.5,
                "drawdown_weight": 0.5,
                "top_k": 5,
                "max_asset_weight": 0.4,
                "rebalance_frequency": "ME",
            }
        }
    }

    parameters = selected_parameters_from_split_report(split_report)

    assert parameters.momentum_window == 126
    assert parameters.top_k == 5
    assert parameters.max_asset_weight == pytest.approx(0.4)


def test_build_stitched_equity_frame_compounds_by_strategy() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-01", "2020-01-02"]),
            "split_index": [0, 0, 0, 0],
            "strategy_name": ["a", "a", "b", "b"],
            "daily_return": [0.1, -0.1, 0.0, 0.2],
        }
    )

    equity = build_stitched_equity_frame(frame)

    final_a = equity[equity["strategy_name"] == "a"]["equity"].iloc[-1]
    final_b = equity[equity["strategy_name"] == "b"]["equity"].iloc[-1]

    assert final_a == pytest.approx(0.99)
    assert final_b == pytest.approx(1.2)


def test_calculate_stitched_metrics_returns_strategy_metrics() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.bdate_range("2020-01-01", periods=260),
            "split_index": [0] * 260,
            "strategy_name": ["a"] * 260,
            "daily_return": [0.001] * 260,
        }
    )
    equity = build_stitched_equity_frame(frame)

    metrics = calculate_stitched_metrics(equity_frame=equity, risk_free_rate=0.0)

    assert "a" in metrics
    assert metrics["a"]["observation_count"] == 260
    assert metrics["a"]["final_equity"] > 1.0


def test_find_stitched_metric_leaders_prefers_less_negative_drawdown() -> None:
    metrics = {
        "optimizer_selected_net": {
            "cagr": 0.05,
            "sharpe": 0.8,
            "max_drawdown": -0.05,
            "calmar": 1.0,
            "final_equity": 1.1,
        },
        "buy_hold_SPY": {
            "cagr": 0.1,
            "sharpe": 1.0,
            "max_drawdown": -0.2,
            "calmar": 0.5,
            "final_equity": 1.2,
        },
    }

    leaders = find_stitched_metric_leaders(metrics)

    assert leaders["highest_stitched_cagr"]["strategy_name"] == "buy_hold_SPY"
    assert (
        leaders["least_severe_stitched_max_drawdown"]["strategy_name"] == "optimizer_selected_net"
    )


def test_build_optimizer_vs_spy_deltas_uses_optimizer_minus_spy() -> None:
    metrics = {
        "optimizer_selected_net": {
            "cagr": 0.05,
            "sharpe": 0.8,
            "max_drawdown": -0.05,
            "calmar": 1.0,
            "final_equity": 1.1,
        },
        "buy_hold_SPY": {
            "cagr": 0.1,
            "sharpe": 1.0,
            "max_drawdown": -0.2,
            "calmar": 0.5,
            "final_equity": 1.2,
        },
    }

    deltas = build_optimizer_vs_spy_deltas(metrics)

    assert deltas["cagr_optimizer_minus_spy"] == pytest.approx(-0.05)
    assert deltas["max_drawdown_optimizer_minus_spy"] == pytest.approx(0.15)


def test_build_stitched_summary_mentions_risk_control_tradeoff() -> None:
    equity_frame = pd.DataFrame(
        {
            "date": pd.bdate_range("2020-01-01", periods=2),
            "split_index": [0, 0],
            "strategy_name": ["optimizer_selected_net", "buy_hold_SPY"],
            "daily_return": [0.01, 0.02],
            "equity": [1.01, 1.02],
        }
    )
    stitched_metrics = {
        "optimizer_selected_net": {
            "cagr": 0.05,
            "sharpe": 0.8,
            "max_drawdown": -0.05,
            "calmar": 1.0,
            "final_equity": 1.1,
            "observation_count": 100,
        },
        "buy_hold_SPY": {
            "cagr": 0.1,
            "sharpe": 1.0,
            "max_drawdown": -0.2,
            "calmar": 0.5,
            "final_equity": 1.2,
            "observation_count": 100,
        },
    }

    report = build_stitched_report(
        optimizer_report_path=(
            pd.Path("reports/walk_forward_optimizer_selection.json")
            if False
            else __import__("pathlib").Path("reports/walk_forward_optimizer_selection.json")
        ),
        equity_output_path=__import__("pathlib").Path(
            "reports/walk_forward_optimizer_stitched_oos_equity.parquet"
        ),
        equity_frame=equity_frame,
        split_windows=[
            {
                "split_index": 0,
                "test_start": "2020-01-01",
                "test_end": "2020-12-31",
                "common_start": "2020-02-01",
                "common_end": "2020-12-31",
                "common_observation_count": 100,
                "selected_candidate_id": "evaluation_0001",
            }
        ],
        stitched_metrics=stitched_metrics,
        transaction_cost_bps=10.0,
        risk_free_rate=0.0,
    )
    summary = build_stitched_summary(report)

    assert "No re-optimization is performed" in summary
    assert "risk-control trade-off" in summary
    assert "optimizer_selected_net" in summary
