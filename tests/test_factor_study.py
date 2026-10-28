"""Timing and sample rules are distinct from the empirical hypotheses."""

from datetime import date, timedelta
import json
from pathlib import Path
import pytest
from src.factor_study import (
    average_before,
    economic_join,
    panel,
    load_series,
    complete,
    MAIN,
    digest,
)
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_daily_window_excludes_authorization_and_later_observations():
    records = [
        dict(date=(date(2020, 1, 1) + timedelta(days=i)).isoformat(), value=float(i))
        for i in range(100)
    ]
    value, n = average_before(records, "2020-02-01", 30)
    assert n == 30 and value == pytest.approx(15.5)
    assert average_before(records[:5], "2020-02-01", 30)[0] is None


def test_month_and_week_lags_do_not_use_later_dates():
    series = {name: [] for name in ["DGS10", "T10Y3M", "STLFSI4", "CPIAUCNS"]}
    series["CPIAUCNS"] = [
        dict(date="2019-11-01", value=100),
        dict(date="2020-11-01", value=103),
        dict(date="2020-12-01", value=999),
    ]
    series["STLFSI4"] = [dict(date="2021-01-01", value=2), dict(date="2021-01-08", value=999)]
    result = economic_join("2021-01-20", series)
    assert result["inflation_month"] == "2020-11-01"
    assert result["inflation"] == pytest.approx(3)
    assert result["stress"] == 2 and result["stress_date"] == "2021-01-01"


def test_prior_awards_never_use_same_day_or_future_rows():
    def row(identifier, day, award):
        return dict(
            id=identifier,
            state="Maine",
            utility="Example unit-test utility",
            award_bp=award,
            request_bp=None,
            authorized_date=day,
            requested_date="",
            year=int(day[:4]),
            case_type="Distribution",
        )

    source = [
        row("a", "2010-01-01", 900),
        row("b", "2011-01-01", 1000),
        row("c", "2011-01-01", 1100),
        row("d", "2012-01-01", 1200),
    ]
    result = panel(source, {name: [] for name in ["DGS10", "T10Y3M", "STLFSI4", "CPIAUCNS"]})
    assert result[0]["prior"] is None
    assert result[1]["prior"] == result[2]["prior"] == 9
    assert result[3]["prior"] == 10.5 and result[3]["prior_ids"] == "b;c"


def test_archived_inputs_match_hashes_and_main_models_share_rows():
    study = json.loads((ROOT / "reports/factor-study/study.json").read_text())
    for name, expected in study["input_sha256"].items():
        assert digest(ROOT / name) == expected, name
    assert study["coverage"]["entries"] == 777 and study["coverage"]["awards"] == 589
    assert study["coverage"]["complete"] == 533
    assert all(m["rows"] == study["models"][0]["rows"] for m in study["models"])
    assert len(complete(pd.DataFrame(study["records"]))) == 533


def test_all_join_dates_obey_rules_and_missing_awards_stay_missing():
    study = json.loads((ROOT / "reports/factor-study/study.json").read_text())
    assert sum(r["roe"] is None for r in study["records"]) == 188
    for row in study["records"]:
        if row["prior_date"]:
            assert row["prior_date"] < row["authorized_date"]
        if row["stress_date"]:
            assert (
                date.fromisoformat(row["authorized_date"]) - date.fromisoformat(row["stress_date"])
            ).days >= 14
    assert load_series(ROOT)["CPIAUCNS"]


def test_temporal_holdout_keeps_later_rows_out_of_estimation():
    study = json.loads((ROOT / "reports/factor-study/study.json").read_text())
    holdout = study["holdout"]
    assert holdout["train_years"] == [2010, 2019] and holdout["test_years"] == [2020, 2024]
    assert all(2020 <= int(p["date"][:4]) <= 2024 for p in holdout["predictions"])
    assert all(m["train_n"] == 345 and m["test_n"] == 188 for m in holdout["metrics"])
