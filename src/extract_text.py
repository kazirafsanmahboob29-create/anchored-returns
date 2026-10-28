"""M2: extract a registered PDF to page-numbered JSON without classifying text."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

import pymupdf

from .manifest import CASE_ID_PATTERN, ManifestError, read_manifest


class ExtractionError(ValueError):
    """Extraction was refused; no incomplete or replacement output is published."""


def _output_target(output_dir: Path, case_id: str) -> Path:
    """Build a safe case filename outside source and coding directories.

    Refuse existing outputs, including symlinks, so reviewed text is preserved.
    """
    if not CASE_ID_PATTERN.fullmatch(case_id):
        raise ExtractionError("case_id must be a safe filename using letters, digits, _, - or .")
    directory = output_dir.expanduser()
    resolved = directory.resolve()
    protected = {
        "raw_orders",
        "practice_orders",
        "coding",
        "project_docs",
        "codebook",
        "literature",
    }
    if any(set(part.lower() for part in path.parts) & protected for path in (directory, resolved)):
        raise ExtractionError("Output directory is protected source or coding material.")
    target = resolved / f"{case_id}.json"
    if target.exists() or target.is_symlink():
        raise ExtractionError(f"Output already exists: {target}. Use a new output directory.")
    return target


def _ocr_page(page: pymupdf.Page, *, tessdata_dir: Path, language: str, dpi: int) -> str:
    """Recognize one explicitly selected low-text page using local Tesseract data.

    Preserve readable native text and recognize the remaining page image areas.
    """
    textpage = page.get_textpage_ocr(
        language=language,
        dpi=dpi,
        full=False,
        tessdata=str(tessdata_dir),
    )
    return page.get_text("text", textpage=textpage, sort=False)


def _publish_json(target: Path, rows: list[dict]) -> None:
    """Publish a complete UTF-8 JSON file without replacing an existing file.

    A same-directory hard link makes publication atomic on the local filesystem.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(rows, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def extract_case(
    manifest_path: str | Path,
    *,
    case_id: str,
    output_dir: str | Path,
    min_text_chars: int,
    ocr: bool = False,
    tessdata_dir: str | Path | None = None,
    ocr_language: str = "eng",
    ocr_dpi: int = 300,
) -> dict:
    """Verify a manifest-selected PDF and extract one record per viewer page.

    Return an audit summary; keep the output page schema exactly as specified in M2.
    """
    if type(min_text_chars) is not int or min_text_chars < 1:
        raise ExtractionError("min_text_chars must be a positive integer.")
    target = _output_target(Path(output_dir), case_id)
    if ocr:
        if tessdata_dir is None:
            raise ExtractionError("Explicit OCR requires --tessdata-dir with local language data.")
        tessdata_dir = Path(tessdata_dir).expanduser().resolve()
        if not re.fullmatch(r"[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*", ocr_language):
            raise ExtractionError("ocr_language must name one or more language codes, e.g. eng.")
        for language in ocr_language.split("+"):
            if not (tessdata_dir / f"{language}.traineddata").is_file():
                raise ExtractionError(f"Missing tessdata language file: {language}.traineddata")
        if type(ocr_dpi) is not int or ocr_dpi < 1:
            raise ExtractionError("ocr_dpi must be a positive integer.")
    elif tessdata_dir is not None:
        raise ExtractionError("tessdata_dir was supplied without the explicit OCR flag.")
    try:
        manifest_path = Path(manifest_path).expanduser().resolve()
        if not manifest_path.is_file():
            raise ExtractionError(f"Manifest not found: {manifest_path}")
        matches = [row for row in read_manifest(manifest_path) if row["case_id"] == case_id]
        if len(matches) != 1:
            raise ExtractionError(f"case_id not found in manifest: {case_id}")
        row = matches[0]
        pdf = Path(row["file_path"])
        content = pdf.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != row["sha256"]:
            raise ExtractionError(
                "PDF SHA-256 differs from its registered fingerprint; source changed."
            )
        pages, flagged, recognized = [], [], []
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if (
                not document.is_pdf
                or document.needs_pass
                or document.is_encrypted
                or document.is_repaired
            ):
                raise ExtractionError("PDF is invalid, encrypted, or requires repair.")
            if document.page_count != int(row["n_pages"]):
                raise ExtractionError("PDF page count differs from the manifest.")
            for number, page in enumerate(document, start=1):
                try:
                    text = page.get_text("text", sort=False)
                    low_text = sum(not char.isspace() for char in text) < min_text_chars
                    if low_text:
                        flagged.append(number)
                    if low_text and ocr:
                        text = _ocr_page(
                            page, tessdata_dir=tessdata_dir, language=ocr_language, dpi=ocr_dpi
                        )
                        recognized.append(number)
                    pages.append(
                        dict(page=number, text=text, n_chars=len(text), likely_scanned=low_text)
                    )
                except (RuntimeError, ValueError) as error:
                    raise ExtractionError(
                        f"Extraction failed on PDF page {number}: {error}"
                    ) from error
        _publish_json(target, pages)
        return dict(
            case_id=case_id,
            source_path=str(pdf),
            source_sha256=digest,
            output_path=str(target),
            output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            n_pages=len(pages),
            min_text_chars=min_text_chars,
            threshold_metric="non-whitespace native-text characters; flag when below threshold",
            flagged_pages=flagged,
            ocr_requested=ocr,
            ocr_pages=recognized,
            ocr_language=ocr_language if ocr else None,
            ocr_dpi=ocr_dpi if ocr else None,
            pymupdf_version=pymupdf.VersionBind,
            extracted_at_utc=datetime.now(timezone.utc).isoformat(),
        )
    except ExtractionError:
        raise
    except (ManifestError, OSError, RuntimeError, ValueError) as error:
        raise ExtractionError(f"Extraction failed: {error}") from error


def main(argv: list[str] | None = None) -> int:
    """Read explicit paths, a case ID, and a low-text threshold from the CLI.

    Print a JSON audit summary or exit with a clear error on refused extraction.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", dest="manifest_path", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-text-chars", type=int, required=True)
    parser.add_argument("--ocr", action="store_true", help="OCR flagged pages only; never implicit")
    parser.add_argument("--tessdata-dir", type=Path)
    parser.add_argument("--ocr-language", default="eng")
    parser.add_argument("--ocr-dpi", type=int, default=300)
    try:
        summary = extract_case(**vars(parser.parse_args(argv)))
    except ExtractionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
