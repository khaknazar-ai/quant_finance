import json

from scripts.summarize_baseline_metrics import (
    build_baseline_summary,
    find_best_strategy,
    format_float,
    format_percent,
    run_summary,
)


def make_report() -> dict:
    return {
        "benchmark_ticker": "SPY",
        "universe_tickers": ["SPY", "QQQ"],
        "price_column": "adjusted_close",
        "risk_free_rate": 0.0,
        "return_alignment": "exact_common_date_intersection",
        "common_start_date": "2020-01-02",
        "common_end_date": "2020-12-31",
        "common_observation_count": 252,
        "include_momentum": True,
        "momentum_lookback_days": 252,
        "momentum_top_k": 5,
        "momentum_rebalance_frequency": "ME",
        "strategy_count": 3,
        "metrics": {
            "buy_hold_SPY": {
                "cumulative_return": 0.20,
                "cagr": 0.20,
                "annualized_volatility": 0.18,
                "sharpe": 1.10,
                "sortino": 1.40,
                "max_drawdown": -0.30,
                "calmar": 0.67,
                "monthly_win_rate": 0.60,
                "observation_count": 252,
            },
            "equal_weight": {
                "cumulative_return": 0.12,
                "cagr": 0.12,
                "annualized_volatility": 0.10,
                "sharpe": 1.00,
                "sortino": 1.20,
                "max_drawdown": -0.15,
                "calmar": 0.80,
                "monthly_win_rate": 0.58,
                "observation_count": 252,
            },
            "momentum_top_5_252d": {
                "cumulative_return": 0.16,
                "cagr": 0.16,
                "annualized_volatility": 0.12,
                "sharpe": 1.30,
                "sortino": 1.50,
                "max_drawdown": -0.12,
                "calmar": 1.33,
                "monthly_win_rate": 0.62,
                "observation_count": 252,
            },
        },
    }


def test_format_helpers() -> None:
    assert format_percent(0.1234) == "12.34%"
    assert format_percent(None) == "n/a"
    assert format_float(1.23456) == "1.235"
    assert format_float(None) == "n/a"


def test_find_best_strategy() -> None:
    metrics = make_report()["metrics"]

    assert find_best_strategy(metrics, "cagr") == "buy_hold_SPY"
    assert find_best_strategy(metrics, "sharpe") == "momentum_top_5_252d"
    assert find_best_strategy(metrics, "max_drawdown") == "momentum_top_5_252d"


def test_build_baseline_summary_contains_protocol_and_metrics() -> None:
    summary = build_baseline_summary(make_report())

    assert "This report is generated from `reports/baseline_metrics.json`." in summary
    assert "exact_common_date_intersection" in summary
    assert "| buy_hold_SPY | 20.00% | 1.100 | -30.00%" in summary
    assert "Highest CAGR: `buy_hold_SPY`" in summary
    assert "Highest Sharpe: `momentum_top_5_252d`" in summary
    assert "Least severe max drawdown: `momentum_top_5_252d`" in summary


def test_run_summary_writes_markdown_file(tmp_path) -> None:
    input_path = tmp_path / "baseline_metrics.json"
    output_path = tmp_path / "baseline_metrics_summary.md"

    input_path.write_text(json.dumps(make_report()), encoding="utf-8")

    run_summary(input_path=input_path, output_path=output_path)

    assert output_path.exists()
    assert "# Baseline Metrics Summary" in output_path.read_text(encoding="utf-8")
