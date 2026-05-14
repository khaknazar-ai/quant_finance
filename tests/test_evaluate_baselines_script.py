import math

import pandas as pd
import pytest
from scripts.evaluate_baselines import (
    align_return_series_to_common_window,
    build_baseline_metrics_report,
    make_json_safe_metrics,
    summarize_cost_impact,
)


def make_price_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=320)
    daily_returns = {
        "SPY": 0.0010,
        "QQQ": 0.0020,
        "IEF": 0.0002,
        "GLD": 0.0005,
        "TLT": -0.0001,
    }

    records = []
    for ticker, daily_return in daily_returns.items():
        for day_index, date in enumerate(dates):
            records.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "adjusted_close": 100.0 * ((1.0 + daily_return) ** day_index),
                }
            )

    return pd.DataFrame(records)


def test_make_json_safe_metrics_replaces_nan_and_inf() -> None:
    metrics = {
        "cagr": 0.10,
        "sharpe": math.nan,
        "sortino": math.inf,
        "observation_count": 10,
    }

    safe_metrics = make_json_safe_metrics(metrics)

    assert safe_metrics == {
        "cagr": 0.10,
        "sharpe": None,
        "sortino": None,
        "observation_count": 10,
    }


def test_align_return_series_uses_exact_common_dates_not_only_range() -> None:
    returns = {
        "strategy_a": pd.Series(
            [0.01, 0.02, 0.03],
            index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-06"]),
        ),
        "strategy_b": pd.Series(
            [0.04, 0.05, 0.06],
            index=pd.to_datetime(["2020-01-01", "2020-01-03", "2020-01-06"]),
        ),
    }

    aligned = align_return_series_to_common_window(returns)
    expected_index = list(pd.to_datetime(["2020-01-01", "2020-01-06"]))

    assert list(aligned["strategy_a"].index) == expected_index
    assert list(aligned["strategy_b"].index) == expected_index


def test_align_return_series_rejects_duplicate_dates() -> None:
    returns = {
        "strategy_a": pd.Series(
            [0.01, 0.02],
            index=pd.to_datetime(["2020-01-01", "2020-01-01"]),
        ),
        "strategy_b": pd.Series(
            [0.03, 0.04],
            index=pd.to_datetime(["2020-01-01", "2020-01-02"]),
        ),
    }

    with pytest.raises(ValueError, match="duplicate dates"):
        align_return_series_to_common_window(returns)


def test_summarize_cost_impact() -> None:
    common_index = pd.to_datetime(["2020-01-02", "2020-01-03"])
    turnover = pd.Series([1.0, 2.0], index=common_index)
    cost_returns = pd.Series([0.001, 0.002], index=common_index)

    summary = summarize_cost_impact(
        turnover=turnover,
        cost_returns=cost_returns,
        common_index=common_index,
    )

    assert summary["average_turnover"] == pytest.approx(1.5)
    assert summary["total_turnover"] == pytest.approx(3.0)
    assert summary["average_transaction_cost_return"] == pytest.approx(0.0015)
    assert summary["total_transaction_cost_return"] == pytest.approx(0.003)
    assert summary["cost_observation_count"] == 2


def test_build_baseline_metrics_report_uses_common_date_window() -> None:
    report = build_baseline_metrics_report(
        prices=make_price_frame(),
        benchmark_ticker="SPY",
        universe_tickers=["SPY", "QQQ", "IEF", "GLD", "TLT"],
        transaction_cost_bps=10.0,
    )

    assert report["benchmark_ticker"] == "SPY"
    assert report["universe_tickers"] == ["SPY", "QQQ", "IEF", "GLD", "TLT"]
    assert report["price_column"] == "adjusted_close"
    assert report["risk_free_rate"] == 0.0
    assert report["return_alignment"] == "exact_common_date_intersection"
    assert report["include_momentum"] is True
    assert report["momentum_lookback_days"] == 252
    assert report["momentum_top_k"] == 5
    assert report["momentum_rebalance_frequency"] == "ME"
    assert report["transaction_cost_bps"] == 10.0
    assert report["strategy_count"] == 4

    assert set(report["metrics"]) == {
        "buy_hold_SPY",
        "equal_weight",
        "momentum_top_5_252d_gross",
        "momentum_top_5_252d_net_10bps",
    }

    gross_return = report["metrics"]["momentum_top_5_252d_gross"]["cumulative_return"]
    net_return = report["metrics"]["momentum_top_5_252d_net_10bps"]["cumulative_return"]

    assert net_return < gross_return
    assert report["momentum_cost_summary"]["total_transaction_cost_return"] > 0

    date_ranges = {
        (date_range["start"], date_range["end"]) for date_range in report["date_ranges"].values()
    }
    assert len(date_ranges) == 1

    observation_counts = {metrics["observation_count"] for metrics in report["metrics"].values()}
    assert len(observation_counts) == 1
    assert next(iter(observation_counts)) == report["common_observation_count"]
    assert report["common_observation_count"] > 0

    common_range = next(iter(date_ranges))
    assert report["common_start_date"] == common_range[0]
    assert report["common_end_date"] == common_range[1]


def test_build_baseline_metrics_report_fails_for_missing_benchmark() -> None:
    with pytest.raises(ValueError, match="Ticker not found"):
        build_baseline_metrics_report(
            prices=make_price_frame(),
            benchmark_ticker="IWM",
            universe_tickers=["SPY", "QQQ", "IEF", "GLD", "TLT"],
        )
