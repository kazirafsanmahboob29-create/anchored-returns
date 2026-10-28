"""Empirical controls and denominator checks for the national extension."""

import json
from pathlib import Path
import pytest
from src.national_study import enrich, describe, select, comparison
from src.eei_benchmarks import read_workbook
from src.treasury import load_snapshot

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rows():
    raw, _ = read_workbook(ROOT / "data/external/eei/eei_rate_review_2025_q3.xlsx")
    _, treasury = load_snapshot(ROOT)
    return enrich(raw, treasury)


def test_preserved_source_and_exclusion_funnel(rows):
    result = describe(rows)
    assert (result["cases"], result["awards"], result["pairs"]) == (2230, 1832, 1810)
    assert result["jurisdictions"] == 50
    assert len({r["id"] for r in rows}) == len(rows)
    assert all(
        r["case_type"] in ("Distribution", "Vertically Integrated")
        and r["authorized_date"] <= "2025-09-30"
        for r in rows
    )


def test_headline_uses_identical_matched_observations(rows):
    a, b = select(rows, 2020, 2021), select(rows, 2023, 2024)
    result = comparison(a, b)
    assert (result["earlier_n"], result["later_n"]) == (77, 89)
    assert result["award_change_bp"] == pytest.approx(32.2749161009)
    assert result["treasury_change_bp"] == pytest.approx(291.6565008026)
    assert all(r["treasury_gap_days"] == 0 for r in a + b if r["award_bp"] is not None)
    assert describe(a)["pairs"] == 75


def test_common_groups_are_shared_and_equally_weighted(rows):
    a, b = select(rows, 2020, 2021), select(rows, 2023, 2024)
    states, utilities = (comparison(a, b, w) for w in ("state", "utility"))
    assert states["common_groups"] == 32
    assert states["award_change_bp"] == pytest.approx(23.3500744048)
    assert utilities["common_groups"] == 46
    assert utilities["award_change_bp"] == pytest.approx(24.3913043478)
    assert all(g["earlier_n"] > 0 and g["later_n"] > 0 for g in utilities["groups"])


def test_missing_awards_and_unavailable_treasury_never_become_zero(rows):
    historic = select(rows, 1980, 1984)
    assert describe(historic)["matched_treasury"] == 0
    assert comparison(historic, select(rows, 2023, 2024))["award_change_bp"] is None
    missing = [r for r in rows if r["award_bp"] is None]
    assert describe(missing)["mean_award_bp"] is None
    assert describe(missing)["pairs"] == 0
    assert comparison([], [], "state")["common_groups"] == 0


def test_longer_window_and_partial_year_are_explicit(rows):
    a, b = describe(select(rows, 2010, 2014)), describe(select(rows, 2020, 2024))
    assert (a["awards"], b["awards"]) == (221, 200)
    assert (b["mean_award_bp"] - a["mean_award_bp"]) == pytest.approx(-48.1025339367)
    assert len(select(rows, 2025, 2025)) == 32
    shared = comparison(select(rows, 2010, 2014), select(rows, 2020, 2024), "state")
    assert shared["common_groups"] == 43
    assert sum(g["award_change_bp"] < 0 for g in shared["groups"]) == 41
    with pytest.raises(ValueError):
        select(rows, 2026, 2026)
