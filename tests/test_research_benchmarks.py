"""Time boundaries, scope integrity and explicit benchmark missingness."""

import copy
import json

import pymupdf
import pytest

from src.research_benchmarks import previous_half_year, join_benchmarks, benchmark_report
from src.research_ledger import fingerprint


@pytest.mark.parametrize(
    "day,expected",
    [
        ("2025-01-01", ("2024-07-01", "2024-12-31")),
        ("2025-06-30", ("2024-07-01", "2024-12-31")),
        ("2025-07-01", ("2025-01-01", "2025-06-30")),
        ("2024-02-29", ("2023-07-01", "2023-12-31")),
    ],
)
def test_previous_completed_half_year_boundary(day, expected):
    assert previous_half_year(day) == expected


def record(service="Electric", published="2025-07-20"):
    return dict(
        benchmark_id="TEST-" + service,
        service=service,
        period_start="2025-01-01",
        period_end="2025-06-30",
        printed_percent="9.45",
        value_fraction="0.0945",
        published_date=published,
    )


def test_joint_order_requires_separate_service_matches_without_duplication():
    cases = [dict(candidate_id="TEST", services=["Electric", "Gas"], order_date="2025-07-01")]
    matches = join_benchmarks(cases, [record()])
    assert len(matches) == 2 and {j["candidate_id"] for j in matches} == {"TEST"}
    assert matches[0]["available_at_written_date"] is False
    assert (
        matches[1]["status"] == "missing_exact_comparable_half_year"
        and matches[1]["value_fraction"] is None
    )


def test_no_annual_service_or_adjacent_half_year_fallback():
    r = record()
    r.update(period_start="2024-01-01", period_end="2024-12-31")
    cases = [dict(candidate_id="TEST", services=["Gas"], order_date="2025-07-10")]
    assert join_benchmarks(cases, [r, record()])[0]["benchmark_id"] is None
    with pytest.raises(ValueError, match="Ambiguous"):
        join_benchmarks(cases, [r, r])


@pytest.fixture
def benchmark_bundle(tmp_path):
    directory = tmp_path / "data/external"
    directory.mkdir(parents=True)
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((72, 72), "SYNTHETIC\nGeneral rate cases 9.45")
    pdf = tmp_path / "source.pdf"
    doc.save(pdf)
    text = doc[0].get_text("text", sort=False)
    doc.close()
    image = tmp_path / "visual.png"
    image.write_bytes(b"SYNTHETIC VISUAL FINGERPRINT")
    r = record()
    r.update(
        source_id="SRC",
        riders_excluded=True,
        statistic="mean_authorized_roe",
        dataset_version="legacy_major_rate_case_coverage",
        evidence=dict(page=1, start_char=0, end_char=len(text), exact_text=text),
        visual_check=dict(
            page=1,
            path="visual.png",
            sha256=fingerprint(image),
            reviewer="Synthetic reviewer",
            checked_date="2025-08-01",
        ),
    )
    source = dict(
        source_id="SRC",
        pdf_path="source.pdf",
        pdf_sha256=fingerprint(pdf),
        n_pages=1,
        published_date="2025-07-20",
        data_compiled_date="2025-07-18",
    )
    data = dict(checked_date="2025-08-01", records=[r], sources=[source], unresolved_sources=[])
    return tmp_path, data


def validate(bundle, data=None):
    root, original = bundle
    (root / "data/external/rra_historical_benchmarks.json").write_text(json.dumps(data or original))
    return benchmark_report(
        root, [dict(candidate_id="TEST", services=["Electric"], order_date="2025-08-01")]
    )


def test_real_pdf_evidence_validation(benchmark_bundle):
    assert validate(benchmark_bundle)["orders_with_all_services_matched"] == 1


@pytest.mark.parametrize(
    "mutation,message",
    [
        (lambda d: d["records"][0].update(riders_excluded=False), "exclude riders"),
        (lambda d: d["records"][0].update(value_fraction="9.45"), "conversion"),
        (lambda d: d["records"][0].update(dataset_version="enhanced"), "dataset version"),
        (lambda d: d["records"][0].update(period_end="2025-12-31"), "complete half-year"),
        (lambda d: d["records"][0]["evidence"].update(exact_text="invented"), "evidence differs"),
        (lambda d: d["sources"][0].update(published_date="2025-07-21"), "vintage differs"),
        (
            lambda d: d["records"][0]["visual_check"].update(checked_date="2025-08-02"),
            "future benchmark",
        ),
    ],
)
def test_rejects_unusable_benchmark_evidence(benchmark_bundle, mutation, message):
    data = copy.deepcopy(benchmark_bundle[1])
    mutation(data)
    with pytest.raises(ValueError, match=message):
        validate(benchmark_bundle, data)
