import pandas as pd
import pytest
from src.backtesting.walk_forward import WalkForwardSplit, generate_walk_forward_splits
from src.config.settings import WalkForwardConfig


def make_config(min_train_observations: int = 1000) -> WalkForwardConfig:
    return WalkForwardConfig(
        train_years=6,
        test_years=1,
        step_years=1,
        min_train_observations=min_train_observations,
        rebalance_frequency="M",
    )


def test_generate_walk_forward_splits_calendar_years() -> None:
    dates = pd.Series(pd.bdate_range("2010-01-04", "2020-12-31"))
    splits = generate_walk_forward_splits(dates=dates, config=make_config())

    assert len(splits) == 5

    first = splits[0]
    assert first.split_id == 0
    assert first.train_start == pd.Timestamp("2010-01-04")
    assert first.train_end == pd.Timestamp("2015-12-31")
    assert first.test_start == pd.Timestamp("2016-01-01")
    assert first.test_end == pd.Timestamp("2016-12-31")

    last = splits[-1]
    assert last.train_start == pd.Timestamp("2014-01-01")
    assert last.train_end == pd.Timestamp("2019-12-31")
    assert last.test_start == pd.Timestamp("2020-01-01")
    assert last.test_end == pd.Timestamp("2020-12-31")


def test_walk_forward_split_to_dict() -> None:
    split = WalkForwardSplit(
        split_id=3,
        train_start=pd.Timestamp("2013-01-01"),
        train_end=pd.Timestamp("2018-12-31"),
        test_start=pd.Timestamp("2019-01-01"),
        test_end=pd.Timestamp("2019-12-31"),
    )

    assert split.to_dict() == {
        "split_id": 3,
        "train_start": "2013-01-01",
        "train_end": "2018-12-31",
        "test_start": "2019-01-01",
        "test_end": "2019-12-31",
    }


def test_empty_dates_fail() -> None:
    with pytest.raises(ValueError, match="dates must not be empty"):
        generate_walk_forward_splits(
            dates=pd.Series([], dtype="datetime64[ns]"), config=make_config()
        )


def test_no_valid_splits_fail_when_min_train_observations_too_high() -> None:
    dates = pd.Series(pd.bdate_range("2010-01-04", "2020-12-31"))

    with pytest.raises(ValueError, match="No valid walk-forward splits"):
        generate_walk_forward_splits(
            dates=dates,
            config=make_config(min_train_observations=100000),
        )


def test_incomplete_final_test_window_is_excluded() -> None:
    dates = pd.Series(pd.bdate_range("2011-01-04", "2026-05-13"))

    splits = generate_walk_forward_splits(dates=dates, config=make_config())

    assert len(splits) == 9
    assert splits[-1].train_start == pd.Timestamp("2019-01-01")
    assert splits[-1].train_end == pd.Timestamp("2024-12-31")
    assert splits[-1].test_start == pd.Timestamp("2025-01-01")
    assert splits[-1].test_end == pd.Timestamp("2025-12-31")
