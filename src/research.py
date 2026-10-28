"""One entry point for the project status, evidence checks and source refresh."""

import argparse
import json
from pathlib import Path

from .research_ledger import validate_ledger, require
from .research_overview import overview_payload, build_overview
from .treasury import load_snapshot, refresh, join_orders
from .research_sample import sample_report
from .research_benchmarks import benchmark_report
from .research_reliability import build_packet, evaluate_ratings, export_rater_kit, rating_preflight
from .treasury_crosscheck import refresh_crosscheck, load_crosscheck

ROOT = Path(__file__).resolve().parents[1]


def status(root=ROOT):
    payload = overview_payload(root)
    access = dict(
        order_pdfs="Original PDFs have been screened; the complete six-state census remains unfinished.",
        treasury="Not yet connected",
        fred_api="Optional keyed transport; public CSV needs no key.",
        national_benchmarks=f"Verified historical benchmarks cover {len(payload['benchmarks']['verified_half_years'])} half-years, including complete-table reconstructions; the comparable series remains incomplete.",
        reliability=payload["reliability"]["status"],
    )
    pointer = Path(root) / "data/external/treasury/latest.json"
    if pointer.exists():
        meta, _ = load_snapshot(root)
        access["treasury"] = dict(
            status="connected",
            transport=meta["transport"],
            retrieved_at_utc=meta["retrieved_at_utc"],
            latest=meta["latest_nonmissing"],
        )
    return dict(
        as_of=payload["date"],
        sample_frame_cutoff="2026-10-01",
        software="M1–M8 complete",
        counts=payload["stats"],
        data_access=access,
        sample_blockers=payload["sample"]["blockers"],
        benchmark_coverage=dict(
            values=payload["benchmarks"]["verified_records"],
            reconstructed_values=payload["benchmarks"]["reconstructed_records"],
            half_years=payload["benchmarks"]["verified_half_years"],
            fully_matched_proposed_orders=payload["benchmarks"]["orders_with_all_services_matched"],
        ),
        cohort=payload.get("cohort")
        and {
            k: payload["cohort"][k]
            for k in ("version", "status", "primary", "supplemental", "total", "census_complete")
        },
        next_steps=[
            "Extend numeric coverage and complete-section coding within the documented order cohort.",
            "Complete original prior-order links and half-year national benchmarks.",
            "Continue complete-section coding and record genuinely separate reliability observations.",
        ],
    )


def check(root=ROOT, *, full=False):
    root = Path(root)
    payload = overview_payload(root)  # Validates catalog and historical numeric provenance too.
    empirical = validate_ledger(root / "data/research/empirical_ledger_v0.1.3.json", root=root)
    result = dict(
        status="passed",
        empirical=empirical,
        source_documents=payload["stats"]["documents"],
        historical_facts=payload["stats"]["facts"] - empirical["n_new_numeric_facts"],
    )
    result["sample"] = {k: v for k, v in payload["sample"].items() if k != "candidates"}
    result["benchmarks"] = {
        k: v
        for k, v in payload["benchmarks"].items()
        if k not in ("records", "sources", "joins", "unresolved_sources")
    }
    result["reliability"] = payload["reliability"]
    if (root / "data/external/treasury/latest.json").exists():
        expected = join_orders(root)
        actual = json.loads((root / "data/research/treasury_order_joins.json").read_text())
        require(
            actual == expected, "Treasury order joins are stale or changed; run refresh-treasury"
        )
        result["treasury"] = dict(
            orders=expected["n_orders"],
            matched=expected["matched"],
            snapshot=expected["retrieved_at_utc"],
        )
    crosscheck = load_crosscheck(root)
    if crosscheck:
        result["treasury_second_source"] = dict(
            overlapping_dates=crosscheck["overlapping_dates"],
            equal=crosscheck["equal"],
            disagreements=crosscheck["disagreements"],
            orders=len(crosscheck["order_checks"]),
        )
    factor_path = root / "reports/factor-study/study.json"
    if factor_path.exists():
        from .factor_study import digest

        factor = json.loads(factor_path.read_text())
        require(
            all(
                digest(root / name) == expected for name, expected in factor["input_sha256"].items()
            ),
            "Factor inputs changed; rebuild factors",
        )
        artifacts = json.loads((factor_path.parent / "artifact-manifest.json").read_text())
        require(
            all(
                digest(factor_path.parent / name) == expected
                for name, expected in artifacts["files"].items()
            ),
            "Factor artifacts changed; rerun checks and package",
        )
        result["factors"] = dict(
            status="passed",
            complete_observations=factor["coverage"]["complete"],
            main_specifications=len(factor["models"]),
            checks=len(factor["sensitivity"]),
            r_validation=artifacts["r_validation"],
        )
    if full:
        import pymupdf
        from .manifest import read_manifest
        from scripts.audit_project import audit

        result["m1_m8"] = audit()
        catalog = {s["source_id"]: s for s in payload["sources"]}
        pages_checked = 0
        for record in read_manifest(root / "data/empirical_manifest.csv"):
            source = catalog[record["case_id"]]
            require(
                record["sha256"] == source["pdf_sha256"]
                and int(record["n_pages"]) == source["n_pages"]
                and Path(record["file_path"]).resolve() == (root / source["pdf_path"]).resolve()
                and all(
                    record[key] == source[key]
                    for key in ("state", "docket", "source_url", "download_date")
                ),
                "Empirical manifest differs from catalog",
            )
            text_path = root / "data/empirical_text" / (record["case_id"] + ".json")
            saved = json.loads(text_path.read_text())
            with pymupdf.open(record["file_path"]) as doc:
                require(len(doc) == len(saved) == source["n_pages"], "Empirical page count changed")
                for n, (row, page) in enumerate(zip(saved, doc), 1):
                    actual = page.get_text("text", sort=False)
                    require(
                        row["page"] == n
                        and row["text"] == actual
                        and row["n_chars"] == len(actual)
                        and row["likely_scanned"] == (len("".join(actual.split())) < 80),
                        "Empirical native text no longer reproduces",
                    )
                    pages_checked += 1
        result["empirical_native_pages_recomputed"] = pages_checked
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Current research coverage and source access")
    server = sub.add_parser(
        "serve", help="Run the local research site with source refresh and downloads"
    )
    server.add_argument("--port", type=int, default=8765)
    server.add_argument(
        "--snapshot",
        action="store_true",
        help="Serve the included release without rebuilding document evidence",
    )
    verify = sub.add_parser("check", help="Read-only evidence and source integrity checks")
    verify.add_argument(
        "--full",
        action="store_true",
        help="Also reproduce saved M1–M8 work and every newly extracted page",
    )
    sub.add_parser("overview", help="Rebuild the local evidence explorer from verified records")
    sub.add_parser(
        "sample", help="Verify screening evidence and the quota-constrained proposed sample"
    )
    sub.add_parser(
        "benchmarks", help="Verify historical report evidence and exact half-year coverage"
    )
    sub.add_parser(
        "sources", help="Audit source connections, contextual reports and state census progress"
    )
    preflight = sub.add_parser(
        "ratings-check", help="Check a draft or completed rating file without calculating agreement"
    )
    preflight.add_argument(
        "ratings", help="Draft or completed rating JSON from the frozen coding workspace"
    )
    sub.add_parser(
        "verify-treasury",
        help="Download official Treasury XML and compare it with the pinned FRED snapshot",
    )
    analysis = sub.add_parser(
        "analyze", help="Export real CSV/DTA tables and generate Python and available R figures"
    )
    analysis.add_argument("--output", help="New output directory; existing releases are preserved")
    analysis.add_argument("--rscript", help="Path to an installed Rscript executable")
    analysis.add_argument(
        "--skip-r", action="store_true", help="Export tables and Python figures without running R"
    )
    sub.add_parser(
        "national", help="Build the national electric rate-case study and period comparisons"
    )
    sub.add_parser(
        "factors", help="Build the economic panel, correlations, regressions and temporal holdout"
    )
    sub.add_parser(
        "reliability-packet", help="Build or verify the frozen independent coding workspace"
    )
    kit = sub.add_parser(
        "reliability-kit",
        help="Export a portable blinded ZIP with definitions and blank rating controls",
    )
    kit.add_argument("--output", required=True, help="New ZIP file; existing files are preserved")
    ratings = sub.add_parser(
        "reliability-check", help="Evaluate completed, separately recorded ratings"
    )
    ratings.add_argument("ratings", help="Completed rating JSON exported by the coding workspace")
    ratings.add_argument(
        "--second-ratings", help="Second completed human file for human inter-rater agreement"
    )
    ratings.add_argument(
        "--output", help="Save the result to a new JSON file; existing files are preserved"
    )
    acquire = sub.add_parser(
        "acquire", help="Acquire, register and extract one reviewed official link"
    )
    acquire.add_argument("source_id", help="ID listed in data/research/source_queue.json")
    source = sub.add_parser(
        "refresh-treasury", help="Download a new FRED snapshot and match original written dates"
    )
    source.add_argument("--start", default="2010-01-01")
    source.add_argument("--end")
    source.add_argument("--transport", choices=["csv", "api"], default="csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            from .research_server import serve

            serve(ROOT, port=args.port, prepare=not args.snapshot)
            return 0
        elif args.command == "status":
            result = status()
        elif args.command == "check":
            result = check(full=args.full)
        elif args.command == "overview":
            result = build_overview()
        elif args.command == "sample":
            result = sample_report(ROOT)
        elif args.command == "benchmarks":
            result = benchmark_report(ROOT, sample_report(ROOT)["candidates"])
        elif args.command == "sources":
            result = overview_payload(ROOT)["audit"]
        elif args.command == "ratings-check":
            result = rating_preflight(ROOT, args.ratings)
        elif args.command == "verify-treasury":
            result = refresh_crosscheck(ROOT)
        elif args.command == "national":
            from .national_study import build

            study = build(ROOT)
            result = {k: study[k] for k in ("as_of", "coverage", "periods", "comparisons")}
        elif args.command == "factors":
            from .factor_study import build

            study = build(ROOT)
            result = {k: study[k] for k in ("coverage", "models", "sensitivity", "holdout")}
        elif args.command == "analyze":
            from .research_analysis import analyze

            report = analyze(ROOT, output=args.output, rscript=args.rscript, run_r=not args.skip_r)
            result = {
                k: report[k]
                for k in (
                    "output_path",
                    "entered_orders",
                    "request_award_pairs",
                    "coded_orders",
                    "commission_units",
                    "source_records",
                    "r",
                    "stata",
                )
            }
            result["status"] = "generated"
            if args.output is None:
                result["overview"] = build_overview()
        elif args.command == "reliability-packet":
            result = build_packet(ROOT)
        elif args.command == "reliability-kit":
            result = export_rater_kit(ROOT, args.output)
        elif args.command == "reliability-check":
            result = evaluate_ratings(ROOT, args.ratings, args.second_ratings)
            if args.output:
                with Path(args.output).open("x") as output:
                    output.write(json.dumps(result, indent=2) + "\n")
        elif args.command == "acquire":
            from .source_acquisition import acquire

            result = acquire(args.source_id)
            result["overview"] = build_overview()
        else:
            meta = refresh(start=args.start, end=args.end, transport=args.transport)
            result = dict(
                snapshot=meta, order_joins=join_orders(write=True), overview=build_overview()
            )
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Research command failed: {error}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
