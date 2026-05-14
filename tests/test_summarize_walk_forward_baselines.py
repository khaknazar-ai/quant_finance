import json

from scripts.summarize_walk_forward_baselines import (
    build_walk_forward_summary,
    find_best_aggregate_strategy,
    find_split_cagr_leader,
    get_aggregate_stat,
    run_summary,
)


def make_report() -> dict:
    return {
        "evaluation_type": "walk_forward_baseline_oos",
        "benchmark_ticker": "SPY",
        "universe_tickers": ["SPY", "QQQ"],
        "price_column": "adjusted_close",
        "risk_free_rate": 0.0,
        "return_alignment": "exact_common_date_intersection_per_split",
        "evaluated_split_count": 2,
        "strategy_count": 2,
        "strategies": ["buy_hold_SPY", "momentum_net"],
        "momentum_lookback_days": 252,
        "momentum_top_k": 5,
        "momentum_rebalance_frequency": "ME",
        "transaction_cost_bps": 10.0,
        "cost_model": "net_return = gross_return - turnover * bps / 10000",
        "turnover_convention": "sum_abs_weight_change",
        "splits": [
            {
                "split_id": 0,
                "test_start": "2020-01-01",
                "test_end": "2020-12-31",
                "metrics": {
                    "buy_hold_SPY": {"cagr": 0.10},
                    "momentum_net": {"cagr": 0.08},
                },
            },
            {
                "split_id": 1,
                "test_start": "2021-01-01",
                "test_end": "2021-12-31",
                "metrics": {
                    "buy_hold_SPY": {"cagr": -0.05},
                    "momentum_net": {"cagr": 0.03},
                },
            },
        ],
        "aggregate_metrics": {
            "buy_hold_SPY": {
                "split_count": 2,
                "positive_cagr_split_fraction": 0.5,
                "best_cagr_split_id": 0,
                "worst_cagr_split_id": 1,
                "metrics": {
                    "cagr": {"mean": 0.025, "std": 0.075, "min": -0.05, "max": 0.10},
                    "sharpe": {"mean": 0.80, "std": 0.10, "min": 0.70, "max": 0.90},
                    "max_drawdown": {
                        "mean": -0.20,
                        "std": 0.05,
                        "min": -0.25,
                        "max": -0.15,
                    },
                    "calmar": {"mean": 0.20, "std": 0.10, "min": 0.10, "max": 0.30},
                },
            },
            "momentum_net": {
                "split_count": 2,
                "positive_cagr_split_fraction": 1.0,
                "best_cagr_split_id": 0,
                "worst_cagr_split_id": 1,
                "metrics": {
                    "cagr": {"mean": 0.055, "std": 0.025, "min": 0.03, "max": 0.08},
                    "sharpe": {"mean": 0.70, "std": 0.10, "min": 0.60, "max": 0.80},
                    "max_drawdown": {
                        "mean": -0.12,
                        "std": 0.02,
                        "min": -0.14,
                        "max": -0.10,
                    },
                    "calmar": {"mean": 0.45, "std": 0.10, "min": 0.35, "max": 0.55},
                },
            },
        },
    }


def test_get_aggregate_stat() -> None:
    report = make_report()

    assert get_aggregate_stat(report, "momentum_net", "cagr") == 0.055
    assert get_aggregate_stat(report, "missing", "cagr") is None


def test_find_best_aggregate_strategy() -> None:
    report = make_report()

    assert find_best_aggregate_strategy(report, "cagr") == "momentum_net"
    assert find_best_aggregate_strategy(report, "sharpe") == "buy_hold_SPY"
    assert find_best_aggregate_strategy(report, "max_drawdown") == "momentum_net"


def test_find_split_cagr_leader() -> None:
    report = make_report()

    assert find_split_cagr_leader(report["splits"][0]) == "buy_hold_SPY"
    assert find_split_cagr_leader(report["splits"][1]) == "momentum_net"


def test_build_walk_forward_summary_contains_protocol_and_tables() -> None:
    summary = build_walk_forward_summary(make_report())

    assert "# Walk-Forward Baseline Summary" in summary
    assert "walk_forward_baseline_oos" in summary
    assert "exact_common_date_intersection_per_split" in summary
    assert "| momentum_net | 5.50% | 0.700 | -12.00% | 0.450 | 100.00%" in summary
    assert "Highest mean CAGR: `momentum_net`" in summary
    assert "| 1 | 2021-01-01 -> 2021-12-31 | momentum_net |" in summary
    assert "It is not the same as CAGR from one stitched equity curve." in summary


def test_run_summary_writes_markdown_file(tmp_path) -> None:
    input_path = tmp_path / "walk_forward_baseline_metrics.json"
    output_path = tmp_path / "walk_forward_baseline_summary.md"

    input_path.write_text(json.dumps(make_report()), encoding="utf-8")

    run_summary(input_path=input_path, output_path=output_path)

    assert output_path.exists()
    assert "# Walk-Forward Baseline Summary" in output_path.read_text(encoding="utf-8")
