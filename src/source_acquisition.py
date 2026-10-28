"""Acquire a reviewed public link through M1/M2 and extend the source library.

Queue membership documents link discovery, not procedural eligibility or coding.
Existing registered bytes are never replaced by a fresh network response.
"""

from datetime import datetime, timezone, date
import json
from pathlib import Path
import re
from urllib.parse import urlparse

import pymupdf
import requests

from .manifest import read_manifest, register_order
from .extract_text import extract_case
from .research_ledger import require, fingerprint, local_path

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {
    "MA": {"www.mass.gov", "fileservice.eea.comacloud.net"},
    "CT": {"www.dpuc.state.ct.us", "portal.ct.gov"},
    "NH": {"www.puc.nh.gov", "puc.nh.gov"},
    "ME": {"mpuc-cms.maine.gov", "www.maine.gov"},
    "VT": {"epuc.vermont.gov", "puc.vermont.gov"},
    "RI": {"ripuc.ri.gov"},
}


def acquire(source_id, root=ROOT, *, session=None, now=None):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    require(now.tzinfo is not None, "Acquisition timestamp needs a timezone")
    today = now.astimezone(timezone.utc).date().isoformat()
    queue = json.loads((root / "data/research/source_queue.json").read_text())["sources"]
    matches = [s for s in queue if s["source_id"] == source_id]
    require(len(matches) == 1, "Source must be uniquely listed in the reviewed acquisition queue")
    source = matches[0]
    require(re.fullmatch(r"(CAND|SUPP)-[A-Z]{2}-[A-Za-z0-9-]+", source_id), "Unsafe source ID")
    prefix = source_id.split("-")[0]
    require(
        source["state"] in HOSTS and source_id.startswith(prefix + "-" + source["state"] + "-"),
        "Source state/ID mismatch",
    )
    source_date = source.get("order_date") or source.get("event_date")
    require(
        source_date and date.fromisoformat(source_date) <= date.fromisoformat(today),
        "Missing or future source date",
    )
    if prefix == "CAND":
        require(source.get("order_date"), "Candidate decision needs a written order date")
    if prefix == "SUPP":
        require(
            source.get("review_status") == "supporting_only"
            and source.get("role")
            and source.get("source_kind"),
            "Supporting source needs an explicit classification",
        )
        if source["source_kind"] in ("official_draft_minutes", "official_docket_filing"):
            require(
                not source.get("order_date") and source.get("event_date"),
                "Minutes and party filings need event dates, not written order dates",
            )
    for key in ("source_url", "landing_url"):
        parsed = urlparse(source[key])
        require(
            parsed.scheme == "https" and parsed.hostname in HOSTS[source["state"]],
            "Source is outside the reviewed official endpoints",
        )
    catalog_path = root / "data/research/source_catalog.json"
    catalog = json.loads(catalog_path.read_text())
    existing = [s for s in catalog["sources"] if s["source_id"] == source_id]
    if existing:
        require(len(existing) == 1, "Duplicate catalog ID")
        record = existing[0]
        require(
            fingerprint(local_path(root, record["pdf_path"])) == record["pdf_sha256"],
            "Saved source changed",
        )
        if record.get("text_path"):
            require(
                fingerprint(local_path(root, record["text_path"])) == record["text_sha256"],
                "Saved extraction changed",
            )
        return dict(status="already_acquired", source=record)
    manifest = root / "data/empirical_manifest.csv"
    registered = [r for r in read_manifest(manifest) if r["case_id"] == source_id]
    require(len(registered) <= 1, "Duplicate registration ID")
    if registered:
        # Keep the first download's date and path, even when extraction resumes
        # on a later day. Missing or changed registered bytes must not be replaced.
        row = registered[0]
        pdf = Path(row["file_path"]).resolve()
        require(pdf.is_relative_to(root), "Registered source is outside the project")
        require(
            row["sha256"] == fingerprint(pdf)
            and row["source_url"] == source["source_url"]
            and row["state"] == source["state"]
            and row["docket"] == source["docket"],
            "Unfinished acquisition conflicts with saved registration",
        )
        directory = pdf.parent
    else:
        directory = root / "data/research" / ("acquisition_" + today)
        directory.mkdir(parents=True, exist_ok=True)
        pdf = directory / (source_id + ".pdf")
    if not pdf.exists():
        try:
            response = (session or requests.Session()).get(source["source_url"], timeout=(10, 30))
            response.raise_for_status()
        except requests.RequestException:
            raise ValueError(
                "Official document download failed; existing library is unchanged"
            ) from None
        destinations = HOSTS[source["state"]] | set(source.get("reviewed_redirect_hosts", []))
        require(urlparse(response.url).hostname in destinations, "Unreviewed download redirect")
        require(response.content.startswith(b"%PDF-"), "Document endpoint returned non-PDF content")
        try:
            with pymupdf.open(stream=response.content, filetype="pdf") as document:
                require(
                    not document.is_encrypted and not document.is_repaired and len(document) > 0,
                    "Source PDF is encrypted, invalid or needs repair",
                )
        except pymupdf.FileDataError:
            raise ValueError("Source PDF is invalid; existing library is unchanged") from None
        with pdf.open("xb") as output:
            output.write(response.content)
    if not registered:
        row = register_order(
            pdf,
            manifest_path=manifest,
            case_id=source_id,
            state=source["state"],
            docket=source["docket"],
            source_url=source["source_url"],
            download_date=today,
        )
    # A failed extraction leaves an immutable download/registration that can be
    # resumed; publication into the catalog waits until the extraction succeeds.
    text_dir = root / "data/empirical_text"
    text = text_dir / (source_id + ".json")
    if not text.exists():
        extract_case(manifest, case_id=source_id, output_dir=text_dir, min_text_chars=80)
    with pymupdf.open(pdf) as document:
        pages = json.loads(text.read_text())
        require(len(pages) == len(document), "Incomplete resumed extraction")
        for n, (saved, page) in enumerate(zip(pages, document), 1):
            native = page.get_text("text", sort=False)
            require(
                saved["page"] == n
                and saved["text"] == native
                and saved["n_chars"] == len(native)
                and saved["likely_scanned"] == (len("".join(native.split())) < 80),
                "Resumed extraction differs",
            )
    record = dict(
        source,
        pdf_path=str(pdf.relative_to(root)),
        pdf_sha256=fingerprint(pdf),
        text_path=str(text.relative_to(root)),
        text_sha256=fingerprint(text),
        n_pages=int(row["n_pages"]),
        download_date=row["download_date"],
        source_kind=source.get("source_kind", "official"),
        review_status=source.get("review_status", "candidate_pending_review"),
        role=source.get(
            "role",
            "Candidate original decision; not selected. Link provenance is recorded in the acquisition queue.",
        ),
    )
    catalog["sources"].append(record)
    catalog.update(n_documents=len(catalog["sources"]), as_of=today)
    (directory / (source_id + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    return dict(status="acquired", source=record)
