"""M1 contract tests. All PDFs and case metadata here are synthetic."""

import csv
import hashlib
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from src.manifest import FIELDS, ManifestError, register_order


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "synthetic.pdf"
    with pymupdf.open() as document:
        for number in range(3):
            page = document.new_page()
            page.insert_text((72, 72), f"SYNTHETIC TEST ONLY. Page {number + 1}.")
        document.save(path)
    return path


@pytest.fixture
def inputs(tmp_path, pdf):
    return dict(
        pdf_path=pdf,
        manifest_path=tmp_path / "data" / "manifest.csv",
        case_id="TEST-01",
        state="VT",
        docket="SYNTHETIC-DOCKET",
        source_url="https://example.org/synthetic.pdf",
        download_date="2026-09-29",
    )


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(FIELDS)
        return list(reader)


def test_registers_exact_metadata_hash_and_pages_without_touching_pdf(inputs, pdf):
    before = pdf.read_bytes(), pdf.stat().st_mtime_ns
    row = register_order(**inputs)
    expected = {
        "case_id": "TEST-01",
        "state": "VT",
        "docket": "SYNTHETIC-DOCKET",
        "file_path": str(pdf.resolve()),
        "source_url": "https://example.org/synthetic.pdf",
        "download_date": "2026-09-29",
        "sha256": hashlib.sha256(before[0]).hexdigest(),
        "n_pages": "3",
    }
    assert row == expected
    assert read_rows(inputs["manifest_path"]) == [expected]
    assert (pdf.read_bytes(), pdf.stat().st_mtime_ns) == before


@pytest.mark.parametrize("renamed", [False, True])
def test_rejects_same_content_even_with_new_id_and_filename(inputs, pdf, renamed):
    register_order(**inputs)
    before = inputs["manifest_path"].read_bytes()
    if renamed:
        copy = pdf.with_name("renamed.pdf")
        copy.write_bytes(pdf.read_bytes())
        inputs["pdf_path"] = copy
    inputs["case_id"] = "TEST-02"
    with pytest.raises(ManifestError, match="[Dd]uplicate SHA-256"):
        register_order(**inputs)
    assert inputs["manifest_path"].read_bytes() == before


def test_rejects_duplicate_case_id_for_different_pdf(inputs, pdf):
    register_order(**inputs)
    before = inputs["manifest_path"].read_bytes()
    with pymupdf.open() as document:
        document.new_page()
        document.save(pdf.with_name("different.pdf"))
    inputs["pdf_path"] = pdf.with_name("different.pdf")
    with pytest.raises(ManifestError, match="[Dd]uplicate case_id"):
        register_order(**inputs)
    assert inputs["manifest_path"].read_bytes() == before


def test_appends_and_preserves_existing_records(inputs, pdf):
    first = register_order(**inputs)
    with pymupdf.open() as document:
        document.new_page()
        document.save(pdf.with_name("second.pdf"))
    inputs.update(case_id="TEST-02", pdf_path=pdf.with_name("second.pdf"))
    second = register_order(**inputs)
    assert read_rows(inputs["manifest_path"]) == [first, second]


@pytest.mark.parametrize(
    "field,value",
    [
        ("state", "NY"),
        ("state", "vt"),
        ("case_id", ""),
        ("docket", " "),
        ("case_id", " TEST-01"),
        ("docket", "test\ncase"),
        ("case_id", "../escape"),
        ("case_id", "a/b"),
        ("case_id", "has space"),
        ("source_url", "not a URL"),
        ("source_url", "file:///tmp/source.pdf"),
        ("source_url", "https://"),
        ("download_date", "2026-02-30"),
        ("download_date", "09/29/2026"),
        ("download_date", "20260929"),
    ],
)
def test_invalid_metadata_does_not_create_manifest(inputs, field, value):
    inputs[field] = value
    with pytest.raises(ManifestError):
        register_order(**inputs)
    assert not inputs["manifest_path"].exists()


@pytest.mark.parametrize("payload", [b"", b"<html>Download error</html>", b"%PDF-1.7\nbroken"])
def test_invalid_pdf_does_not_create_manifest(inputs, pdf, payload):
    pdf.write_bytes(payload)
    with pytest.raises(ManifestError, match="PDF"):
        register_order(**inputs)
    assert not inputs["manifest_path"].exists()
    assert pdf.read_bytes() == payload


def test_missing_pdf_does_not_create_manifest(inputs, pdf):
    pdf.unlink()
    with pytest.raises(ManifestError, match="PDF"):
        register_order(**inputs)
    assert not inputs["manifest_path"].exists()


def test_encrypted_pdf_is_rejected(inputs, pdf):
    protected = pdf.with_name("encrypted.pdf")
    with pymupdf.open(pdf) as document:
        document.save(
            protected, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="test", owner_pw="owner"
        )
    inputs["pdf_path"] = protected
    with pytest.raises(ManifestError, match="[Ee]ncrypted"):
        register_order(**inputs)
    assert not inputs["manifest_path"].exists()


def test_repair_dependent_pdf_is_rejected(inputs, pdf):
    original = pdf.read_bytes()
    pdf.write_bytes(original[: original.index(b"xref\n")])
    with pymupdf.open(pdf) as document:
        assert document.is_repaired
    with pytest.raises(ManifestError, match="repair"):
        register_order(**inputs)
    assert not inputs["manifest_path"].exists()


@pytest.mark.parametrize(
    "target",
    [
        "data/raw_orders/VT/manifest.csv",
        "data/coding/manifest.csv",
        "coding.xlsx",
    ],
)
def test_output_cannot_target_raw_orders_or_coding_sheet(inputs, tmp_path, target):
    inputs["manifest_path"] = tmp_path / target
    with pytest.raises(ManifestError):
        register_order(**inputs)
    assert not inputs["manifest_path"].exists()


def test_output_cannot_alias_pdf(inputs, pdf):
    inputs["manifest_path"] = pdf.with_suffix(".csv")
    inputs["manifest_path"].symlink_to(pdf)
    before = pdf.read_bytes()
    with pytest.raises(ManifestError):
        register_order(**inputs)
    assert pdf.read_bytes() == before


@pytest.mark.parametrize("contents", ["", "wrong,header\nvalue,other\n"])
def test_invalid_existing_manifest_is_not_overwritten(inputs, contents):
    path = inputs["manifest_path"]
    path.parent.mkdir(parents=True)
    path.write_text(contents)
    with pytest.raises(ManifestError, match="schema"):
        register_order(**inputs)
    assert path.read_text() == contents


def test_malformed_existing_row_is_not_overwritten(inputs):
    register_order(**inputs)
    path = inputs["manifest_path"]
    with path.open("a") as handle:
        handle.write("incomplete,row\n")
    before = path.read_bytes()
    with pytest.raises(ManifestError, match="row"):
        register_order(**inputs)
    assert path.read_bytes() == before


def test_failed_atomic_replace_preserves_manifest(inputs, monkeypatch):
    path = inputs["manifest_path"]
    path.parent.mkdir(parents=True)
    path.write_text(",".join(FIELDS) + "\n")
    before = path.read_bytes()

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr("src.manifest.os.replace", fail)
    with pytest.raises(ManifestError, match="simulated disk failure"):
        register_order(**inputs)
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.tmp"))


def test_cli_and_duplicate_exit_status(inputs, pdf):
    command = [sys.executable, "-m", "src.manifest", str(pdf)]
    for name in ("manifest_path", "case_id", "state", "docket", "source_url", "download_date"):
        flag = "--manifest" if name == "manifest_path" else "--" + name.replace("_", "-")
        command.extend([flag, str(inputs[name])])
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode != 0
    assert "Duplicate SHA-256" in second.stderr
    assert len(read_rows(inputs["manifest_path"])) == 1


def test_simultaneous_registrations_cannot_both_add_same_pdf(inputs, pdf):
    command = [
        sys.executable,
        "-m",
        "src.manifest",
        str(pdf),
        "--manifest",
        str(inputs["manifest_path"]),
        "--case-id",
        "TEST-01",
        "--state",
        "VT",
        "--docket",
        "SYNTHETIC",
        "--source-url",
        "https://example.org/test.pdf",
        "--download-date",
        "2026-09-29",
    ]
    processes = [
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(2)
    ]
    outputs = [process.communicate(timeout=30) for process in processes]
    assert sorted(process.returncode for process in processes) == [0, 2], outputs
    assert len(read_rows(inputs["manifest_path"])) == 1
