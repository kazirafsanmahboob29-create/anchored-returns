"""Validate the empirical evidence ledger without changing research inputs.

The ledger keeps reviewed paragraph boundaries, exact source spans and per-code
stances outside the frozen v0.1.2 workbook. Validation establishes integrity and
coverage; it does not independently verify the interpretation of a passage.
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys

from .validate_sheet import SCHEMA

CODES = tuple(SCHEMA["lists"]["Code"])
STANCES = set(SCHEMA["lists"]["Stance"])
SECTIONS = set(SCHEMA["lists"]["Section"])
METHODS = set(SCHEMA["lists"]["Method"])


class LedgerError(ValueError):
    """An empirical record lacks valid evidence or has inconsistent labels."""


def require(condition, message):
    if not condition:
        raise LedgerError(message)


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_path(root, value):
    path = Path(value)
    require(not path.is_absolute(), "Ledger paths must be relative to the project")
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root), "Ledger path escapes project")
    return resolved


def evidence_text(spans, pages):
    require(isinstance(spans, list) and spans, "Evidence needs at least one span")
    pieces = []
    previous = None
    for span in spans:
        page, start, end = (span.get(k) for k in ("page", "start_char", "end_char"))
        require(all(type(n) is int for n in (page, start, end)), "Span offsets must be integers")
        require(
            page in pages and 0 <= start < end <= len(pages[page]), "Evidence span out of bounds"
        )
        require(
            previous is None or (page, start) >= previous,
            "Evidence spans overlap or are out of order",
        )
        actual = pages[page][start:end]
        require(actual == span.get("exact_text"), "Exact evidence differs from source text")
        pieces.append(actual)
        previous = (page, end)
    return "\n".join(pieces)


def validate_ledger(path, *, root=None):
    path = Path(path).resolve()
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    ledger = json.loads(path.read_text())
    require(ledger.get("schema_version") == "1.0", "Unsupported evidence-ledger schema")
    require(
        ledger.get("sample_status") == "not_finalized", "This ledger is a candidate coding release"
    )
    require(ledger.get("coding_origin") == "assistant_assisted", "Coding provenance is missing")
    require(
        ledger.get("independent_reliability") == "not_measured",
        "Reliability must be measured separately",
    )
    require(
        bool(ledger.get("coder")) and bool(ledger.get("codebook_version")), "Missing coder/version"
    )
    freeze = date.fromisoformat(ledger["frame_cutoff"])
    released = date.fromisoformat(ledger.get("release_date", ledger["coding_date"]))
    require(
        date.fromisoformat(ledger["coding_date"]) <= released, "Coding date exceeds release date"
    )
    sources, pages = {}, {}
    for source in ledger["sources"]:
        sid = source["source_id"]
        require(sid not in sources, "Duplicate source ID")
        require(re.match(r"^https://", source["source_url"]), "Source needs an HTTPS reference")
        for kind in ("pdf", "text"):
            target = local_path(root, source[f"{kind}_path"])
            require(
                fingerprint(target) == source[f"{kind}_sha256"],
                f"{kind} fingerprint changed: {sid}",
            )
        rows = json.loads(local_path(root, source["text_path"]).read_text())
        require(
            [r["page"] for r in rows] == list(range(1, len(rows) + 1)), "Nonsequential source pages"
        )
        require(len(rows) == source["n_pages"], "Page count changed")
        pages[sid] = {r["page"]: r["text"] for r in rows}
        sources[sid] = source
    cases = {c["case_id"]: c for c in ledger["cases"]}
    require(bool(cases), "Ledger needs a case record")
    require(len(cases) == len(ledger["cases"]), "Duplicate case ID")
    occupied = {cid: {} for cid in cases}
    passage_ids = set()
    for unit in ledger["passages"]:
        pid, cid = unit["passage_id"], unit["case_id"]
        require(pid not in passage_ids, "Duplicate passage ID")
        passage_ids.add(pid)
        require(cid in cases and unit["source_id"] in sources, "Unknown case/source")
        require(
            unit["source_id"] in cases[cid]["source_ids"], "Passage belongs to another case source"
        )
        require(unit["unit_type"] in ("paragraph", "footnote"), "Unsupported passage unit")
        require(unit["section"] in SECTIONS, "Unknown passage section")
        require(set(unit["codes"]) == set(CODES), "Passage needs all eleven code flags")
        require(
            all(type(v) is int and v in (0, 1) for v in unit["codes"].values()),
            "Code flags must be binary integers",
        )
        active = {k for k, v in unit["codes"].items() if v}
        require(set(unit["stances"]) == active, "Each active code needs its own stance")
        require(set(unit["stances"].values()) <= STANCES, "Invalid stance")
        require(
            unit["primary_code"] in active if active else unit["primary_code"] is None,
            "Primary code is not active",
        )
        require(unit["method"] in METHODS, "Unknown model method")
        require(
            unit["method"] != "n.a." if "MKT" in active else unit["method"] == "n.a.",
            "Method/MKT mismatch",
        )
        require(bool(unit["notes"].strip()), "A contextual coding rationale is required")
        require(
            date.fromisoformat(unit.get("coding_date", ledger["coding_date"])) <= released,
            "Passage coding date exceeds release date",
        )
        if unit["section"] in ("Positions of parties", "ALJ recommendation"):
            require(
                set(unit["stances"].values()) <= {"Summarized only"},
                "Party summaries cannot count as adopted reasoning",
            )
        else:
            require(
                "Summarized only" not in unit["stances"].values(),
                "Commission passages need evaluated stances",
            )
        require(
            evidence_text(unit["spans"], pages[unit["source_id"]]) == unit["text"],
            "Passage text changed",
        )
        for span in unit["spans"]:
            key = (unit["source_id"], span["page"])
            positions = occupied[cid].setdefault(key, set())
            current = set(range(span["start_char"], span["end_char"]))
            require(not positions & current, "Coded passages overlap")
            positions.update(current)
    coverage = []
    for cid, case in cases.items():
        require(set(case["source_ids"]) <= sources.keys(), "Case has unknown source")
        require(date.fromisoformat(case["order_date"]) <= freeze, "Future decision")
        require(
            case["coding_status"] in ("first_pass_complete", "not_started"), "Unknown coding status"
        )
        n_units = sum(u["case_id"] == cid for u in ledger["passages"])
        require(
            bool(case["reviewed_scopes"]) and n_units > 0
            if case["coding_status"] == "first_pass_complete"
            else not case["reviewed_scopes"] and not case["excluded_spans"] and n_units == 0,
            "Coding status contradicts reviewed evidence",
        )
        scope_positions = {}
        for scope in case["reviewed_scopes"]:
            sid = scope["source_id"]
            evidence_text([scope], pages[sid])
            key = (sid, scope["page"])
            positions = scope_positions.setdefault(key, set())
            current = set(range(scope["start_char"], scope["end_char"]))
            require(not positions & current, "Reviewed scopes overlap")
            positions.update(current)
        covered = {key: set(values) for key, values in occupied[cid].items()}
        for item in case["excluded_spans"]:
            sid = item["source_id"]
            require(bool(item["reason"].strip()), "Excluded text needs a reason")
            evidence_text([item], pages[sid])
            key = (sid, item["page"])
            values = set(range(item["start_char"], item["end_char"]))
            require(
                values <= scope_positions.get(key, set()), "Excluded span outside reviewed scope"
            )
            require(
                not values & covered.setdefault(key, set()),
                "Exclusion overlaps coded/excluded text",
            )
            covered[key].update(values)
        for key, positions in occupied[cid].items():
            require(
                positions <= scope_positions.get(key, set()), "Coded text outside reviewed scope"
            )
        for (sid, page), positions in scope_positions.items():
            missing = positions - covered.get((sid, page), set())
            require(
                all(pages[sid][page][n].isspace() for n in missing),
                f"Unaccounted source text: {cid}, p.{page}",
            )
        coverage.append(
            dict(
                case_id=cid,
                passages=n_units,
                scoped_pages=len(scope_positions),
                nonwhitespace_coverage="complete" if scope_positions else "not_reviewed",
            )
        )
    fact_ids = set()
    for fact in ledger["numeric_facts"]:
        require(fact["fact_id"] not in fact_ids, "Duplicate numeric fact")
        fact_ids.add(fact["fact_id"])
        require(
            fact["case_id"] in cases and fact["source_id"] in cases[fact["case_id"]]["source_ids"],
            "Unknown fact case/source",
        )
        require(date.fromisoformat(fact["event_date"]) <= freeze, "Future numeric event")
        quote = evidence_text(fact["spans"], pages[fact["source_id"]])
        require(fact["relation"] in ("equal", "at_least", "at_most"), "Unknown numeric relation")
        divisor = {"percent": Decimal(100), "basis_points": Decimal(10000)}.get(
            fact["printed_unit"]
        )
        require(divisor is not None, "Unknown numeric unit")
        try:
            printed, value = Decimal(fact["printed_value"]), Decimal(fact["value_fraction"])
        except InvalidOperation as error:
            raise LedgerError("Invalid decimal") from error
        require(
            printed.is_finite() and value.is_finite() and printed / divisor == value,
            "Numeric conversion differs",
        )
        token = re.escape(fact["printed_value"].lstrip("+-"))
        require(
            re.search(r"(?<![\d.])" + token + r"(?![\d.])", quote),
            "Printed number absent from evidence",
        )
        visual = fact["visual_check"]
        require(
            visual["page"] in {s["page"] for s in fact["spans"]},
            "Visual check is for a different page",
        )
        require(
            fingerprint(local_path(root, visual["path"])) == visual["sha256"],
            "Visual evidence changed",
        )
        require(
            bool(visual.get("reviewer")) and date.fromisoformat(visual["checked_date"]) <= released,
            "Missing or future visual review",
        )
        require(bool(fact["notes"].strip()), "Numeric attribution needs a note")
    return dict(
        status="passed",
        n_cases=len(cases),
        n_passages=len(passage_ids),
        n_new_numeric_facts=len(fact_ids),
        coverage=coverage,
        limits=[
            "Candidate coding, not a finalized sample.",
            "Integrity checks do not establish independent coding reliability.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger")
    args = parser.parse_args()
    try:
        print(json.dumps(validate_ledger(args.ledger), indent=2))
    except (LedgerError, OSError, KeyError, TypeError, ValueError) as error:
        print(f"ledger validation failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
