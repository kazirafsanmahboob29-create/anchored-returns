"""Document checks should work in a restored clone, from any working directory."""

import csv
import hashlib
import json

import pymupdf
import pytest

from src import research
from src.manifest import FIELDS


@pytest.fixture
def evidence(tmp_path):
    root = tmp_path / "project"
    pdf = root / "data/orders/example.pdf"
    pdf.parent.mkdir(parents=True)
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "A synthetic page used only to test document validation.")
        doc.save(pdf)
    with pymupdf.open(pdf) as doc:
        text = doc[0].get_text("text", sort=False)
    source = {
        "source_id": "TEST-MA-001",
        "pdf_path": "data/orders/example.pdf",
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "n_pages": 1,
        "state": "MA",
        "docket": "TEST-001",
        "source_url": "https://example.org/test.pdf",
        "download_date": "2026-10-28",
    }
    record = {key: source[key] for key in ("state", "docket", "source_url", "download_date")}
    record.update(
        case_id=source["source_id"],
        file_path=source["pdf_path"],
        sha256=source["pdf_sha256"],
        n_pages=1,
    )
    with (root / "data/empirical_manifest.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(record)
    text_path = root / "data/empirical_text/TEST-MA-001.json"
    text_path.parent.mkdir()
    text_path.write_text(
        json.dumps(
            [
                {
                    "page": 1,
                    "text": text,
                    "n_chars": len(text),
                    "likely_scanned": len("".join(text.split())) < 80,
                }
            ]
        )
    )
    return root, source, pdf, text_path


def test_native_pages_are_resolved_from_project_root(evidence, monkeypatch, tmp_path):
    root, source, _, _ = evidence
    monkeypatch.chdir(tmp_path)
    assert research.verify_native_text(root, [source]) == 1


def test_changed_pdf_is_rejected(evidence):
    root, source, pdf, _ = evidence
    pdf.write_bytes(pdf.read_bytes() + b"\nchanged")
    with pytest.raises(ValueError, match="fingerprint changed"):
        research.verify_native_text(root, [source])


def test_changed_saved_text_is_rejected(evidence):
    root, source, _, text_path = evidence
    saved = json.loads(text_path.read_text())
    saved[0]["text"] = "Different text"
    text_path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="no longer reproduces"):
        research.verify_native_text(root, [source])


def test_relative_paths_cannot_escape_project(evidence):
    root, source, _, _ = evidence
    path = root / "data/empirical_manifest.csv"
    path.write_text(path.read_text().replace(source["pdf_path"], "../outside.pdf"))
    with pytest.raises(ValueError, match="escapes the project root"):
        research.verify_native_text(root, [source])


def test_missing_manifest_is_not_a_successful_full_check(evidence):
    root, source, _, _ = evidence
    (root / "data/empirical_manifest.csv").unlink()
    with pytest.raises(ValueError, match="manifest is missing"):
        research.verify_native_text(root, [source])


def test_full_check_does_not_require_development_archive(evidence, monkeypatch):
    root, source, _, _ = evidence
    payload = {
        "stats": {"documents": 1, "facts": 0},
        "sample": {},
        "benchmarks": {},
        "reliability": {},
        "sources": [source],
    }
    monkeypatch.setattr(research, "overview_payload", lambda path: payload)
    monkeypatch.setattr(research, "validate_ledger", lambda *a, **k: {"n_new_numeric_facts": 0})
    monkeypatch.setattr(research, "load_crosscheck", lambda path: None)
    assert research.check(root, full=True)["empirical_native_pages_recomputed"] == 1


def test_legacy_audit_explains_its_missing_inputs(monkeypatch, tmp_path):
    from scripts import audit_project

    monkeypatch.setattr(audit_project, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="original development workspace"):
        audit_project.audit()
