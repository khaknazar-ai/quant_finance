import numpy as np
import pandas as pd
import pytest
from scripts.run_nsga2_train_smoke import (
    build_nsga2_train_smoke_report,
    build_nsga2_train_smoke_summary,
)
from src.optimization.nsga2_optimizer import (
    FactorRotationNSGA2Problem,
    NSGA2SearchSpace,
    build_pareto_front_records,
    objective_array_to_dict,
    objective_dict_to_array,
)


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


def test_search_space_decode_vector_returns_factor_rotation_parameters() -> None:
    search_space = NSGA2SearchSpace(top_k_max=4)
    vector = np.array([1.2, 0.2, 2.0, 1.0, 0.5, 0.25, 3.4, 0.45])

    parameters = search_space.decode_vector(vector)

    assert parameters.momentum_window == 126
    assert parameters.volatility_window == 21
    assert parameters.drawdown_window == 252
    assert parameters.momentum_weight == pytest.approx(1.0)
    assert parameters.volatility_weight == pytest.approx(0.5)
    assert parameters.drawdown_weight == pytest.approx(0.25)
    assert parameters.top_k == 3
    assert parameters.max_asset_weight == pytest.approx(0.45)


def test_search_space_rejects_invalid_top_k_bounds() -> None:
    with pytest.raises(ValueError, match="top_k_max"):
        NSGA2SearchSpace(top_k_min=5, top_k_max=4)


def test_objective_array_round_trip_uses_fixed_order() -> None:
    objectives = {
        "negative_sharpe": -1.0,
        "negative_cagr": -0.1,
        "max_drawdown_abs": 0.2,
        "average_turnover": 0.05,
    }

    objective_array = objective_dict_to_array(objectives)
    rebuilt = objective_array_to_dict(objective_array)

    assert rebuilt == objectives


def test_problem_evaluate_records_candidate() -> None:
    price_matrix = make_price_matrix()
    search_space = NSGA2SearchSpace(top_k_max=3)
    problem = FactorRotationNSGA2Problem(
        price_matrix=price_matrix,
        train_start=price_matrix.index[0],
        train_end=price_matrix.index[-1],
        search_space=search_space,
        min_return_observations=100,
    )
    vector = np.array([1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 2.0, 0.5])
    out = {}

    problem._evaluate(vector, out)

    assert out["F"].shape == (4,)
    assert len(problem.evaluations) == 1
    assert problem.evaluations[0]["valid"] is True
    assert problem.evaluations[0]["candidate_id"] == "evaluation_0000"


def test_build_pareto_front_records_handles_result_arrays() -> None:
    search_space = NSGA2SearchSpace(top_k_max=3)
    result_x = np.array([[1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 2.0, 0.5]])
    result_f = np.array([[-1.0, -0.1, 0.2, 0.05]])

    records = build_pareto_front_records(
        result_x=result_x,
        result_f=result_f,
        search_space=search_space,
    )

    assert len(records) == 1
    assert records[0]["pareto_id"] == "pareto_000"
    assert records[0]["objectives"]["negative_sharpe"] == pytest.approx(-1.0)


def test_nsga2_train_smoke_summary_mentions_no_oos_claims() -> None:
    optimizer_result = {
        "objective_names": [
            "negative_sharpe",
            "negative_cagr",
            "max_drawdown_abs",
            "average_turnover",
        ],
        "population_size": 4,
        "generations": 1,
        "seed": 42,
        "search_space": NSGA2SearchSpace(top_k_max=3).to_dict(),
        "evaluation_count": 1,
        "valid_evaluation_count": 1,
        "invalid_evaluation_count": 0,
        "pareto_candidate_count": 1,
        "pareto_front": [
            {
                "pareto_id": "pareto_000",
                "strategy_name": "factor_rotation_test",
                "objectives": {
                    "negative_sharpe": -1.0,
                    "negative_cagr": -0.1,
                    "max_drawdown_abs": 0.2,
                    "average_turnover": 0.05,
                },
            }
        ],
        "all_evaluations": [
            {
                "candidate_id": "evaluation_0000",
                "strategy_name": "factor_rotation_test",
                "valid": True,
                "metrics": {
                    "cagr": 0.1,
                    "sharpe": 1.0,
                    "max_drawdown": -0.2,
                },
                "turnover_summary": {
                    "average_turnover": 0.05,
                },
            }
        ],
    }

    report = build_nsga2_train_smoke_report(
        train_start="2020-01-01",
        train_end="2020-12-31",
        optimizer_result=optimizer_result,
        transaction_cost_bps=10.0,
        risk_free_rate=0.0,
        min_return_observations=100,
    )
    summary = build_nsga2_train_smoke_summary(report)

    assert "not OOS evidence" in summary
    assert "must not be used to claim strategy outperformance" in summary
    assert report["pareto_candidate_count"] == 1
