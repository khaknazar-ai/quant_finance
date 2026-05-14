import pandas as pd
import pytest
from scripts.evaluate_walk_forward_baselines import (
    aggregate_metrics_by_strategy,
    build_walk_forward_baseline_report,
    filter_returns_to_test_window,
    load_walk_forward_splits_report,
)


def make_price_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2018-01-01", periods=800)
    daily_returns = {
        "SPY": 0.0008,
        "QQQ": 0.0012,
        "IEF": 0.0002,
        "GLD": 0.0004,
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


def make_splits_report() -> dict:
    return {
        "split_count": 2,
        "splits": [
            {
                "split_id": 0,
                "train_start": "2018-01-01",
                "train_end": "2018-12-31",
                "test_start": "2019-01-01",
                "test_end": "2019-12-31",
            },
            {
                "split_id": 1,
                "train_start": "2019-01-01",
                "train_end": "2019-12-31",
                "test_start": "2020-01-01",
                "test_end": "2020-12-31",
            },
        ],
    }


def test_load_walk_forward_splits_report_rejects_empty_splits(tmp_path) -> None:
    path = tmp_path / "splits.json"
    path.write_text('{"splits": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="at least one split"):
        load_walk_forward_splits_report(path)


def test_filter_returns_to_test_window_uses_exact_common_dates() -> None:
    returns = {
        "a": pd.Series(
            [0.01, 0.02, 0.03],
            index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-06"]),
        ),
        "b": pd.Series(
            [0.04, 0.05, 0.06],
            index=pd.to_datetime(["2020-01-01", "2020-01-03", "2020-01-06"]),
        ),
    }

    filtered = filter_returns_to_test_window(
        return_series_by_strategy=returns,
        test_start="2020-01-01",
        test_end="2020-01-06",
    )

    assert list(filtered["a"].index) == list(pd.to_datetime(["2020-01-01", "2020-01-06"]))
    assert list(filtered["b"].index) == list(pd.to_datetime(["2020-01-01", "2020-01-06"]))


def test_aggregate_metrics_by_strategy() -> None:
    split_reports = [
        {
            "split_id": 0,
            "metrics": {
                "strategy": {
                    "cagr": 0.10,
                    "sharpe": 1.0,
                    "max_drawdown": -0.20,
                    "observation_count": 252,
                }
            },
        },
        {
            "split_id": 1,
            "metrics": {
                "strategy": {
                    "cagr": -0.05,
                    "sharpe": -0.2,
                    "max_drawdown": -0.30,
                    "observation_count": 252,
                }
            },
        },
    ]

    aggregate = aggregate_metrics_by_strategy(split_reports)

    assert aggregate["strategy"]["split_count"] == 2
    assert aggregate["strategy"]["metrics"]["cagr"]["mean"] == pytest.approx(0.025)
    assert aggregate["strategy"]["positive_cagr_split_fraction"] == pytest.approx(0.5)
    assert aggregate["strategy"]["best_cagr_split_id"] == 0
    assert aggregate["strategy"]["worst_cagr_split_id"] == 1


def test_build_walk_forward_baseline_report() -> None:
    report = build_walk_forward_baseline_report(
        prices=make_price_frame(),
        splits_report=make_splits_report(),
        benchmark_ticker="SPY",
        universe_tickers=["SPY", "QQQ", "IEF", "GLD", "TLT"],
        transaction_cost_bps=10.0,
    )

    assert report["evaluation_type"] == "walk_forward_baseline_oos"
    assert report["return_alignment"] == "exact_common_date_intersection_per_split"
    assert report["requested_split_count"] == 2
    assert report["evaluated_split_count"] == 2
    assert report["strategy_count"] == 4
    assert report["strategies"] == [
        "buy_hold_SPY",
        "equal_weight",
        "momentum_top_5_252d_gross",
        "momentum_top_5_252d_net_10bps",
    ]

    assert len(report["splits"]) == 2

    for split_report in report["splits"]:
        assert split_report["common_observation_count"] > 0
        assert set(split_report["metrics"]) == set(report["strategies"])

        observation_counts = {
            metrics["observation_count"] for metrics in split_report["metrics"].values()
        }
        assert len(observation_counts) == 1

    gross_cagr = report["aggregate_metrics"]["momentum_top_5_252d_gross"]["metrics"]["cagr"]["mean"]
    net_cagr = report["aggregate_metrics"]["momentum_top_5_252d_net_10bps"]["metrics"]["cagr"][
        "mean"
    ]

    assert net_cagr <= gross_cagr
