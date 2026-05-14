import pandas as pd
import pytest
from scripts.build_walk_forward_oos_equity import (
    add_stitched_equity,
    build_stitched_oos_equity_report,
    stitch_walk_forward_returns,
    summarize_stitched_equity,
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


def test_add_stitched_equity_compounds_returns_by_strategy() -> None:
    stitched_returns = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "split_id": [0, 0],
            "strategy": ["strategy", "strategy"],
            "oos_return": [0.10, -0.10],
        }
    )

    oos_equity = add_stitched_equity(stitched_returns)

    assert oos_equity["equity"].iloc[0] == pytest.approx(1.10)
    assert oos_equity["equity"].iloc[1] == pytest.approx(0.99)


def test_stitch_walk_forward_returns_rejects_overlapping_split_dates() -> None:
    returns = {
        "strategy": pd.Series(
            [0.01, 0.02, 0.03],
            index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
        )
    }
    splits = [
        {
            "split_id": 0,
            "test_start": "2020-01-01",
            "test_end": "2020-01-02",
        },
        {
            "split_id": 1,
            "test_start": "2020-01-02",
            "test_end": "2020-01-03",
        },
    ]

    with pytest.raises(ValueError, match="Overlapping split dates"):
        stitch_walk_forward_returns(
            return_series_by_strategy=returns,
            splits=splits,
        )


def test_summarize_stitched_equity_returns_strategy_metrics() -> None:
    stitched_returns = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "split_id": [0, 0, 0],
            "strategy": ["strategy", "strategy", "strategy"],
            "oos_return": [0.01, 0.02, -0.01],
        }
    )
    oos_equity = add_stitched_equity(stitched_returns)

    summary = summarize_stitched_equity(oos_equity)

    assert summary["strategy"]["observation_count"] == 3
    assert summary["strategy"]["final_equity"] > 1.0
    assert "cagr" in summary["strategy"]["metrics"]


def test_build_stitched_oos_equity_report() -> None:
    oos_equity, summary = build_stitched_oos_equity_report(
        prices=make_price_frame(),
        splits_report=make_splits_report(),
        benchmark_ticker="SPY",
        universe_tickers=["SPY", "QQQ", "IEF", "GLD", "TLT"],
        transaction_cost_bps=10.0,
    )

    assert summary["evaluation_type"] == "walk_forward_baseline_oos_stitched_equity"
    assert summary["return_alignment"] == "exact_common_date_intersection_per_split"
    assert summary["evaluated_split_count"] == 2
    assert summary["strategy_count"] == 4
    assert summary["equity_base"] == 1.0
    assert set(summary["strategies"]) == {
        "buy_hold_SPY",
        "equal_weight",
        "momentum_top_5_252d_gross",
        "momentum_top_5_252d_net_10bps",
    }
    assert not oos_equity.empty
    assert set(oos_equity.columns) == {
        "date",
        "split_id",
        "strategy",
        "oos_return",
        "equity",
    }

    for strategy_name in summary["strategies"]:
        assert summary["strategy_summary"][strategy_name]["final_equity"] > 0.0
        assert summary["strategy_summary"][strategy_name]["observation_count"] > 0

    assert summary["leaders"]["highest_stitched_cagr"] in summary["strategies"]
