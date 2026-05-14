import json

import pandas as pd
import pytest
from scripts.run_one_split_optimizer_selection import (
    align_return_series_to_common_index,
    build_one_split_selection_report,
    build_one_split_selection_summary,
    calculate_selected_degradation,
    find_test_metric_leaders,
    load_train_test_window_from_split_report,
    select_evaluation_by_metric,
)


def test_select_evaluation_by_metric_ignores_invalid_candidates() -> None:
    evaluations = [
        {
            "candidate_id": "bad",
            "valid": False,
            "metrics": {"sharpe": 99.0},
        },
        {
            "candidate_id": "good",
            "valid": True,
            "metrics": {"sharpe": 1.2},
        },
    ]

    selected = select_evaluation_by_metric(
        evaluations=evaluations,
        metric_name="sharpe",
        maximize=True,
    )

    assert selected["candidate_id"] == "good"


def test_select_evaluation_by_metric_raises_without_valid_candidates() -> None:
    with pytest.raises(ValueError, match="No valid evaluations"):
        select_evaluation_by_metric(
            evaluations=[{"candidate_id": "bad", "valid": False, "metrics": {}}],
            metric_name="sharpe",
        )


def test_align_return_series_to_common_index_uses_exact_intersection() -> None:
    dates = pd.bdate_range("2020-01-01", periods=5)
    first = pd.Series([0.01, 0.02, 0.03], index=dates[:3])
    second = pd.Series([0.04, 0.05, 0.06], index=dates[2:5])

    aligned, common_index = align_return_series_to_common_index({"first": first, "second": second})

    assert list(common_index) == [dates[2]]
    assert aligned["first"].iloc[0] == pytest.approx(0.03)
    assert aligned["second"].iloc[0] == pytest.approx(0.04)


def test_find_test_metric_leaders_returns_expected_strategy() -> None:
    metrics = {
        "optimizer": {"cagr": 0.1, "sharpe": 0.8, "max_drawdown": -0.1},
        "spy": {"cagr": 0.2, "sharpe": 0.7, "max_drawdown": -0.2},
    }

    leaders = find_test_metric_leaders(metrics)

    assert leaders["highest_test_cagr"]["strategy_name"] == "spy"
    assert leaders["highest_test_sharpe"]["strategy_name"] == "optimizer"
    assert leaders["least_severe_test_max_drawdown"]["strategy_name"] == "optimizer"


def test_calculate_selected_degradation_uses_test_minus_train() -> None:
    degradation = calculate_selected_degradation(
        train_metrics={"cagr": 0.2, "sharpe": 1.0, "max_drawdown": -0.1},
        test_metrics={"cagr": 0.1, "sharpe": 0.5, "max_drawdown": -0.2},
    )

    assert degradation["cagr_test_minus_train"] == pytest.approx(-0.1)
    assert degradation["sharpe_test_minus_train"] == pytest.approx(-0.5)
    assert degradation["max_drawdown_test_minus_train"] == pytest.approx(-0.1)


def test_load_train_test_window_from_split_report(tmp_path) -> None:
    split_report = {
        "splits": [
            {
                "train_start": "2020-01-01",
                "train_end": "2020-12-31",
                "test_start": "2021-01-01",
                "test_end": "2021-12-31",
            }
        ]
    }
    path = tmp_path / "splits.json"
    path.write_text(json.dumps(split_report), encoding="utf-8")

    split_window = load_train_test_window_from_split_report(
        split_report_path=path,
        split_index=0,
    )

    assert split_window["train_start"] == "2020-01-01"
    assert split_window["test_end"] == "2021-12-31"


def test_build_one_split_selection_summary_mentions_no_final_claim() -> None:
    optimizer_result = {
        "objective_names": ["negative_sharpe"],
        "population_size": 4,
        "generations": 1,
        "seed": 42,
        "evaluation_count": 4,
        "valid_evaluation_count": 4,
        "invalid_evaluation_count": 0,
        "pareto_candidate_count": 1,
        "pareto_front": [],
    }
    selected_train = {
        "candidate_id": "evaluation_0001",
        "strategy_name": "factor_rotation_test",
        "valid": True,
        "parameters": {},
        "metrics": {
            "cagr": 0.2,
            "sharpe": 1.0,
            "max_drawdown": -0.1,
            "calmar": 2.0,
        },
        "turnover_summary": {},
    }
    selected_test = {
        "valid": True,
        "invalid_reason": None,
        "strategy_name": "factor_rotation_test_selected_oos",
        "parameters": {},
        "metrics": {
            "cagr": 0.1,
            "sharpe": 0.5,
            "max_drawdown": -0.2,
            "calmar": 0.5,
        },
        "turnover_summary": {},
        "return_observation_count": 120,
    }
    test_common_metrics = {
        "optimizer_selected_net": {
            "cagr": 0.1,
            "sharpe": 0.5,
            "max_drawdown": -0.2,
            "calmar": 0.5,
            "final_equity": 1.1,
        },
        "buy_hold_SPY": {
            "cagr": 0.2,
            "sharpe": 0.7,
            "max_drawdown": -0.15,
            "calmar": 1.3,
            "final_equity": 1.2,
        },
    }

    report = build_one_split_selection_report(
        split_index=0,
        train_start="2020-01-01",
        train_end="2020-12-31",
        test_start="2021-01-01",
        test_end="2021-12-31",
        optimizer_result=optimizer_result,
        selected_train_evaluation=selected_train,
        selected_test_evaluation=selected_test,
        test_common_metrics=test_common_metrics,
        test_common_start="2021-02-01",
        test_common_end="2021-12-31",
        test_common_observation_count=200,
        transaction_cost_bps=10.0,
        risk_free_rate=0.0,
        selection_metric="sharpe",
    )
    summary = build_one_split_selection_summary(report)

    assert "Test data is not used for candidate selection" in summary
    assert "not final walk-forward evidence" in summary
    assert "optimizer_selected_net" in summary
    assert report["selection_rule"]["test_data_used_for_selection"] is False
