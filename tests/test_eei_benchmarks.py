"""Independent source controls, period boundaries and explicit EEI scope."""

from copy import deepcopy
import csv
from decimal import Decimal
import json
from pathlib import Path

import pytest

from src.eei_benchmarks import (
    AS_OF,
    _number,
    eei_report,
    join_eei_benchmarks,
    read_workbook,
    reconstruct,
    summarize,
    validate_quarters,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def source():
    return eei_report(ROOT)


def test_complete_source_and_published_quarter_controls(source):
    assert source["row_count"] == 2589
    assert source["n_completed"] == 2535
    assert source["n_pending"] == 54
    assert source["n_completed_after_source_as_of"] == 3
    assert len(source["controls"]) == 31
    assert all(c["status"] == "passed" for c in source["controls"])
    assert source["sources"][0]["published_date"] is None
    assert source["sources"][0]["reporting_as_of"] == AS_OF


@pytest.mark.parametrize(
    "period,n,total,display",
    [
        ("2018-H2", 19, "181.35", "9.54"),
        ("2023-H1", 12, "115.70", "9.64"),
        ("2023-H2", 36, "347.88", "9.66"),
        ("2024-H2", 27, "265.32", "9.83"),
        ("2025-H1", 18, "174.23", "9.68"),
    ],
)
def test_exact_half_year_reconstruction(source, period, n, total, display):
    record = next(
        r for r in source["records"] if r["benchmark_id"] == f"EEI-{period}-base_rate_electric"
    )
    assert record["n_observed"] == n
    assert Decimal(record["sum_percent"]) == Decimal(total)
    assert record["display_percent"] == display
    assert Decimal(record["unrounded_percent"]) == Decimal(total) / n
    assert record["riders_excluded"] and record["transmission_excluded"]
    assert record["retrospective"]


def test_annual_counts_and_means_reconcile_to_legacy_controls(source):
    # Control values are independently printed in the original annual reports.
    for year, n, all_mean, base_n, base_mean in (
        (2023, 63, "9.60", 48, "9.66"),
        (2024, 55, "9.74", 41, "9.78"),
    ):
        rows = [
            r
            for r in source["rows"]
            if r["completion_status"] == "Settled" and r["authorized_date"].startswith(str(year))
        ]
        assert summarize(rows)["n_observed"] == n
        assert summarize(rows)["display_percent"] == all_mean
        base = [r for r in rows if r["case_type"] in ("Vertically Integrated", "Distribution")]
        assert summarize(base)["n_observed"] == base_n
        assert summarize(base)["display_percent"] == base_mean


def test_missing_values_do_not_become_zero_or_enter_the_denominator(source):
    period = next(
        r for r in source["records"] if r["benchmark_id"] == "EEI-2024-H2-base_rate_electric"
    )
    assert period["n_decisions"] == 39
    assert period["n_missing"] == 12
    assert period["n_observed"] == 27
    assert not set(period["included_source_rows"]) & set(period["missing_source_rows"])
    with pytest.raises(ValueError, match="non-positive"):
        _number(Decimal(0), "Q4")


def test_retrospective_join_never_falls_back_to_gas_or_a_future_half_year(source):
    candidates = [
        dict(candidate_id="JOINT", services=["Electric", "Gas"], order_date="2025-01-01"),
        dict(candidate_id="AFTER", services=["Electric"], order_date="2026-08-28"),
    ]
    joins = join_eei_benchmarks(candidates, source["records"])
    assert joins[0]["display_percent"] == "9.83"
    assert joins[0]["status"] == "matched_retrospective_context"
    assert joins[0]["available_at_written_date"] is None
    assert joins[0]["published_date"] is None
    assert joins[1]["benchmark_id"] is None
    assert joins[2]["benchmark_id"] is None


def test_deleted_observation_fails_independent_quarter_control(source):
    bad = [r for r in source["rows"] if r["source_row"] != 135]
    with pytest.raises(ValueError, match="observation count"):
        validate_quarters(bad, source["controls"])


def test_changed_roe_fails_independent_quarter_control(source):
    bad = deepcopy(source["rows"])
    next(r for r in bad if r["source_row"] == 135)["authorized_roe_percent"] = "9.36"
    with pytest.raises(ValueError, match="quarterly mean"):
        validate_quarters(bad, source["controls"])


def test_pending_status_and_transmission_case_do_not_enter_base_mean(source):
    bad = deepcopy(source["rows"])
    target = next(r for r in bad if r["source_row"] == 43)
    assert target["case_type"] == "Transmission"
    before = next(
        r for r in reconstruct(bad) if r["benchmark_id"] == "EEI-2025-H1-base_rate_electric"
    )
    target["authorized_roe_percent"] = "20.00"
    after = next(r for r in reconstruct(bad) if r["benchmark_id"] == before["benchmark_id"])
    assert after == before
    target["case_type"] = "Distribution"
    target["completion_status"] = "Pending"
    pending = next(r for r in reconstruct(bad) if r["benchmark_id"] == before["benchmark_id"])
    assert pending["included_source_rows"] == before["included_source_rows"]
    assert pending["sum_percent"] == before["sum_percent"]
    assert pending["n_observed"] == before["n_observed"]


def test_binary_serialization_is_normalized_without_discarding_real_precision():
    assert _number(Decimal("9.6999999999999993"), "Q4") == "9.70"
    with pytest.raises(ValueError, match="precision"):
        _number(Decimal("9.701"), "Q4")


def test_changed_original_workbook_is_rejected(tmp_path):
    path = tmp_path / "changed.xlsx"
    path.write_bytes(b"not the original source")
    with pytest.raises(ValueError, match="fingerprint"):
        read_workbook(path)


def test_exported_observations_equal_original_source_reconstruction(source):
    path = ROOT / "data/external/eei/electric_observations.csv"
    with path.open(newline="") as stream:
        exported = list(csv.DictReader(stream))
    expected = [
        {key: "" if value is None else str(value) for key, value in row.items()}
        for row in source["rows"]
    ]
    assert exported == expected


def test_exported_benchmark_report_has_not_drifted(source):
    path = ROOT / "data/external/eei/reconstruction.json"
    exported = json.loads(path.read_text())
    assert exported == {key: value for key, value in source.items() if key != "rows"}
