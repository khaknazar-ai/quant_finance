from pathlib import Path

import pandas as pd
import pytest
from scripts.generate_walk_forward_splits import build_walk_forward_report


def write_walk_forward_config(path: Path, min_train_observations: int = 1000) -> None:
    path.write_text(
        f"""
walk_forward:
  train_years: 6
  test_years: 1
  step_years: 1
  min_train_observations: {min_train_observations}
  rebalance_frequency: "M"

backtest:
  initial_capital: 100000.0
  transaction_cost_bps: 10
  slippage_bps: 0
  allow_short: false
  allow_leverage: false
  max_asset_weight: 0.40
""",
        encoding="utf-8",
    )


def make_feature_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2011-01-04", "2020-12-31")
    frame = pd.DataFrame(
        {
            "date": list(dates) * 2,
            "ticker": ["SPY"] * len(dates) + ["QQQ"] * len(dates),
            "adjusted_close": [100.0] * len(dates) + [200.0] * len(dates),
            "momentum_21d": [0.1] * len(dates) + [0.2] * len(dates),
            "rank_momentum_21d": [0.5] * len(dates) + [1.0] * len(dates),
        }
    )

    frame.loc[frame["date"] < pd.Timestamp("2011-01-06"), "momentum_21d"] = None
    frame.loc[frame["date"] < pd.Timestamp("2011-01-06"), "rank_momentum_21d"] = None

    return frame


def test_build_walk_forward_report_uses_complete_feature_dates(tmp_path: Path) -> None:
    config_path = tmp_path / "walk_forward.yaml"
    write_walk_forward_config(config_path)

    report = build_walk_forward_report(
        features=make_feature_frame(),
        config_path=config_path,
        require_complete_features=True,
    )

    assert report["input_rows"] > 0
    assert report["require_complete_features"] is True
    assert report["feature_count"] == 2
    assert report["eligible_min_date"] == "2011-01-06"
    assert report["eligible_max_date"] == "2020-12-31"
    assert report["train_years"] == 6
    assert report["test_years"] == 1
    assert report["step_years"] == 1
    assert report["split_count"] == 4

    first_split = report["splits"][0]
    assert first_split == {
        "split_id": 0,
        "train_start": "2011-01-06",
        "train_end": "2016-12-31",
        "test_start": "2017-01-01",
        "test_end": "2017-12-31",
    }


def test_build_walk_forward_report_requires_date_column(tmp_path: Path) -> None:
    config_path = tmp_path / "walk_forward.yaml"
    write_walk_forward_config(config_path)

    features = make_feature_frame().drop(columns=["date"])

    with pytest.raises(ValueError, match="date column"):
        build_walk_forward_report(features=features, config_path=config_path)


def test_build_walk_forward_report_requires_feature_columns(tmp_path: Path) -> None:
    config_path = tmp_path / "walk_forward.yaml"
    write_walk_forward_config(config_path)

    features = make_feature_frame()[["date", "ticker", "adjusted_close"]]

    with pytest.raises(ValueError, match="No feature columns"):
        build_walk_forward_report(features=features, config_path=config_path)
