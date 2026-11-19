"""Timing and weighting fixtures for the other-state peer measure."""

import numpy as np
import pandas as pd
import pytest

from src.peer_study import peer_windows


def observations():
    return pd.DataFrame(
        [
            {
                "id": "target",
                "state": "A",
                "requested_date": "2022-03-31",
                "authorized_date": "2023-01-01",
                "award": 9.5,
            },
            {
                "id": "own",
                "state": "A",
                "requested_date": "2020-01-01",
                "authorized_date": "2021-12-01",
                "award": 20.0,
            },
            {
                "id": "start",
                "state": "B",
                "requested_date": "2020-01-01",
                "authorized_date": "2021-03-31",
                "award": 10.0,
            },
            {
                "id": "before",
                "state": "C",
                "requested_date": "2020-01-01",
                "authorized_date": "2021-03-30",
                "award": 25.0,
            },
            {
                "id": "one",
                "state": "C",
                "requested_date": "2020-01-01",
                "authorized_date": "2022-01-01",
                "award": 8.0,
            },
            {
                "id": "two",
                "state": "C",
                "requested_date": "2020-01-01",
                "authorized_date": "2022-01-01",
                "award": 10.0,
            },
            {
                "id": "same",
                "state": "D",
                "requested_date": "2020-01-01",
                "authorized_date": "2022-03-31",
                "award": 30.0,
            },
            {
                "id": "missing",
                "state": "E",
                "requested_date": "2020-01-01",
                "authorized_date": "2022-02-01",
                "award": np.nan,
            },
        ]
    )


def test_other_state_strict_cutoff_and_calendar_boundary():
    p = peer_windows(observations(), min_awards=1, min_states=1).loc["target"]
    assert p.peer12_ids == "one;start;two"
    assert p.peer12_n == 3 and p.peer12_states == 2 and p.peer12_dates == 2
    assert p.peer12_last == "2022-01-01"
    assert p.peer12 == pytest.approx(9.5)
    assert p.peer12_row == pytest.approx(28 / 3)


def test_six_month_window_and_minimum_coverage_are_explicit():
    p = peer_windows(observations(), 6, min_awards=1, min_states=1).loc["target"]
    assert p.peer6_ids == "one;two" and p.peer6 == 9
    missing = peer_windows(observations()).loc["target"]
    assert pd.isna(missing.peer12) and missing.peer12_n == 3
    with pytest.raises(ValueError, match="specified"):
        peer_windows(observations(), 9)


def test_missing_filing_has_no_peer_values():
    d = observations()
    d.loc[d.id == "target", "requested_date"] = None
    p = peer_windows(d, min_awards=1, min_states=1).loc["target"]
    assert p.peer12_n == 0 and pd.isna(p.peer12)


def test_future_awards_cannot_change_the_target_feature():
    d = observations()
    before = peer_windows(d, min_awards=1, min_states=1).loc["target"]
    d.loc[d.authorized_date >= "2022-03-31", "award"] = 100
    after = peer_windows(d, min_awards=1, min_states=1).loc["target"]
    pd.testing.assert_series_equal(before, after)
