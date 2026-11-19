"""Window indexing must preserve timing, missing values and source identities."""

import csv
from datetime import date, timedelta

import numpy as np
import pytest

from src.economic_history import EconomicHistory, SeriesIndex
from src.factor_study import economic_join


def records():
    return [
        {
            "date": (date(2000, 1, 1) + timedelta(days=i)).isoformat(),
            "value": None if i % 7 == 0 else i / 10,
        }
        for i in range(130)
    ]


def test_indexed_windows_equal_direct_calculation_and_exclude_decision_day():
    values = records()
    index = SeriesIndex.from_records(values)
    for written in ("2000-03-01", "2000-04-10"):
        mean, count = index.windows([written], days=30, minimum=10)
        start = (date.fromisoformat(written) - timedelta(days=30)).isoformat()
        expected = [
            r["value"] for r in values if start <= r["date"] < written and r["value"] is not None
        ]
        assert count[0] == len(expected)
        assert mean[0] == pytest.approx(np.mean(expected), abs=1e-12)


def test_missing_stale_and_zero_values_remain_distinct():
    index = SeriesIndex.from_records(
        [{"date": "2000-01-01", "value": 0.0}, {"date": "2000-01-02", "value": None}]
    )
    mean, count = index.windows(["2000-01-02", "2000-01-20"], days=30, minimum=1)
    assert mean[0] == 0 and count.tolist() == [1, 1]
    assert np.isnan(mean[1])
    assert np.isnan(index.exact(["2000-01-02"])[0])
    latest, observed = index.latest(["2000-01-15", "2000-02-01"])
    assert latest[0] == 0 and observed[0] == "2000-01-01"
    assert np.isnan(latest[1]) and observed[1] == ""


@pytest.mark.parametrize(
    "values",
    [
        [],
        [{"date": "2000-01-01", "value": float("inf")}],
        [{"date": "2000-01-01", "value": 1}, {"date": "2000-01-01", "value": 2}],
        [{"date": "2000-01-02", "value": 1}, {"date": "2000-01-01", "value": 2}],
    ],
)
def test_bad_economic_observations_are_rejected(values):
    with pytest.raises(ValueError):
        SeriesIndex.from_records(values)


def test_wrong_csv_series_is_rejected(tmp_path):
    path = tmp_path / "wrong.csv"
    path.write_text("DATE,OTHER\n2000-01-01,1\n")
    with pytest.raises(ValueError, match="series identity"):
        SeriesIndex.from_csv(path, "DGS10")


def test_real_indexed_joins_match_direct_original_algorithm():
    from src.expanded_study import ROOT

    history = EconomicHistory(ROOT)
    original = {}
    for name in ("DGS10", "T10Y3M", "CPIAUCNS", "STLFSI4"):
        with (history.folder / "macro" / (name + ".csv")).open() as stream:
            original[name] = [
                {
                    "date": r.get("observation_date", r.get("DATE")),
                    "value": None if r[name] in ("", ".") else float(r[name]),
                }
                for r in csv.DictReader(stream)
            ]
    days = ["1995-04-10", "2011-12-30", "2024-11-01"]
    result = history.join(days, ["Connecticut"] * len(days))
    for i, day in enumerate(days):
        direct = economic_join(day, original)
        for key in ("treasury90", "curve90", "inflation", "stress"):
            assert result.iloc[i][key] == pytest.approx(direct[key], abs=1e-10)
    assert result.unemployment.notna().all()


def test_unknown_state_has_no_national_fallback():
    from src.expanded_study import ROOT

    with pytest.raises(ValueError, match="no verified economic mapping"):
        EconomicHistory(ROOT).join(["2024-01-01"], ["Unknown"])


def test_failed_retrieval_does_not_publish_an_incomplete_snapshot(tmp_path, monkeypatch):
    from scripts import fetch_expanded_sources

    def incomplete(root, output):
        output.mkdir()
        (output / "one_response.csv").write_text("Incomplete retrieval")
        raise ValueError("A later source failed")

    monkeypatch.setattr(fetch_expanded_sources, "_retrieve", incomplete)
    target = tmp_path / "source"
    with pytest.raises(ValueError, match="later source failed"):
        fetch_expanded_sources.acquire(tmp_path, output=target)
    assert not target.exists()
    assert not list(tmp_path.glob(".economic-retrieval-*"))
