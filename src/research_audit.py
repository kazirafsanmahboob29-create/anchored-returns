"""Source availability and census progress, without turning access into evidence."""

from collections import Counter
import json
from pathlib import Path
from urllib.parse import urlparse

import pymupdf

from .research_ledger import fingerprint, local_path, require
from .treasury_crosscheck import load_crosscheck


def source_audit(root, catalog, treasury, benchmarks, reliability):
    root = Path(root)
    path = root / "data/external/rra_context_sources.json"
    context = json.loads(path.read_text()) if path.exists() else {"sources": []}
    for source in context["sources"]:
        require(
            source["status"] == "context_only", "Context report cannot become a half-year benchmark"
        )
        parsed = urlparse(source["source_url"])
        require(
            parsed.scheme == "https"
            and parsed.hostname in {"documents.dps.ny.gov", "pscdocs.utah.gov"},
            "Context report endpoint is outside reviewed commission hosts",
        )
        pdf = local_path(root, source["pdf_path"])
        require(fingerprint(pdf) == source["pdf_sha256"], "Context report fingerprint changed")
        with pymupdf.open(pdf) as doc:
            require(
                len(doc) == source["n_pages"] and 1 <= source["page"] <= len(doc),
                "Context report page count or reference differs",
            )
    frame = json.loads((root / "data/research/sample_screening.json").read_text())
    crosscheck = load_crosscheck(root)
    by_source = {s["source_id"]: s for s in catalog["sources"]}
    census = []
    for state in ("CT", "MA", "ME", "NH", "RI", "VT"):
        screened = [c for c in frame["considered_local_candidates"] if c["state"] == state]
        counts = Counter(c["status"].split("_")[0] for c in screened)
        census.append(
            dict(
                state=state,
                complete=frame["state_census_complete"].get(state) is True,
                screened=len(screened),
                eligible=counts["eligible"],
                excluded=counts["excluded"],
                conditional=counts["conditional"],
                leads=[r for r in frame["unresolved_search_leads"] if r["state"] == state],
                records=[
                    dict(
                        candidate_id=c["candidate_id"],
                        docket=c["docket"],
                        order_date=c["order_date"],
                        status=c["status"],
                        reason=c["reason"],
                        evidence=[
                            dict(
                                page=e["page"],
                                purpose=e["purpose"],
                                pdf_path=by_source[e["source_id"]]["pdf_path"],
                            )
                            for e in c["screening_evidence"]
                        ],
                    )
                    for c in screened
                ],
            )
        )
    return dict(
        status="verified_saved_sources_partial_research",
        context_sources=context["sources"],
        census=census,
        census_complete=sum(c["complete"] for c in census),
        connections=[
            dict(
                name="FRED DGS10",
                mode="Refreshable public CSV / optional keyed JSON",
                status="saved_snapshot_verified" if treasury else "not_connected",
                retrieved_at_utc=treasury["retrieved_at_utc"] if treasury else None,
                source_url="https://fred.stlouisfed.org/series/DGS10",
            ),
            dict(
                name="U.S. Treasury",
                mode="Refreshable official XML; separate FRED comparison",
                status="saved_crosscheck_verified" if crosscheck else "not_connected",
                comparisons=crosscheck["overlapping_dates"] if crosscheck else None,
                disagreements=len(crosscheck["disagreements"]) if crosscheck else None,
                source_url="https://home.treasury.gov/resource-center-data-chart-center/interest-rates",
            ),
            dict(
                name="Commission orders",
                mode="Reviewed docket links and preserved PDF downloads",
                status="saved_library_verified_census_incomplete",
                documents=catalog["n_documents"],
            ),
            dict(
                name="RRA national means",
                mode="Original publisher reports in public dockets",
                status="partial_public_access",
                verified_half_years=benchmarks["verified_half_years"],
                context_reports=len(context["sources"]),
            ),
        ],
        independent_ratings=dict(
            status=reliability["status"],
            units=reliability.get("units", 0),
            orders=reliability.get("orders", 0),
            agreement=None,
            explanation="No independent observations have been recorded. The frozen packet and blank workspace are ready; repeated coding by the first coder cannot supply independent agreement.",
        ),
        limits="A verified saved file is not a continuous live docket connection. Refresh dates identify retrievals, not historical real-time availability. Search text, annual means and confidential removal notices do not fill missing half-year values.",
    )
