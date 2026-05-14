import json

from scripts.summarize_walk_forward_oos_equity import (
    build_stitched_oos_equity_summary,
    get_strategy_metric,
    run_summary,
)


def make_summary() -> dict:
    return {
        "evaluation_type": "walk_forward_baseline_oos_stitched_equity",
        "benchmark_ticker": "SPY",
        "universe_tickers": ["SPY", "QQQ"],
        "price_column": "adjusted_close",
        "risk_free_rate": 0.0,
        "return_alignment": "exact_common_date_intersection_per_split",
        "evaluated_split_count": 2,
        "strategy_count": 2,
        "strategies": ["buy_hold_SPY", "momentum_net"],
        "equity_base": 1.0,
        "momentum_lookback_days": 252,
        "momentum_top_k": 5,
        "momentum_rebalance_frequency": "ME",
        "transaction_cost_bps": 10.0,
        "cost_model": "net_return = gross_return - turnover * bps / 10000",
        "turnover_convention": "sum_abs_weight_change",
        "split_windows": [
            {
                "split_id": 0,
                "common_start_date": "2020-01-02",
                "common_end_date": "2020-12-31",
                "common_observation_count": 252,
            },
            {
                "split_id": 1,
                "common_start_date": "2021-01-04",
                "common_end_date": "2021-12-31",
                "common_observation_count": 252,
            },
        ],
        "strategy_summary": {
            "buy_hold_SPY": {
                "start_date": "2020-01-02",
                "end_date": "2021-12-31",
                "observation_count": 504,
                "final_equity": 1.25,
                "metrics": {
                    "cumulative_return": 0.25,
                    "cagr": 0.12,
                    "annualized_volatility": 0.18,
                    "sharpe": 0.80,
                    "sortino": 1.00,
                    "max_drawdown": -0.20,
                    "calmar": 0.60,
                    "monthly_win_rate": 0.60,
                    "observation_count": 504,
                },
            },
            "momentum_net": {
                "start_date": "2020-01-02",
                "end_date": "2021-12-31",
                "observation_count": 504,
                "final_equity": 1.20,
                "metrics": {
                    "cumulative_return": 0.20,
                    "cagr": 0.10,
                    "annualized_volatility": 0.12,
                    "sharpe": 0.90,
                    "sortino": 1.10,
                    "max_drawdown": -0.12,
                    "calmar": 0.83,
                    "monthly_win_rate": 0.65,
                    "observation_count": 504,
                },
            },
        },
        "leaders": {
            "highest_stitched_cagr": "buy_hold_SPY",
            "highest_stitched_sharpe": "momentum_net",
            "least_severe_stitched_max_drawdown": "momentum_net",
            "highest_final_equity": "buy_hold_SPY",
        },
    }


def test_get_strategy_metric() -> None:
    summary = make_summary()

    assert get_strategy_metric(summary, "buy_hold_SPY", "cagr") == 0.12
    assert get_strategy_metric(summary, "missing", "cagr") is None


def test_build_stitched_oos_equity_summary_contains_protocol_and_metrics() -> None:
    markdown = build_stitched_oos_equity_summary(make_summary())

    assert "# Stitched Walk-Forward OOS Equity Summary" in markdown
    assert "walk_forward_baseline_oos_stitched_equity" in markdown
    assert "Do not manually edit metric values in this file." in markdown
    assert "| buy_hold_SPY | 1.250 | 12.00% | 0.800 | -20.00%" in markdown
    assert "| momentum_net | 1.200 | 10.00% | 0.900 | -12.00%" in markdown
    assert "Highest stitched CAGR: `buy_hold_SPY`" in markdown
    assert "Highest stitched Sharpe: `momentum_net`" in markdown
    assert "| 1 | 2021-01-04 -> 2021-12-31 | 252 |" in markdown
    assert "risk-return trade-off" in markdown


def test_run_summary_writes_markdown_file(tmp_path) -> None:
    input_path = tmp_path / "stitched_oos_summary.json"
    output_path = tmp_path / "stitched_oos_summary.md"

    input_path.write_text(json.dumps(make_summary()), encoding="utf-8")

    run_summary(input_path=input_path, output_path=output_path)

    assert output_path.exists()
    assert "# Stitched Walk-Forward OOS Equity Summary" in output_path.read_text(encoding="utf-8")
