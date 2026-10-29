"""M1: register an identified PDF without changing its bytes.

The CSV stores explicitly supplied metadata, an absolute file path,
SHA-256, and the PDF viewer page count. It does not infer research data.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

import pymupdf


FIELDS = (
    "case_id",
    "state",
    "docket",
    "file_path",
    "source_url",
    "download_date",
    "sha256",
    "n_pages",
)
STATES = frozenset({"CT", "MA", "ME", "NH", "RI", "VT"})
CASE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class ManifestError(ValueError):
    """A registration was refused; no research row should be added."""


def _validate_metadata(metadata: dict[str, str]) -> None:
    """Check supplied metadata without guessing replacements.

    These are syntax checks, not verification of the underlying source.
    """
    for key in ("case_id", "state", "docket", "source_url", "download_date"):
        value = metadata.get(key)
        if not isinstance(value, str) or not value or value != value.strip():
            raise ManifestError(f"{key} must be nonempty text without edge whitespace.")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ManifestError(f"{key} must not contain control characters.")
    if metadata["state"] not in STATES:
        raise ManifestError("state must be one of CT, MA, ME, NH, RI, VT.")
    if not CASE_ID_PATTERN.fullmatch(metadata["case_id"]):
        raise ManifestError("case_id must be a safe filename using letters, digits, _, - or .")
    try:
        url = urlsplit(metadata["source_url"])
        valid_url = url.scheme in {"https", "http"} and bool(url.hostname)
    except ValueError as error:
        raise ManifestError(f"Invalid source_url: {error}") from error
    if not valid_url or any(char.isspace() for char in metadata["source_url"]):
        raise ManifestError("source_url must be a complete HTTP(S) URL without spaces.")
    try:
        value = metadata["download_date"]
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("use YYYY-MM-DD")
    except ValueError as error:
        raise ManifestError("download_date must be a real date in YYYY-MM-DD form.") from error


def _pdf_identity(path: Path) -> tuple[str, int]:
    """Hash a byte snapshot and count PDF pages from that same snapshot.

    Refuse unreadable, encrypted, or repair-dependent files rather than guessing.
    """
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ManifestError(f"Cannot read PDF {path}: {error}") from error
    if not content:
        raise ManifestError("PDF is empty.")
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if not document.is_pdf:
                raise ManifestError("Input is not a PDF.")
            if document.needs_pass or document.is_encrypted:
                raise ManifestError("Encrypted PDF is not supported; verify a readable copy.")
            if document.is_repaired:
                raise ManifestError("PDF requires repair; verify a fresh downloaded copy.")
            count = document.page_count
            if count < 1:
                raise ManifestError("PDF has no pages.")
    except (RuntimeError, ValueError) as error:
        if isinstance(error, ManifestError):
            raise
        raise ManifestError(f"Invalid PDF {path}: {error}") from error
    return hashlib.sha256(content).hexdigest(), count


def _manifest_target(path: Path, pdf: Path) -> Path:
    """Resolve a CSV destination outside the protected research directories.

    Reject source aliases and symlink destinations before opening an output.
    """
    path = path.expanduser()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or resolved == pdf
        or (resolved.exists() and pdf.exists() and resolved.samefile(pdf))
    ):
        raise ManifestError("Manifest output must not alias a source or be a symlink.")
    if resolved.suffix.lower() != ".csv":
        raise ManifestError("Manifest output must be a .csv file.")
    for candidate in (path, resolved):
        if {part.lower() for part in candidate.parts} & {"raw_orders", "coding"}:
            raise ManifestError("Manifest output cannot be inside raw_orders/ or coding/.")
    return resolved


def read_manifest(path: Path, *, root: Path | None = None) -> list[dict[str, str]]:
    """Read an existing manifest only if its schema and all rows validate.

    A missing manifest is empty, but an existing empty or corrupt file is an error.
    Restored releases may supply a root for portable, repository-relative paths.
    """
    if not path.exists():
        return []
    rows = []
    seen_hashes, seen_ids = set(), set()
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames != list(FIELDS):
                raise ManifestError(f"Manifest schema must be exactly {','.join(FIELDS)}.")
            for row in reader:
                try:
                    if set(row) != set(FIELDS) or any(value is None for value in row.values()):
                        raise ManifestError("incorrect number of columns")
                    _validate_metadata(row)
                    if not Path(row["file_path"]).is_absolute():
                        if root is None:
                            raise ManifestError("file_path must be absolute")
                        base = Path(root).resolve()
                        if not (base / row["file_path"]).resolve().is_relative_to(base):
                            raise ManifestError("relative file_path escapes the project root")
                    if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                        raise ManifestError("sha256 must be 64 lowercase hexadecimal characters")
                    if not re.fullmatch(r"[1-9][0-9]*", row["n_pages"]):
                        raise ManifestError("n_pages must be a positive integer")
                    if row["sha256"] in seen_hashes or row["case_id"] in seen_ids:
                        raise ManifestError("duplicate sha256 or case_id already in manifest")
                except ManifestError as error:
                    raise ManifestError(
                        f"Invalid manifest row near line {reader.line_num}: {error}"
                    ) from error
                seen_hashes.add(row["sha256"])
                seen_ids.add(row["case_id"])
                rows.append(row)
    except (csv.Error, UnicodeError) as error:
        raise ManifestError(f"Cannot parse manifest: {error}") from error
    return rows


def _atomic_write(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a complete CSV beside its target, then replace the target atomically.

    Clean up a temporary file on failure so an incomplete CSV never replaces it.
    """
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def register_order(
    pdf_path: str | Path,
    *,
    manifest_path: str | Path,
    case_id: str,
    state: str,
    docket: str,
    source_url: str,
    download_date: str,
) -> dict[str, str]:
    """Validate a supplied PDF registration and add one manifest row.

    Return the saved row, or raise ManifestError without modifying the source PDF.
    """
    row = dict(
        case_id=case_id,
        state=state,
        docket=docket,
        source_url=source_url,
        download_date=download_date,
    )
    _validate_metadata(row)
    try:
        pdf = Path(pdf_path).expanduser().resolve()
        target = _manifest_target(Path(manifest_path), pdf)
        digest, pages = _pdf_identity(pdf)
        row.update(file_path=str(pdf), sha256=digest, n_pages=str(pages))
        row = {field: row[field] for field in FIELDS}
        target.parent.mkdir(parents=True, exist_ok=True)
        # Lock a stable sidecar: replacing the CSV must not replace the locked inode.
        with target.with_name(target.name + ".lock").open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            existing = read_manifest(target)
            if any(item["sha256"] == digest for item in existing):
                raise ManifestError("Duplicate SHA-256: this PDF is already registered.")
            if any(item["case_id"] == case_id for item in existing):
                raise ManifestError(f"Duplicate case_id: {case_id} is already registered.")
            _atomic_write(target, [*existing, row])
        return row
    except OSError as error:
        raise ManifestError(f"Registration failed: {error}") from error


def main(argv: list[str] | None = None) -> int:
    """Read explicit command-line inputs and print the row that was saved.

    Return a nonzero exit code with an explanatory message on refused registration.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path", type=Path, help="Existing downloaded PDF; read only")
    parser.add_argument("--manifest", dest="manifest_path", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--state", choices=sorted(STATES), required=True)
    parser.add_argument("--docket", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--download-date", required=True, help="Actual download date: YYYY-MM-DD")
    arguments = parser.parse_args(argv)
    try:
        row = register_order(**vars(arguments))
    except ManifestError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(row, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
