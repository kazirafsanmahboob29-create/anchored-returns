"""Build the local project overview from the evidence ledger and source catalog."""

import argparse
import json
from pathlib import Path

from .research_ledger import fingerprint, local_path, require, validate_ledger
from .research_sample import sample_report
from .research_benchmarks import benchmark_report
from .research_reliability import packet_status
from .research_insights import build_insights, original_fact, AWARD_FIELDS
from .research_audit import source_audit
from .research_cohort import cohort_report
from .cohort_facts import load_cohort_facts
from .eei_benchmarks import eei_report

ROOT = Path(__file__).resolve().parents[1]


def overview_payload(root=ROOT):
    root = Path(root).resolve()
    ledger_path = root / "data/research/empirical_ledger_v0.1.3.json"
    check = validate_ledger(ledger_path, root=root)
    ledger = json.loads(ledger_path.read_text())
    catalog = json.loads((root / "data/research/source_catalog.json").read_text())
    baseline = json.loads((root / "data/research/assistant_verified_case_facts.json").read_text())
    for source in catalog["sources"]:
        require(
            fingerprint(local_path(root, source["pdf_path"])) == source["pdf_sha256"],
            "Library source changed: " + source["source_id"],
        )
    require(
        len({s["source_id"] for s in catalog["sources"]}) == catalog["n_documents"],
        "Library IDs/count differ",
    )
    facts = []
    for record in baseline["facts"]:
        require(
            fingerprint(local_path(root, record["pdf_path"])) == record["pdf_sha256"],
            "Historical numeric source changed",
        )
        rows = json.loads(local_path(root, record["text_path"]).read_text())
        require(
            fingerprint(local_path(root, record["text_path"])) == record["text_sha256"],
            "Historical numeric text changed",
        )
        evidence = record["evidence"]
        require(
            rows[record["pdf_page"] - 1]["text"][evidence["start_char"] : evidence["end_char"]]
            == evidence["exact_text"],
            "Historical numeric excerpt changed",
        )
        facts.append(
            dict(
                case_id=record["case_id"],
                field=record["field"],
                value=record["printed_value"],
                unit=record["printed_unit"],
                relation=record["relation"],
                event_date=record["event_date"],
                page=record["pdf_page"],
                quote=evidence["exact_text"],
                notes=record["notes"],
                source_url=record["source_url"],
                pdf_path=record["pdf_path"],
                pdf_sha256=record["pdf_sha256"],
            )
        )
    sources = {s["source_id"]: s for s in ledger["sources"]}
    for record in ledger["numeric_facts"]:
        source = sources[record["source_id"]]
        facts.append(
            dict(
                case_id=record["case_id"],
                field=record["field"],
                value=record["printed_value"],
                unit=record["printed_unit"],
                relation=record["relation"],
                event_date=record["event_date"],
                page=record["spans"][0]["page"],
                quote="\n".join(s["exact_text"] for s in record["spans"]),
                notes=record["notes"],
                source_url=source["source_url"],
                pdf_path=source["pdf_path"],
                pdf_sha256=source["pdf_sha256"],
            )
        )
    case_cards = []
    cohort = cohort_report(root) if (root / "data/research/cohort_v0.1.4.json").exists() else None
    if cohort:
        facts.extend(load_cohort_facts(root))
    for case in ledger["cases"]:
        award = original_fact(facts, case, AWARD_FIELDS)
        case_cards.append(
            dict(
                case_id=case["case_id"],
                state=case["state"],
                utility=case["utility"],
                docket=case["docket"],
                order_date=case["order_date"],
                coding_status=case["coding_status"],
                award=award["value"] if award else None,
                notes=case["reasoning_notes"],
            )
        )
    treasury = None
    sample = sample_report(root)
    # Historical numeric entries are real evidence even when their sections have
    # not yet been coded or the candidate is outside the current proposal.
    screened = json.loads(
        (
            root / (cohort["screening_path"] if cohort else "data/research/sample_screening.json")
        ).read_text()
    )["considered_local_candidates"]
    known = {c["case_id"] for c in case_cards}
    for c in screened:
        if c["candidate_id"] not in known and any(f["case_id"] == c["candidate_id"] for f in facts):
            case = dict(
                case_id=c["candidate_id"],
                state=c["state"],
                utility=c["utility"],
                docket=c["docket"],
                order_date=c["order_date"],
                coding_status="not_started",
                stratum=next(
                    (
                        r["stratum"]
                        for r in cohort["members"]
                        if r["candidate_id"] == c["candidate_id"]
                    ),
                    None,
                )
                if cohort
                else None,
            )
            award = original_fact(facts, case, AWARD_FIELDS) or original_fact(
                facts, case, {"approved_settlement_roe"}
            )
            case_cards.append(
                dict(
                    case,
                    award=award["value"] if award else None,
                    notes="Verified numeric records; full-section coding has not started. "
                    + c["reason"],
                )
            )
            known.add(c["candidate_id"])
    benchmarks = benchmark_report(root, sample["candidates"])
    cohort_benchmarks = benchmark_report(root, cohort["members"]) if cohort else None
    eei = (
        eei_report(root, cohort["members"])
        if cohort and (root / "data/external/eei/source.json").exists()
        else None
    )
    if eei:
        eei = {k: v for k, v in eei.items() if k != "rows"}
    reliability = packet_status(root)
    inputs = [
        ledger_path,
        root / "data/research/source_catalog.json",
        root / "data/research/assistant_verified_case_facts.json",
    ]
    inputs.extend(
        [
            root / "data/research/sample_screening.json",
            root / "data/external/rra_historical_benchmarks.json",
        ]
    )
    if cohort:
        inputs.extend(
            [
                root / cohort["manifest_path"],
                root / ("data/research/cohort_numeric_facts_v" + cohort["version"] + ".json"),
                root / cohort["screening_path"],
                root / cohort["protocol_path"],
            ]
        )
    if eei:
        inputs.extend([root / "data/external/eei/source.json", root / eei["sources"][0]["path"]])
    for record in benchmarks["records"]:
        if record.get("estimation_method") == "case_level_reconstruction":
            inputs.append(root / record["reconstruction"]["path"])
    if reliability["status"] != "packet_not_built":
        inputs.append(
            root / "data/research/reliability" / reliability["packet_id"] / "manifest.json"
        )
    if (root / "data/external/treasury/latest.json").exists():
        from .treasury import load_snapshot, join_orders

        meta, observations = load_snapshot(root)
        expected = join_orders(root)
        joined = root / "data/research/treasury_order_joins.json"
        require(
            json.loads(joined.read_text()) == expected,
            "Treasury order joins changed or need refreshing",
        )
        treasury = dict(
            latest=meta["latest_nonmissing"],
            retrieved_at_utc=meta["retrieved_at_utc"],
            transport=meta["transport"],
            rows=meta["rows"],
            missing=meta["missing"],
            source_url=meta["series_url"],
            raw_sha256=meta["raw_sha256"],
            joins=expected["joins"],
            observations_sha256=meta["observations_sha256"],
            series=[
                dict(date=r["date"], percent=r["printed_percent"])
                for r in observations
                if r["date"] >= "2019-01-01"
            ],
        )
        inputs.extend([root / "data/external/treasury/latest.json", joined])
    if (root / "data/external/rra_context_sources.json").exists():
        inputs.append(root / "data/external/rra_context_sources.json")
    return dict(
        date=max(
            ledger.get("release_date", catalog["as_of"]),
            catalog["as_of"],
            cohort["date"] if cohort else "",
            eei["checked_date"] if eei else "",
        ),
        stats=dict(
            documents=catalog["n_documents"],
            facts=len(facts),
            passages=check["n_passages"],
            coded_orders=sum(c["coding_status"] == "first_pass_complete" for c in ledger["cases"]),
            selected_orders=sample["finalized"],
            proposed_orders=sample["proposed"],
            screened_orders=sample["screened"],
            benchmark_values=benchmarks["verified_records"],
            benchmark_matched_orders=benchmarks["orders_with_all_services_matched"],
            target_orders=15,
            cohort_orders=cohort["total"] if cohort else 0,
        ),
        cases=case_cards,
        passages=ledger["passages"],
        facts=facts,
        sources=catalog["sources"],
        missing=ledger["missing_fields"],
        treasury=treasury,
        sample=sample,
        cohort=cohort,
        cohort_benchmarks=cohort_benchmarks,
        eei=eei,
        benchmarks=benchmarks,
        reliability=reliability,
        insights=build_insights(
            case_cards,
            facts,
            ledger["passages"],
            benchmark_joins=benchmarks["joins"],
            benchmark_records=benchmarks["records"],
        ),
        audit=source_audit(root, catalog, treasury, benchmarks, reliability),
        provenance=dict(
            coder=ledger["coder"],
            coding_origin=ledger["coding_origin"],
            version=ledger["codebook_version"],
            reliability=ledger["independent_reliability"],
        ),
        inputs={str(p.relative_to(root)): fingerprint(p) for p in inputs},
    )


def build_overview(root=ROOT):
    root = Path(root).resolve()
    payload = overview_payload(root)
    pointer = root / "reports/analysis/latest.json"
    if pointer.exists():
        reference = json.loads(pointer.read_text())
        manifest_path = local_path(root, reference["manifest_path"])
        require(
            fingerprint(manifest_path) == reference["manifest_sha256"],
            "Analysis release manifest changed",
        )
        analysis = json.loads(manifest_path.read_text())
        current = all(
            analysis["input_sha256"].get(path) == sha for path, sha in payload["inputs"].items()
        )
        current = current and all(
            fingerprint(root / "analysis" / name) == sha
            for name, sha in analysis["script_sha256"].items()
        )
        current = current and all(
            fingerprint(root / name) == sha for name, sha in analysis.get("code_sha256", {}).items()
        )
        extra = "data/external/treasury_official/latest.json"
        if extra in analysis["input_sha256"]:
            current = current and fingerprint(root / extra) == analysis["input_sha256"][extra]
        figures = []
        if current:
            directory = manifest_path.parent
            for relative, sha in analysis["file_sha256"].items():
                require(
                    fingerprint(local_path(root, str((directory / relative).relative_to(root))))
                    == sha,
                    "Analysis release output changed: " + relative,
                )
            for name, title, caption in [
                (
                    "r/request_award",
                    "Requested and allowed returns",
                    f"R: {analysis['entered_orders']} entered decisions and {analysis['request_award_pairs']} original request-award pairs.",
                ),
                (
                    "r/evidence_stances",
                    "Evidence categories and stance",
                    "R: counts and shares of Commission-analysis units, with separate order denominators.",
                ),
                (
                    "python/benchmark_coverage",
                    "Exact national benchmark coverage",
                    "Python: verified and missing same-service matches for each proposed order.",
                ),
                (
                    "python/treasury_context",
                    "Awards and the interest-rate environment",
                    "Python: nominal Treasury context and descriptive award-minus-yield differences.",
                ),
            ]:
                if name + ".png" in analysis["file_sha256"]:
                    figures.append(
                        dict(
                            title=title,
                            caption=caption,
                            image_path=str((directory / (name + ".png")).relative_to(root)),
                            pdf_path=str((directory / (name + ".pdf")).relative_to(root)),
                        )
                    )
        payload["analysis"] = dict(
            status="current" if current else "stale_rebuild_required",
            figures=figures,
            manifest_path=str(manifest_path.relative_to(root)),
            r=analysis["r"],
            stata=analysis["stata"],
            treasury_crosscheck=analysis["treasury_crosscheck"],
        )
    template = (root / "presentation/template.html").read_text()
    require(template.count("__RESEARCH_DATA__") == 1, "Overview template needs one data slot")
    for slot in ("__STYLES__", "__APP_SCRIPT__"):
        require(template.count(slot) == 1, "Overview template needs one " + slot + " slot")
    embedded = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("&", "\\u0026")
    )
    target = root / "presentation/index.html"
    styles = root / "presentation/styles.css"
    script = root / "presentation/app.js"
    target.write_text(
        template.replace("__RESEARCH_DATA__", embedded)
        .replace("__STYLES__", styles.read_text())
        .replace("__APP_SCRIPT__", script.read_text())
    )
    project_template = root / "presentation/project.template.html"
    if project_template.is_file():
        from .national_study import render_article
        from .regional_study import render_regional
        from .factor_study import render_article as render_factors

        article = render_regional(root, project_template.read_text(), payload)
        (root / "presentation/project.html").write_text(
            render_factors(root, render_article(root, article))
        )
    audit = dict(
        status="passed",
        as_of=payload["date"],
        counts=payload["stats"],
        input_sha256=payload["inputs"],
        template_sha256=fingerprint(root / "presentation/template.html"),
        output_sha256=fingerprint(target),
        styles_sha256=fingerprint(styles),
        script_sha256=fingerprint(script),
        output_path="presentation/index.html",
        scope="Local candidate evidence explorer; no synthetic records and no final-sample findings.",
    )
    (root / "reports/presentation_build.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(build_overview(), indent=2))


if __name__ == "__main__":
    main()
