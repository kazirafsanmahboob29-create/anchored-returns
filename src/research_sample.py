"""Evidence checks and quota-constrained selection of original written decisions."""

from collections import Counter
from datetime import date
from functools import lru_cache
import json
from pathlib import Path

import pymupdf

from .research_ledger import fingerprint, local_path, require

STATES = ("CT", "MA", "ME", "NH", "RI", "VT")
REQUIRED = "CAND-NH-24-070"
ELIGIBLE = {
    "eligible_contested_roe",
    "eligible_formula_setting",
    "eligible_included_by_design",
    "eligible_uncontested_roe_on_record",
}
STATUSES = ELIGIBLE | {
    "conditional_settled_substitute",
    "excluded_formula_implementation",
    "excluded_no_roe_determination",
}


def choose_sample(candidates, *, size=15, cutoff="2026-10-01", conditional=False):
    """Return the first feasible subsequence in the protocol's descending-date order.

    Conditional substitutes are admitted only for a provisional allocation. An
    unresolved census must never be represented as a completed sampling frame.
    """
    date.fromisoformat(cutoff)
    require(type(size) is int and size > 0, "Sample size must be a positive integer")
    require(all(c["status"] in STATUSES for c in candidates), "Unknown eligibility classification")
    pool = [
        c
        for c in candidates
        if (
            c["status"] in ELIGIBLE
            or conditional
            and c["status"] == "conditional_settled_substitute"
        )
        and "2019-01-01" <= c["order_date"] <= cutoff
    ]
    require(len({c["candidate_id"] for c in pool}) == len(pool), "Duplicate candidate identity")
    # Sorting the date separately retains ascending tie-breaks.
    pool.sort(key=lambda c: (c["state"], c["docket"], c["utility"]))
    pool.sort(key=lambda c: c["order_date"], reverse=True)
    for c in pool:
        require(c["state"] in STATES, "Unknown sample state")
        date.fromisoformat(c["order_date"])

    @lru_cache(None)
    def solve(i, n, counts, early, later, required):
        if n == size:
            return (
                ()
                if all(counts) and counts[5] >= 2 and early >= 5 and later >= 5 and required
                else None
            )
        if len(pool) - i < size - n:
            return None
        if i == len(pool):
            return None
        c = pool[i]
        state = STATES.index(c["state"])
        if counts[state] < 4:
            updated = list(counts)
            updated[state] += 1
            suffix = solve(
                i + 1,
                n + 1,
                tuple(updated),
                min(5, early + int(c["order_date"] <= "2021-12-31")),
                min(5, later + int(c["order_date"] >= "2023-01-01")),
                required or c["candidate_id"] == REQUIRED,
            )
            if suffix is not None:
                return (i,) + suffix
        return solve(i + 1, n, counts, early, later, required)

    indices = solve(0, 0, (0,) * 6, 0, 0, False)
    return None if indices is None else [pool[i] for i in indices]


def sample_report(root, screening_path="data/research/sample_screening.json"):
    root = Path(root)
    path = root / screening_path
    data = json.loads(path.read_text())
    catalog = {
        s["source_id"]: s
        for s in json.loads((root / "data/research/source_catalog.json").read_text())["sources"]
    }
    candidates = data["considered_local_candidates"]
    require(type(data["frame_complete"]) is bool, "Frame completion must be an explicit boolean")
    require(
        len({c["candidate_id"] for c in candidates}) == len(candidates),
        "Duplicate screening identity",
    )
    documents = {}
    try:
        for c in candidates:
            date.fromisoformat(c["order_date"])
            require(c["state"] in STATES and c.get("utility"), "Screening needs state and utility")
            require(
                c["services"]
                and len(set(c["services"])) == len(c["services"])
                and set(c["services"]) <= {"Electric", "Gas"},
                "Screening needs distinct electric/gas services",
            )
            require(
                c.get("screening_evidence"),
                "Screening decision needs original evidence: " + c["candidate_id"],
            )
            for evidence in c["screening_evidence"]:
                sid = evidence["source_id"]
                require(
                    sid in c["source_ids"] and sid in catalog,
                    "Screening references an unrelated source",
                )
                source = catalog[sid]
                require(
                    evidence["pdf_sha256"] == source["pdf_sha256"],
                    "Screening PDF fingerprint differs",
                )
                if sid not in documents:
                    pdf = local_path(root, source["pdf_path"])
                    require(fingerprint(pdf) == source["pdf_sha256"], "Screening source changed")
                    documents[sid] = pymupdf.open(pdf)
                doc = documents[sid]
                require(
                    type(evidence["page"]) is int and 1 <= evidence["page"] <= len(doc),
                    "Invalid screening page",
                )
                text = doc[evidence["page"] - 1].get_text("text", sort=False)
                a, b = evidence["start_char"], evidence["end_char"]
                require(
                    type(a) is int and type(b) is int and 0 <= a < b <= len(text),
                    "Invalid screening offsets",
                )
                require(
                    text[a:b] == evidence["exact_text"], "Screening excerpt differs from original"
                )
                require(evidence.get("purpose"), "Screening evidence needs a purpose")
    finally:
        for doc in documents.values():
            doc.close()
    selected = choose_sample(candidates, cutoff=data["frame_cutoff"])
    proposal = selected or choose_sample(candidates, cutoff=data["frame_cutoff"], conditional=True)
    blockers = []
    if not data["frame_complete"]:
        blockers.append("The six-state written-decision census is incomplete.")
    if data["unresolved_search_leads"]:
        blockers.append(
            "Unresolved original-order leads could change eligibility or date priority."
        )
    if proposal and any(
        c["status"] == "conditional_settled_substitute"
        and not (
            data.get("state_census_complete", {}).get(c["state"]) is True
            and c.get("substitution_confirmed") is True
            and c.get("substitution_basis")
        )
        for c in proposal
    ):
        blockers.append("Rhode Island substitution still requires a completed state census.")
    if proposal is None:
        blockers.append("The screened records cannot satisfy all sample quotas.")
    final = not blockers
    require(
        data["frame_complete"] is False
        or all(data.get("state_census_complete", {}).get(s) is True for s in STATES),
        "A complete frame requires a documented census for all six states",
    )
    expected = [c["candidate_id"] for c in (proposal or [])]
    require(
        data.get("proposed_ids", []) == expected, "Sample allocation is stale; rebuild the proposal"
    )
    require(
        data["selected_ids"] == (expected if final else []),
        "Final sample is inconsistent with its evidence",
    )
    counts = Counter(c["state"] for c in proposal or [])
    return dict(
        status="finalized"
        if final
        else "provisional_feasible"
        if proposal
        else "infeasible_local_frame",
        frame_cutoff=data["frame_cutoff"],
        screened=len(candidates),
        eligible=sum(c["status"].startswith("eligible_") for c in candidates),
        excluded=sum(c["status"].startswith("excluded_") for c in candidates),
        proposed=len(expected),
        finalized=len(data["selected_ids"]),
        proposed_ids=expected,
        state_counts=dict(counts),
        early_orders=sum(c["order_date"] <= "2021-12-31" for c in proposal or []),
        later_orders=sum(c["order_date"] >= "2023-01-01" for c in proposal or []),
        blockers=blockers,
        candidates=[
            dict(
                {k: v for k, v in c.items() if k != "screening_evidence"},
                evidence_pages=[
                    dict(source_id=e["source_id"], page=e["page"]) for e in c["screening_evidence"]
                ],
            )
            for c in proposal or []
        ],
        screening_sha256=fingerprint(path),
    )
