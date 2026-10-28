"""Versioned document cohorts, separate from the original quota-based pilot."""

from collections import Counter
import json
from pathlib import Path

from .research_ledger import fingerprint, require
from .research_sample import ELIGIBLE, sample_report


def cohort_report(root, version="0.1.5"):
    root = Path(root).resolve()
    path = root / ("data/research/cohort_v" + version + ".json")
    data = json.loads(path.read_text())
    # Validate every original screening excerpt before admitting a document.
    screening_name = data.get("screening_path", "data/research/sample_screening.json")
    sample_report(root, screening_name)
    screening_path = root / screening_name
    require(
        fingerprint(screening_path) == data["screening_sha256"], "Cohort screening snapshot changed"
    )
    screening = json.loads(screening_path.read_text())
    catalog = {
        s["source_id"]: s
        for s in json.loads((root / "data/research/source_catalog.json").read_text())["sources"]
    }
    expected = {
        c["candidate_id"]
        for c in screening["considered_local_candidates"]
        if c["status"] in ELIGIBLE and "2019-01-01" <= c["order_date"] <= data["cutoff"]
    }
    primary = {r["candidate_id"] for r in data["members"] if r["stratum"] == "primary"}
    require(primary == expected, "Expanded cohort must include every screened eligible decision")
    require(
        len({r["candidate_id"] for r in data["members"]}) == len(data["members"]),
        "Duplicate cohort member",
    )
    candidates = {c["candidate_id"]: c for c in screening["considered_local_candidates"]}
    members = []
    for r in data["members"]:
        require(r["stratum"] in ("primary", "settlement", "formula"), "Unknown cohort stratum")
        c = candidates[r["candidate_id"]]
        require(
            r["stratum"] != "settlement"
            or c["status"] in ("conditional_settled_substitute", "eligible_settlement_supplement"),
            "Settlement admission differs",
        )
        require(
            r["stratum"] != "formula" or c["status"] == "excluded_formula_implementation",
            "Formula supplement admission differs",
        )
        require(
            r["source_sha256"] == {sid: catalog[sid]["pdf_sha256"] for sid in c["source_ids"]},
            "Cohort source identity changed",
        )
        members.append(dict(c, **r))
    return dict(
        version=data["version"],
        date=data["date"],
        cutoff=data["cutoff"],
        status="fixed_document_cohort",
        census_complete=False,
        primary=len(primary),
        supplemental=sum(r["stratum"] == "settlement" for r in members),
        formula=sum(r["stratum"] == "formula" for r in members),
        total=len(members),
        proceedings=len({r["proceeding_group"] for r in members}),
        state_counts=dict(Counter(c["state"] for c in members)),
        members=members,
        manifest_path=str(path.relative_to(root)),
        manifest_sha256=fingerprint(path),
        protocol_path=data["protocol_path"],
        screening_path=screening_name,
        scope=data["scope"],
    )
