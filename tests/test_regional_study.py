"""Regional coverage, stratum separation and preservation of the earlier cohort."""

from pathlib import Path
import json
import pytest
from src.research_cohort import cohort_report
from src.research_overview import overview_payload
from src.regional_study import records, summarize
from src.national_study import regional_context, enrich
from src.eei_benchmarks import read_workbook
from src.treasury import load_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_expansion_preserves_primary_and_old_manifest():
    old, new = cohort_report(ROOT, "0.1.4"), cohort_report(ROOT)
    primary = lambda d: {r["candidate_id"] for r in d["members"] if r["stratum"] == "primary"}
    assert old["total"] == 23 and new["total"] == 27
    assert primary(old) == primary(new) and new["primary"] == 22
    assert new["formula"] == 4 and new["supplemental"] == 1
    assert (ROOT / "data/research/sample_screening.json").read_bytes() == (
        ROOT / "data/research/sample_screening_v0.1.5.json"
    ).read_bytes()


def test_formula_facts_are_not_backfilled_or_classified_as_discretionary():
    p = overview_payload(ROOT)
    r = {r["case_id"]: r for r in records(p)}
    assert r["CAND-VT-24-2137"]["award_bp"] is None
    assert r["CAND-VT-19-1932"]["award_bp"] is None
    assert r["CAND-VT-25-1261"]["award_bp"] == 962
    assert r["CAND-VT-26-1298"]["award_bp"] == 963
    primary = summarize(list(r.values()))
    all_rows = summarize(list(r.values()), include_settlements=True, include_formulas=True)
    assert sum(s["orders"] for s in primary) == 22
    assert sum(s["awards"] for s in primary) == 19
    assert sum(s["awards"] for s in all_rows) == 22
    assert all(
        o["award_kind"] == "formula_implementation"
        for o in p["insights"]["outcomes"]
        if o["case_id"] in ["CAND-VT-25-1261", "CAND-VT-26-1298"]
    )


def test_publisher_panel_keeps_missing_awards_and_all_six_states():
    raw, _ = read_workbook(ROOT / "data/external/eei/eei_rate_review_2025_q3.xlsx")
    _, treasury = load_snapshot(ROOT)
    result = regional_context(enrich(raw, treasury))
    assert result["coverage"]["cases"] == 57 and result["coverage"]["awards"] == 46
    assert len(result["states"]) == 6
    changed = [r for r in result["states"] if r["change_bp"] is not None]
    assert len(changed) == 5 and sum(r["change_bp"] < 0 for r in changed) == 4
    assert next(r for r in result["states"] if r["state"] == "Rhode Island")["later_awards"] == 0
    assert result["recent"]["earlier_n"] == result["recent"]["later_n"] == 7
    assert result["recent"]["award_change_bp"] == pytest.approx(45.1428571429)


def test_common_utility_check_is_an_explicit_source_label_comparison():
    raw, _ = read_workbook(ROOT / "data/external/eei/eei_rate_review_2025_q3.xlsx")
    _, treasury = load_snapshot(ROOT)
    r = regional_context(enrich(raw, treasury))["longer_utility"]
    assert r["common_groups"] == 8 and r["earlier_n"] == 9 and r["later_n"] == 15
    assert sum(g["award_change_bp"] < 0 for g in r["groups"]) == 7
    assert r["award_change_bp"] == pytest.approx(-39.775)
