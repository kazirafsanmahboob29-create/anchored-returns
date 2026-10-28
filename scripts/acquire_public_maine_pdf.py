"""Retrieve a known public MPUC PDF through its public document-opening form.

The legacy query-string ViewDoc links no longer identify the requested document
in a fresh session. The site's current filing control posts a document reference,
then opens session-scoped ViewDoc.aspx. No account, credentials, browser state,
CAPTCHA, or security setting is used. Supply only a publicly documented reference.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import pymupdf
import requests

BASE = "https://mpuc-cms.maine.gov/CQM.Public.WebUI/"


class Form(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "hidden" and attrs.get("name"):
            self.fields[attrs["name"]] = attrs.get("value", "")


def acquire(*, guid, document_name, filing_url, public_reference_url, output):
    if not re.fullmatch(r"[A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12}", guid):
        raise ValueError("Supply the exact public document GUID.")
    if not filing_url.startswith(BASE + "MatterManagement/MatterFilingItem.aspx?"):
        raise ValueError("Use an observed official filing-detail URL.")
    output = Path(output)
    if output.suffix != ".pdf" or any(
        output.with_suffix(ext).exists() for ext in (".pdf", ".txt", ".json")
    ):
        raise ValueError("Use a new output path with no existing PDF, text or metadata files.")
    with requests.Session() as session:
        response = session.get(filing_url, timeout=25)
        response.raise_for_status()
        form = Form()
        form.feed(response.text)
        if not {"__VIEWSTATE", "HdnDocumentParameter"} <= form.fields.keys():
            raise ValueError("The public document-opening form has changed.")
        form.fields["HdnDocumentParameter"] = "{" + guid + "}^pdf^Public^0^" + document_name
        form.fields["HdnBtnDocumentOpen"] = ""
        opened = session.post(filing_url, data=form.fields, timeout=25)
        opened.raise_for_status()
        if "window.open('../Common/ViewDoc.aspx')" not in opened.text:
            raise ValueError("The public site did not open the requested document.")
        response = session.get(BASE + "Common/ViewDoc.aspx", timeout=30)
        response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise ValueError("The site returned a non-PDF response; nothing saved.")
    with pymupdf.open(stream=response.content, filetype="pdf") as doc:
        if doc.is_encrypted or doc.is_repaired:
            raise ValueError("Unexpected PDF structure.")
        text = "\n".join(
            f"\n=== VIEWER PAGE {i + 1} ===\n" + page.get_text() for i, page in enumerate(doc)
        )
        pages = len(doc)
    metadata = dict(
        source_url=public_reference_url,
        landing_url=filing_url,
        document_guid=guid,
        document_name=document_name,
        sha256=hashlib.sha256(response.content).hexdigest(),
        n_pages=pages,
        downloaded_at_utc=datetime.now(timezone.utc).isoformat(),
        retrieval_method="Public document-opening form and session-scoped ViewDoc; no authentication",
        status="acquired_pending_eligibility",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as destination:
        destination.write(response.content)
    with output.with_suffix(".txt").open("x") as destination:
        destination.write(text)
    with output.with_suffix(".json").open("x") as destination:
        destination.write(json.dumps(metadata, indent=2) + "\n")
    return dict(path=str(output.resolve()), sha256=metadata["sha256"], n_pages=pages)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("guid", "document-name", "filing-url", "public-reference-url", "output"):
        parser.add_argument("--" + name, required=True)
    print(json.dumps(acquire(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()
