"""Complete-table, rider and precision checks for the preserved original report."""

from copy import deepcopy
from pathlib import Path

import pymupdf
import pytest

from src.rra_reconstruction import parse_2019_table, reconstruct_2019
from src.research_benchmarks import benchmark_report
from src.research_sample import sample_report

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def report():
    with pymupdf.open(ROOT / "data/external/rra/rra_2020_h1.pdf") as doc:
        yield doc


def test_complete_annual_table_preserves_missing_roe_rows(report):
    rows = parse_2019_table(report)
    assert len(rows) == 126
    assert sum(r["service"] == "Electric" for r in rows) == 63
    assert sum(r["roe_percent"] is None for r in rows) == 47


@pytest.mark.parametrize(
    "service,count,total,mean", [("Electric", 19, "184.23", "9.70"), ("Gas", 23, "224.25", "9.75")]
)
def test_h2_reconstruction_reconciles_with_published_annual_controls(
    report, service, count, total, mean
):
    rows = parse_2019_table(report)
    result = reconstruct_2019(report, rows, service, "2019-07-01", "2019-12-31")
    assert (result["observations"], result["sum_percent"], result["display_percent"]) == (
        count,
        total,
        mean,
    )
    included = [r for r in rows if r["row_id"] in result["included_row_ids"]]
    assert all(not r["limited_issue_rider"] and r["roe_percent"] is not None for r in included)
    assert all("2019-07-01" <= r["decision_date"] <= "2019-12-31" for r in included)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows.pop(),
        lambda rows: rows[0].update(limited_issue_rider=False),
        lambda rows: rows[0].update(roe_percent="9.40"),
        lambda rows: rows.reverse(),
    ],
)
def test_partial_or_recategorized_table_cannot_be_accepted(report, mutation):
    rows = deepcopy(parse_2019_table(report))
    mutation(rows)
    with pytest.raises(ValueError, match="complete original table"):
        reconstruct_2019(report, rows, "Electric", "2019-07-01", "2019-12-31")


def test_reconstruction_does_not_claim_unseen_periods(report):
    with pytest.raises(ValueError, match="Unsupported"):
        reconstruct_2019(report, parse_2019_table(report), "Gas", "2025-01-01", "2025-06-30")


def test_integrated_benchmarks_distinguish_calculated_and_printed_values():
    data = benchmark_report(ROOT, sample_report(ROOT)["candidates"])
    reconstructed = [
        r for r in data["records"] if r.get("estimation_method") == "case_level_reconstruction"
    ]
    assert len(reconstructed) == data["reconstructed_records"] == 2
    assert all(r["printed_percent"] is None for r in reconstructed)
    ri = [r for r in data["joins"] if r["candidate_id"] == "CAND-RI-4770-4780"]
    assert {r["display_percent"] for r in ri} == {"9.70", "9.75"}
    assert all(r["printed_percent"] is None and r["available_at_written_date"] for r in ri)
