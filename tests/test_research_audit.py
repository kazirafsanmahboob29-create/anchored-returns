"""Synthetic files exercise context access contracts, not research values."""

import json
from pathlib import Path

import pymupdf
import pytest

from src.research_audit import source_audit
from src.research_ledger import fingerprint


@pytest.fixture
def context_root(tmp_path):
    (tmp_path / "data/external").mkdir(parents=True)
    (tmp_path / "data/research").mkdir(parents=True)
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), "SYNTHETIC CONTEXT SOURCE FIXTURE")
        pdf.save(tmp_path / "source.pdf")
    source = dict(
        status="context_only",
        source_url="https://documents.dps.ny.gov/public/test-fixture",
        pdf_path="source.pdf",
        pdf_sha256=fingerprint(tmp_path / "source.pdf"),
        n_pages=1,
        page=1,
    )
    (tmp_path / "data/external/rra_context_sources.json").write_text(
        json.dumps({"sources": [source]})
    )
    (tmp_path / "data/research/sample_screening.json").write_text(
        json.dumps(
            dict(
                considered_local_candidates=[], state_census_complete={}, unresolved_search_leads=[]
            )
        )
    )
    return tmp_path


def audit(root):
    return source_audit(
        root,
        dict(sources=[], n_documents=0),
        None,
        dict(verified_half_years=[]),
        dict(status="packet_not_built"),
    )


def test_context_sources_do_not_change_benchmark_or_census_coverage(context_root):
    report = audit(context_root)
    assert len(report["context_sources"]) == 1
    assert report["census_complete"] == 0 and report["independent_ratings"]["agreement"] is None
    assert report["connections"][-1]["verified_half_years"] == []


@pytest.mark.parametrize(
    "key,value,message",
    [
        ("status", "verified_half_year", "cannot become"),
        ("source_url", "https://example.org/fabricated", "outside reviewed"),
        ("source_url", "javascript:alert(1)", "outside reviewed"),
        ("pdf_sha256", "changed", "fingerprint changed"),
        ("page", 2, "page count"),
    ],
)
def test_context_checks_reject_misclassification_wrong_hosts_and_changed_bytes(
    context_root, key, value, message
):
    p = context_root / "data/external/rra_context_sources.json"
    data = json.loads(p.read_text())
    data["sources"][0][key] = value
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=message):
        audit(context_root)
