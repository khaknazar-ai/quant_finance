from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.config.settings import WalkForwardConfig


@dataclass(frozen=True)
class WalkForwardSplit:
    split_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp

    def to_dict(self) -> dict[str, int | str]:
        return {
            "split_id": self.split_id,
            "train_start": str(self.train_start.date()),
            "train_end": str(self.train_end.date()),
            "test_start": str(self.test_start.date()),
            "test_end": str(self.test_end.date()),
        }


def generate_walk_forward_splits(
    dates: pd.Series,
    config: WalkForwardConfig,
) -> list[WalkForwardSplit]:
    """Generate complete calendar-year walk-forward train/test splits.

    The function intentionally excludes incomplete final test windows. This keeps
    out-of-sample annual metrics comparable across splits.
    """
    unique_dates = (
        pd.Series(pd.to_datetime(dates).dropna().unique()).sort_values().reset_index(drop=True)
    )

    if unique_dates.empty:
        raise ValueError("dates must not be empty.")

    min_date = unique_dates.iloc[0]
    max_date = unique_dates.iloc[-1]

    start_year = int(min_date.year)
    split_id = 0
    splits: list[WalkForwardSplit] = []

    current_train_start_year = start_year

    while True:
        train_start = pd.Timestamp(year=current_train_start_year, month=1, day=1)
        train_start = max(train_start, min_date)

        train_end = pd.Timestamp(
            year=current_train_start_year + config.train_years - 1,
            month=12,
            day=31,
        )
        test_start = train_end + pd.Timedelta(days=1)
        test_end = pd.Timestamp(
            year=test_start.year + config.test_years - 1,
            month=12,
            day=31,
        )

        if test_end > max_date:
            break

        train_dates = unique_dates[(unique_dates >= train_start) & (unique_dates <= train_end)]

        if len(train_dates) >= config.min_train_observations:
            splits.append(
                WalkForwardSplit(
                    split_id=split_id,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )
            split_id += 1

        current_train_start_year += config.step_years

    if not splits:
        raise ValueError("No valid walk-forward splits generated.")

    return splits
