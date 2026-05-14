import pandas as pd
import pytest
from scripts.run_walk_forward_optimizer_selection import (
    aggregate_metrics_by_strategy,
    aggregate_selected_degradation,
    build_walk_forward_optimizer_report,
    build_walk_forward_optimizer_summary,
    count_split_metric_winners,
)


def make_split_report(
    split_index: int,
    optimizer_cagr: float,
    spy_cagr: float,
    optimizer_sharpe: float,
    spy_sharpe: float,
) -> dict:
    return {
        "split_index": split_index,
        "train_start": "2020-01-01",
        "train_end": "2020-12-31",
        "test_start": "2021-01-01",
        "test_end": "2021-12-31",
        "selected_train_evaluation": {
            "candidate_id": f"evaluation_{split_index:04d}",
            "strategy_name": "factor_rotation_test",
            "metrics": {
                "cagr": 0.2,
                "sharpe": 1.0,
                "max_drawdown": -0.1,
                "calmar": 2.0,
            },
        },
        "selected_test_evaluation": {
            "valid": True,
            "metrics": {
                "cagr": optimizer_cagr,
                "sharpe": optimizer_sharpe,
                "max_drawdown": -0.1,
                "calmar": 1.0,
            },
        },
        "selected_metric_degradation": {
            "cagr_test_minus_train": optimizer_cagr - 0.2,
            "sharpe_test_minus_train": optimizer_sharpe - 1.0,
        },
        "test_common_window": {
            "start": "2021-02-01",
            "end": "2021-12-31",
            "observation_count": 200,
        },
        "test_common_metrics": {
            "optimizer_selected_net": {
                "cagr": optimizer_cagr,
                "sharpe": optimizer_sharpe,
                "max_drawdown": -0.1,
                "calmar": 1.0,
                "final_equity": 1.1,
            },
            "buy_hold_SPY": {
                "cagr": spy_cagr,
                "sharpe": spy_sharpe,
                "max_drawdown": -0.2,
                "calmar": 0.8,
                "final_equity": 1.2,
            },
        },
        "test_common_metric_leaders": {
            "highest_test_cagr": {
                "strategy_name": (
                    "optimizer_selected_net" if optimizer_cagr > spy_cagr else "buy_hold_SPY"
                ),
                "metric": "cagr",
                "value": max(optimizer_cagr, spy_cagr),
            },
            "highest_test_sharpe": {
                "strategy_name": (
                    "optimizer_selected_net" if optimizer_sharpe > spy_sharpe else "buy_hold_SPY"
                ),
                "metric": "sharpe",
                "value": max(optimizer_sharpe, spy_sharpe),
            },
        },
    }


def test_aggregate_metrics_by_strategy_calculates_mean_and_positive_fraction() -> None:
    split_reports = [
        make_split_report(
            0, optimizer_cagr=0.1, spy_cagr=0.2, optimizer_sharpe=1.0, spy_sharpe=0.8
        ),
        make_split_report(
            1, optimizer_cagr=-0.1, spy_cagr=0.1, optimizer_sharpe=0.2, spy_sharpe=0.4
        ),
    ]

    aggregate = aggregate_metrics_by_strategy(split_reports)

    assert aggregate["optimizer_selected_net"]["mean_cagr"] == pytest.approx(0.0)
    assert aggregate["optimizer_selected_net"]["positive_cagr_fraction"] == pytest.approx(0.5)
    assert aggregate["buy_hold_SPY"]["mean_cagr"] == pytest.approx(0.15)


def test_count_split_metric_winners_counts_by_leader_label() -> None:
    split_reports = [
        make_split_report(
            0, optimizer_cagr=0.3, spy_cagr=0.2, optimizer_sharpe=1.0, spy_sharpe=0.8
        ),
        make_split_report(
            1, optimizer_cagr=0.1, spy_cagr=0.2, optimizer_sharpe=0.2, spy_sharpe=0.4
        ),
    ]

    counts = count_split_metric_winners(split_reports)

    assert counts["highest_test_cagr"]["optimizer_selected_net"] == 1
    assert counts["highest_test_cagr"]["buy_hold_SPY"] == 1
    assert counts["highest_test_sharpe"]["optimizer_selected_net"] == 1


def test_aggregate_selected_degradation_returns_mean_delta() -> None:
    split_reports = [
        make_split_report(
            0, optimizer_cagr=0.1, spy_cagr=0.2, optimizer_sharpe=0.8, spy_sharpe=0.7
        ),
        make_split_report(
            1, optimizer_cagr=0.0, spy_cagr=0.1, optimizer_sharpe=0.4, spy_sharpe=0.6
        ),
    ]

    degradation = aggregate_selected_degradation(split_reports)

    assert degradation["mean_cagr_test_minus_train"] == pytest.approx(-0.15)
    assert degradation["mean_sharpe_test_minus_train"] == pytest.approx(-0.4)


def test_build_walk_forward_optimizer_summary_mentions_no_broad_outperformance() -> None:
    split_reports = [
        make_split_report(0, optimizer_cagr=0.1, spy_cagr=0.2, optimizer_sharpe=1.0, spy_sharpe=0.8)
    ]
    report = build_walk_forward_optimizer_report(
        split_reports=split_reports,
        selection_metric="sharpe",
        transaction_cost_bps=10.0,
        risk_free_rate=0.0,
        population_size=4,
        generations=1,
        base_seed=42,
        momentum_lookback_days=252,
        momentum_top_k=5,
        momentum_rebalance_frequency="ME",
    )

    summary = build_walk_forward_optimizer_summary(report)

    assert "Test data is not used for candidate selection" in summary
    assert "risk-control trade-off" in summary
    assert report["selection_rule"]["test_data_used_for_selection"] is False


def test_metric_aggregation_handles_missing_strategy_metric() -> None:
    split_reports = [
        make_split_report(0, optimizer_cagr=0.1, spy_cagr=0.2, optimizer_sharpe=1.0, spy_sharpe=0.8)
    ]
    split_reports[0]["test_common_metrics"]["buy_hold_SPY"]["calmar"] = None

    aggregate = aggregate_metrics_by_strategy(split_reports)

    assert aggregate["buy_hold_SPY"]["mean_calmar"] is None


def test_pandas_is_available_for_test_data_generation() -> None:
    dates = pd.bdate_range("2020-01-01", periods=3)

    assert len(dates) == 3
