"""Validate additive numeric records without rewriting frozen first-pass inputs."""

import json
from decimal import Decimal
from pathlib import Path

import pymupdf

from .research_ledger import fingerprint, local_path, require


def load_cohort_facts(root, version="0.1.5"):
    root = Path(root).resolve()
    path = root / ("data/research/cohort_numeric_facts_v" + version + ".json")
    data = json.loads(path.read_text())
    catalog = {
        s["source_id"]: s
        for s in json.loads((root / "data/research/source_catalog.json").read_text())["sources"]
    }
    facts = []
    require(
        len({r["fact_id"] for r in data["facts"]}) == len(data["facts"]),
        "Duplicate expanded numeric identity",
    )
    for r in data["facts"]:
        source = catalog[r["source_id"]]
        pdf = local_path(root, source["pdf_path"])
        require(
            fingerprint(pdf) == r["pdf_sha256"] == source["pdf_sha256"],
            "Expanded numeric source changed",
        )
        require(r["event_date"] == source["order_date"], "Expanded numeric event date differs")
        value = Decimal(r["value"])
        require(
            value.is_finite() and 0 < value < 25 and r["unit"] == "percent", "Invalid expanded ROE"
        )
        with pymupdf.open(pdf) as doc:
            quotes = []
            for span in r["spans"]:
                require(
                    type(span["page"]) is int and 1 <= span["page"] <= len(doc),
                    "Invalid expanded evidence page",
                )
                t = doc[span["page"] - 1].get_text("text", sort=False)
                a, b = span["start_char"], span["end_char"]
                require(
                    type(a) is int and type(b) is int and 0 <= a < b <= len(t),
                    "Invalid expanded offsets",
                )
                require(t[a:b] == span["exact_text"], "Expanded numeric excerpt differs")
                quotes.append(span["exact_text"])
        quote = "\n".join(quotes)
        require(r["value"] in quote, "Expanded value is absent from evidence")
        review = r["visual_check"]
        require(
            fingerprint(local_path(root, review["path"])) == review["sha256"],
            "Expanded source rendering changed",
        )
        facts.append(
            dict(
                case_id=r["case_id"],
                field=r["field"],
                value=r["value"],
                unit=r["unit"],
                relation="equal",
                event_date=r["event_date"],
                page=r["spans"][0]["page"],
                quote=quote,
                notes=r["notes"],
                source_url=source["source_url"],
                pdf_path=source["pdf_path"],
                pdf_sha256=source["pdf_sha256"],
            )
        )
    return facts
