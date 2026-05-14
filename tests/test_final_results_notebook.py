from scripts.build_final_results_notebook import build_notebook, format_float, format_percent


def make_walk_forward_report() -> dict:
    return {
        "evaluated_split_count": 9,
        "aggregate_test_metrics": {
            "buy_hold_SPY": {
                "mean_cagr": 0.15,
                "mean_sharpe": 1.2,
                "mean_max_drawdown": -0.14,
            },
            "optimizer_selected_net": {
                "mean_cagr": 0.06,
                "mean_sharpe": 0.86,
                "mean_max_drawdown": -0.08,
            },
        },
        "split_metric_winner_counts": {
            "highest_test_cagr": {"buy_hold_SPY": 4, "optimizer_selected_net": 1}
        },
        "split_reports": [
            {
                "split_index": 0,
                "test_start": "2017-01-01",
                "test_end": "2017-12-31",
                "selected_train_evaluation": {"candidate_id": "evaluation_0001"},
                "selected_test_evaluation": {
                    "metrics": {
                        "cagr": 0.1,
                        "sharpe": 1.0,
                        "max_drawdown": -0.05,
                    }
                },
            }
        ],
    }


def make_stitched_report() -> dict:
    return {
        "stitched_start": "2017-02-01",
        "stitched_end": "2025-12-31",
        "stitched_metrics": {
            "buy_hold_SPY": {
                "final_equity": 2.92,
                "cagr": 0.1387,
                "sharpe": 0.785,
                "max_drawdown": -0.3372,
                "calmar": 0.411,
                "observation_count": 2079,
            },
            "momentum_top_5_252d_gross": {
                "final_equity": 2.52,
                "cagr": 0.1187,
                "sharpe": 0.825,
                "max_drawdown": -0.2254,
                "calmar": 0.526,
                "observation_count": 2079,
            },
            "optimizer_selected_net": {
                "final_equity": 1.63,
                "cagr": 0.0613,
                "sharpe": 0.642,
                "max_drawdown": -0.1852,
                "calmar": 0.331,
                "observation_count": 2079,
            },
        },
        "optimizer_vs_spy_deltas": {
            "cagr_optimizer_minus_spy": -0.0774,
            "sharpe_optimizer_minus_spy": -0.143,
            "max_drawdown_optimizer_minus_spy": 0.152,
            "calmar_optimizer_minus_spy": -0.080,
            "final_equity_optimizer_minus_spy": -1.286,
        },
    }


def notebook_text(notebook: dict) -> str:
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


def test_format_helpers_are_human_readable() -> None:
    assert format_percent(0.1234) == "12.34%"
    assert format_float(1.23456) == "1.235"


def test_notebook_contains_visible_negative_result_and_tradeoff() -> None:
    notebook = build_notebook(
        walk_forward_report=make_walk_forward_report(),
        stitched_report=make_stitched_report(),
    )
    text = notebook_text(notebook)

    assert len(notebook["cells"]) >= 12
    assert "did not outperform SPY" in text
    assert "risk-control trade-off" in text
    assert "No bad results are removed" in text
    assert "SPY buy-and-hold" in text
    assert "Optimizer selected net" in text
    assert "## CV Bullets" not in text
    assert "CV Bullets" not in text


def test_notebook_contains_reproducible_artifact_paths() -> None:
    notebook = build_notebook(
        walk_forward_report=make_walk_forward_report(),
        stitched_report=make_stitched_report(),
    )
    text = notebook_text(notebook)

    assert "reports/walk_forward_optimizer_selection.json" in text
    assert "reports/walk_forward_optimizer_stitched_oos_equity_summary.json" in text
    assert "reports/walk_forward_optimizer_stitched_oos_equity.parquet" in text


def test_notebook_metadata_is_valid_nbformat() -> None:
    notebook = build_notebook(
        walk_forward_report=make_walk_forward_report(),
        stitched_report=make_stitched_report(),
    )

    assert notebook["nbformat"] == 4
    assert notebook["nbformat_minor"] == 5
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
