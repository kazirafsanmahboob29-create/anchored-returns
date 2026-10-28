"""Checks of empirical export roles and cross-software missingness preservation."""

from copy import deepcopy

import pandas as pd
import pytest

from src.research_analysis import (
    tables_from_payload,
    write_table,
    source_inventory,
    reconstruction_rows,
)
from src.research_insights import build_insights
from src.research_overview import overview_payload, ROOT
from src.treasury_crosscheck import load_crosscheck


@pytest.fixture(scope="module")
def payload():
    return overview_payload()


def test_actual_numeric_coverage_includes_historical_entries_without_inventing_coding(payload):
    p = payload
    tables = tables_from_payload(p)
    outcomes = {r["case_id"]: r for r in tables["outcomes"]}
    assert len(outcomes) == 22 and sum(r["gap_bp"] is not None for r in outcomes.values()) == 7
    assert outcomes["CAND-MA-19-120"]["gap_bp"] == -55
    assert outcomes["CAND-MA-23-150"]["gap_bp"] == -115
    assert outcomes["CAND-CT-22-08-08"]["award_pct"] == 8.63
    assert outcomes["CAND-CT-22-08-08"]["gap_bp"] == -157
    assert outcomes["CAND-RI-4770-4780"]["award_pct"] == 9.275
    assert outcomes["CAND-RI-4770-4780"]["award_kind"] == "approved_settlement"
    assert outcomes["CAND-RI-4770-4780"]["request_pct"] is None
    assert outcomes["CAND-ME-2023-00336"]["gap_bp"] == 0
    assert outcomes["CAND-CT-22-08-08"]["proposed"] == 0
    assert {r["case_id"] for r in tables["coding"]} == {
        "CAND-NH-24-070",
        "CAND-ME-2023-00336",
        "CAND-VT-26-0096",
    }


def test_long_code_table_reconstructs_case_counts_including_zero_units(payload):
    t = tables_from_payload(payload)
    assert len(t["commission_units"]) == 45 * 3
    for r in t["coding"]:
        units = [
            u
            for u in t["commission_units"]
            if u["case_id"] == r["case_id"] and u["code"] == r["code"]
        ]
        assert len(units) == r["denominator"]
        assert sum(u["stance"] == "Relied on" for u in units) == r["relied"]
        assert sum(u["present"] == 0 for u in units) == r["absent"]
        assert r["relied"] + r["considered"] + r["rejected"] + r["absent"] == r["denominator"]


def test_exact_benchmark_missingness_and_separate_service_rows(payload):
    tables = tables_from_payload(payload)
    rows = tables["benchmark_joins"]
    assert len(rows) == 17 and sum(r["benchmark_pct"] is not None for r in rows) == 9
    assert all(r["benchmark_pct"] is None for r in rows if r["status"] != "matched")
    assert all(r["riders_excluded"] == 1 for r in tables["benchmarks"])
    reconstructed = [
        r for r in tables["benchmarks"] if r["estimation_method"] == "case_level_reconstruction"
    ]
    assert {(r["service"], r["mean_pct"]) for r in reconstructed} == {
        ("Electric", 9.70),
        ("Gas", 9.75),
    }
    joint = [r for r in rows if r["case_id"] == "CAND-MA-23-80-81"]
    assert {r["service"] for r in joint} == {"Electric", "Gas"}


def test_reconstruction_export_retains_full_table_and_reproduces_both_means(payload, tmp_path):
    rows = reconstruction_rows(ROOT, payload)
    assert len(rows) == 126 and sum(r["roe_pct"] is None for r in rows) == 47
    result = write_table(rows, tmp_path / "benchmark_decisions")
    assert result["stata_roundtrip"] == "passed"
    table = pd.read_csv(tmp_path / "benchmark_decisions.csv")
    included = table[table["included_h2"] == 1]
    assert not included["roe_pct"].isna().any() and not included["limited_issue_rider"].any()
    assert included.groupby("service")["roe_pct"].count().to_dict() == {"Electric": 19, "Gas": 23}
    assert included.groupby("service")["roe_pct"].mean().round(2).to_dict() == {
        "Electric": 9.70,
        "Gas": 9.75,
    }
    assert {r["source_page"] for r in rows} == {40, 41}


def test_settlement_benchmarks_preserve_written_report_timing_limit(payload):
    rows = tables_from_payload(payload)["benchmark_comparisons"]
    ri = [r for r in rows if r["case_id"] == "CAND-RI-4770-4780"]
    assert len(ri) == 2 and all(r["award_kind"] == "approved_settlement" for r in ri)
    assert all(
        r["comparison_basis"] == "original_written_date"
        and "when the return was agreed" in r["timing_note"]
        for r in ri
    )
    assert {r["award_minus_benchmark_bp"] for r in ri} == {-42.5, -47.5}


def test_treasury_spread_is_derived_from_matched_nominal_percent_inputs(payload):
    row = next(
        r
        for r in tables_from_payload(payload)["treasury_orders"]
        if r["case_id"] == "CAND-NH-24-070"
    )
    assert row["yield_pct"] == 4.4 and row["award_pct"] == 9.5
    assert row["spread_bp"] == pytest.approx(510)
    p = deepcopy(payload)
    p["treasury"]["joins"][0]["value_fraction"] = None
    changed = tables_from_payload(p)["treasury_orders"][0]
    assert changed["yield_pct"] is None and changed["spread_bp"] is None


def test_csv_and_stata_exports_preserve_missing_zero_precision_and_dates(tmp_path):
    rows = [
        dict(
            case_id="SYNTHETIC-A",
            order_date="2025-01-03",
            gap_bp=0.0,
            award_pct=9.275,
            request_pct=None,
        ),
        dict(
            case_id="SYNTHETIC-B",
            order_date="2025-01-04",
            gap_bp=None,
            award_pct=8.63,
            request_pct=10.2,
        ),
    ]
    report = write_table(rows, tmp_path / "fixture")
    csv = pd.read_csv(tmp_path / "fixture.csv")
    dta = pd.read_stata(tmp_path / "fixture.dta")
    assert report["stata_roundtrip"] == "passed" and report["rows"] == 2
    assert csv.loc[0, "gap_bp"] == 0 and dta.loc[0, "gap_bp"] == 0
    assert pd.isna(csv.loc[1, "gap_bp"]) and pd.isna(dta.loc[1, "gap_bp"])
    assert dta.loc[0, "award_pct"] == 9.275
    assert dta.loc[0, "order_date"] == pd.Timestamp("2025-01-03")


def test_source_audit_rejects_fixture_url_in_production_inventory(payload):
    p = deepcopy(payload)
    p["sources"][0]["source_url"] = "https://example.org/fabricated"
    with pytest.raises(ValueError, match="outside reviewed"):
        source_inventory(ROOT, p, None)


def test_stata_roundtrip_preserves_dates_with_missing_authorization(tmp_path):
    rows = [
        dict(authorized_date="2025-09-30", requested_date="2024-05-06", roe_pct=9.5),
        dict(authorized_date=None, requested_date="2025-03-01", roe_pct=None),
    ]
    report = write_table(rows, tmp_path / "pending_dates")
    assert report["stata_roundtrip"] == "passed"
    saved = pd.read_stata(tmp_path / "pending_dates.dta")
    assert saved.loc[0, "authorized_date"] == pd.Timestamp("2025-09-30")
    assert pd.isna(saved.loc[1, "authorized_date"])


def test_real_source_inventory_verifies_saved_primary_feeds(payload):
    rows = source_inventory(ROOT, payload, load_crosscheck(ROOT))
    assert any(r["source_id"] == "FRED-DGS10" for r in rows)
    assert all(r["check"] == "reviewed_endpoint_and_saved_bytes" for r in rows)
    assert not any(r["host"] in ("example.org", "localhost", "127.0.0.1") for r in rows)


def test_final_sample_flag_changes_only_when_selection_is_finalized(payload):
    p = deepcopy(payload)
    assert not any(r["final_sample"] for r in tables_from_payload(p)["outcomes"])
    p["sample"]["status"] = "finalized"
    rows = tables_from_payload(p)["outcomes"]
    assert all(r["final_sample"] == r["proposed"] for r in rows)
