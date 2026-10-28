"""M2 tests use synthetic PDFs, not human-coded research passages."""

import json
from pathlib import Path
import subprocess
import sys

import pymupdf
import pytest

from src.extract_text import ExtractionError, extract_case
from src.manifest import register_order


@pytest.fixture
def registered(tmp_path):
    pdf = tmp_path / "source.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "Synthetic page one.\nLine-break hyphen-\nation is preserved.")
        page.insert_text((72, 700), "1 Footnote on the first PDF page.", fontsize=9)
        page = doc.new_page()
        page.insert_text((72, 72), "Short.")
        doc.new_page()
        doc.set_page_labels([{"startpage": 0, "prefix": "", "style": "r", "firstpagenum": 1}])
        doc.save(pdf)
    manifest = tmp_path / "manifest.csv"
    register_order(
        pdf,
        manifest_path=manifest,
        case_id="TEST-M2",
        state="VT",
        docket="SYNTHETIC",
        source_url="https://example.org/test.pdf",
        download_date="2026-09-29",
    )
    return dict(
        manifest_path=manifest, case_id="TEST-M2", output_dir=tmp_path / "text", min_text_chars=10
    ), pdf


def test_one_row_per_viewer_page_preserving_text_footnotes_and_source(registered):
    args, pdf = registered
    before = pdf.read_bytes(), pdf.stat().st_mtime_ns, args["manifest_path"].read_bytes()
    with pymupdf.open(pdf) as doc:
        expected = [page.get_text("text", sort=False) for page in doc]
    summary = extract_case(**args)
    rows = json.loads(Path(summary["output_path"]).read_text())
    assert [row["page"] for row in rows] == [1, 2, 3]
    assert [row["text"] for row in rows] == expected
    assert [row["n_chars"] for row in rows] == [len(text) for text in expected]
    assert all(set(row) == {"page", "text", "n_chars", "likely_scanned"} for row in rows)
    assert [row["likely_scanned"] for row in rows] == [False, True, True]
    assert "Footnote" in rows[0]["text"]
    assert "hyphen-\nation" in rows[0]["text"]
    assert summary["flagged_pages"] == [2, 3]
    assert summary["ocr_pages"] == []
    assert (pdf.read_bytes(), pdf.stat().st_mtime_ns, args["manifest_path"].read_bytes()) == before


def test_threshold_is_strict_and_counts_nonwhitespace(registered):
    args, _ = registered
    args["min_text_chars"] = 6
    summary = extract_case(**args)
    rows = json.loads(Path(summary["output_path"]).read_text())
    assert rows[1]["text"].strip() == "Short."
    assert rows[1]["likely_scanned"] is False
    assert rows[2]["likely_scanned"] is True


def test_ocr_is_never_called_without_flag(registered, monkeypatch):
    args, _ = registered

    def unexpected(*a, **kw):
        pytest.fail("OCR ran without explicit authorization")

    monkeypatch.setattr("src.extract_text._ocr_page", unexpected)
    extract_case(**args)


def test_explicit_ocr_only_runs_on_flagged_pages_and_flag_remains(
    registered, monkeypatch, tmp_path
):
    args, _ = registered
    data = tmp_path / "tessdata"
    data.mkdir()
    (data / "eng.traineddata").write_bytes(b"mock language data")
    calls = []

    def recognize(page, **kwargs):
        calls.append(page.number + 1)
        return "OCR candidate wording\n" if page.number == 1 else ""

    monkeypatch.setattr("src.extract_text._ocr_page", recognize)
    summary = extract_case(**args, ocr=True, tessdata_dir=data)
    rows = json.loads(Path(summary["output_path"]).read_text())
    assert calls == [2, 3]
    assert summary["ocr_pages"] == [2, 3]
    assert rows[1] == dict(page=2, text="OCR candidate wording\n", n_chars=22, likely_scanned=True)
    assert rows[2]["text"] == ""


def test_missing_ocr_data_fails_without_creating_output(registered):
    args, _ = registered
    with pytest.raises(ExtractionError, match="tessdata"):
        extract_case(**args, ocr=True)
    assert not args["output_dir"].exists()


def test_ocr_failure_never_leaves_partial_output(registered, monkeypatch, tmp_path):
    args, _ = registered
    data = tmp_path / "tessdata"
    data.mkdir()
    (data / "eng.traineddata").write_bytes(b"mock")

    def fail(*a, **kw):
        raise RuntimeError("OCR unavailable")

    monkeypatch.setattr("src.extract_text._ocr_page", fail)
    with pytest.raises(ExtractionError, match="page 2"):
        extract_case(**args, ocr=True, tessdata_dir=data)
    assert not (args["output_dir"] / "TEST-M2.json").exists()


def test_changed_pdf_hash_is_rejected(registered):
    args, pdf = registered
    pdf.write_bytes(pdf.read_bytes() + b"\n% changed after registration\n")
    with pytest.raises(ExtractionError, match="SHA-256"):
        extract_case(**args)
    assert not args["output_dir"].exists()


def test_wrong_manifest_page_count_is_rejected(registered):
    args, _ = registered
    manifest = args["manifest_path"]
    manifest.write_text(manifest.read_text().replace(",3\n", ",4\n"))
    with pytest.raises(ExtractionError, match="page count"):
        extract_case(**args)


@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_bad_threshold_is_rejected(registered, value):
    args, _ = registered
    args["min_text_chars"] = value
    with pytest.raises(ExtractionError, match="min_text_chars"):
        extract_case(**args)


def test_unknown_case_is_rejected(registered):
    args, _ = registered
    args["case_id"] = "MISSING"
    with pytest.raises(ExtractionError, match="not found"):
        extract_case(**args)


@pytest.mark.parametrize("folder", ["raw_orders", "coding", "project_docs", "codebook"])
def test_protected_output_locations_are_rejected(registered, tmp_path, folder):
    args, _ = registered
    args["output_dir"] = tmp_path / folder
    with pytest.raises(ExtractionError, match="protected"):
        extract_case(**args)
    assert not args["output_dir"].exists()


@pytest.mark.parametrize("identifier", ["../escape", "/absolute", "nested/id", "..", "a\\b"])
def test_case_id_cannot_escape_output_directory(registered, identifier):
    args, _ = registered
    manifest = args["manifest_path"]
    manifest.write_text(manifest.read_text().replace("TEST-M2", identifier))
    args["case_id"] = identifier
    with pytest.raises(ExtractionError, match="case_id"):
        extract_case(**args)


def test_existing_output_is_never_overwritten(registered):
    args, _ = registered
    args["output_dir"].mkdir()
    target = args["output_dir"] / "TEST-M2.json"
    target.write_text("existing reviewed output")
    with pytest.raises(ExtractionError, match="exists"):
        extract_case(**args)
    assert target.read_text() == "existing reviewed output"


def test_symlink_to_source_is_never_overwritten(registered):
    args, pdf = registered
    args["output_dir"].mkdir()
    (args["output_dir"] / "TEST-M2.json").symlink_to(pdf)
    before = pdf.read_bytes()
    with pytest.raises(ExtractionError):
        extract_case(**args)
    assert pdf.read_bytes() == before


def test_atomic_publish_failure_leaves_no_output(registered, monkeypatch):
    args, _ = registered

    def fail(*a, **kw):
        raise OSError("simulated publication failure")

    monkeypatch.setattr("src.extract_text.os.link", fail)
    with pytest.raises(ExtractionError, match="publication failure"):
        extract_case(**args)
    assert not list(args["output_dir"].iterdir())


def test_cli_selects_manifest_row_and_prints_audit_summary(registered):
    args, _ = registered
    command = [
        sys.executable,
        "-m",
        "src.extract_text",
        "--manifest",
        str(args["manifest_path"]),
        "--case-id",
        args["case_id"],
        "--output-dir",
        str(args["output_dir"]),
        "--min-text-chars",
        "10",
    ]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    summary = json.loads(first.stdout)
    assert summary["n_pages"] == 3
    assert summary["min_text_chars"] == 10
    assert summary["ocr_requested"] is False
    assert Path(summary["output_path"]).exists()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2
    assert "exists" in second.stderr
