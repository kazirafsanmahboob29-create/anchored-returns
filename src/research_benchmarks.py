"""Comparable national benchmarks with exact half-year, scope and vintage checks."""

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

import pymupdf

from .research_ledger import fingerprint, local_path, require
from .rra_reconstruction import reconstruct_2019


def benchmark_percent(record):
    """Keep calculated display values distinct from publisher-printed values."""
    return record.get("display_percent") or record["printed_percent"]


def previous_half_year(order_date):
    d = date.fromisoformat(order_date)
    if d.month >= 7:
        return f"{d.year}-01-01", f"{d.year}-06-30"
    return f"{d.year - 1}-07-01", f"{d.year - 1}-12-31"


def join_benchmarks(candidates, records):
    keys = [(r["service"], r["period_start"], r["period_end"]) for r in records]
    require(len(keys) == len(set(keys)), "Ambiguous benchmark vintage for service and half-year")
    lookup = dict(zip(keys, records))
    joins = []
    for c in candidates:
        start, end = previous_half_year(c["order_date"])
        for service in c["services"]:
            require(service in ("Electric", "Gas"), "Unknown benchmark service")
            r = lookup.get((service, start, end))
            joins.append(
                dict(
                    candidate_id=c["candidate_id"],
                    service=service,
                    order_date=c["order_date"],
                    required_period_start=start,
                    required_period_end=end,
                    status="matched" if r else "missing_exact_comparable_half_year",
                    value_fraction=r["value_fraction"] if r else None,
                    printed_percent=r.get("printed_percent") if r else None,
                    display_percent=benchmark_percent(r) if r else None,
                    estimation_method=r.get("estimation_method", "publisher_reported")
                    if r
                    else None,
                    benchmark_id=r["benchmark_id"] if r else None,
                    published_date=r["published_date"] if r else None,
                    available_at_written_date=r["published_date"] <= c["order_date"] if r else None,
                    reason=""
                    if r
                    else "No verified same-service, rider-excluded record for the required half-year. Annual and trailing-year means are not substituted.",
                )
            )
    return joins


def benchmark_report(root, candidates):
    root = Path(root)
    path = root / "data/external/rra_historical_benchmarks.json"
    data = json.loads(path.read_text())
    records = data["records"]
    require(
        len({r["benchmark_id"] for r in records}) == len(records), "Duplicate benchmark identity"
    )
    sources = {s["source_id"]: s for s in data["sources"]}
    require(len(sources) == len(data["sources"]), "Duplicate benchmark source")
    docs = {}
    try:
        for r in records:
            require(
                r["service"] in ("Electric", "Gas") and r["riders_excluded"] is True,
                "Benchmark must exclude riders and identify its service",
            )
            require(
                r["statistic"] == "mean_authorized_roe"
                and r["dataset_version"] == "legacy_major_rate_case_coverage",
                "Benchmark statistic or dataset version differs",
            )
            start, end = date.fromisoformat(r["period_start"]), date.fromisoformat(r["period_end"])
            require(
                start.year == end.year
                and (start.month, start.day, end.month, end.day) in ((1, 1, 6, 30), (7, 1, 12, 31)),
                "Benchmark must describe one complete half-year",
            )
            require(
                end
                < date.fromisoformat(r["published_date"])
                <= date.fromisoformat(data["checked_date"]),
                "Benchmark publication date is inconsistent",
            )
            try:
                printed, fraction = Decimal(benchmark_percent(r)), Decimal(r["value_fraction"])
            except (InvalidOperation, TypeError) as error:
                raise ValueError("Invalid benchmark decimal") from error
            require(
                printed.is_finite()
                and fraction.is_finite()
                and 0 < fraction < 1
                and printed / 100 == fraction,
                "Benchmark percent conversion differs",
            )
            sid = r["source_id"]
            require(sid in sources, "Missing benchmark source")
            s = sources[sid]
            require(
                r["published_date"] == s["published_date"]
                and date.fromisoformat(s["data_compiled_date"])
                <= date.fromisoformat(s["published_date"]),
                "Benchmark source vintage differs",
            )
            if sid not in docs:
                p = local_path(root, s["pdf_path"])
                require(fingerprint(p) == s["pdf_sha256"], "Benchmark source fingerprint changed")
                docs[sid] = pymupdf.open(p)
                require(len(docs[sid]) == s["n_pages"], "Benchmark page count differs")
            e = r["evidence"]
            require(
                type(e["page"]) is int and 1 <= e["page"] <= len(docs[sid]),
                "Invalid benchmark evidence page",
            )
            text = docs[sid][e["page"] - 1].get_text("text", sort=False)
            a, b = e["start_char"], e["end_char"]
            require(
                type(a) is int and type(b) is int and 0 <= a < b <= len(text),
                "Invalid benchmark offsets",
            )
            require(text[a:b] == e["exact_text"], "Benchmark evidence differs")
            method = r.get("estimation_method", "publisher_reported")
            if method == "publisher_reported":
                require(r["printed_percent"] in e["exact_text"], "Benchmark evidence differs")
                require(
                    r.get("display_percent", r["printed_percent"]) == r["printed_percent"],
                    "Publisher display value differs from printed mean",
                )
            elif method == "case_level_reconstruction":
                require(
                    r.get("printed_percent") is None,
                    "Calculated mean cannot be labeled publisher printed",
                )
                require(
                    s["published_date"] == "2020-01-31" and s["data_compiled_date"] == "2020-01-29",
                    "Reconstruction report vintage differs from original",
                )
                calc = r["reconstruction"]
                cp = local_path(root, calc["path"])
                require(fingerprint(cp) == calc["sha256"], "Reconstruction file changed")
                case_data = json.loads(cp.read_text())
                require(
                    case_data["source_id"] == sid and case_data["pdf_sha256"] == s["pdf_sha256"],
                    "Reconstruction source differs",
                )
                expected = reconstruct_2019(
                    docs[sid], case_data["rows"], r["service"], r["period_start"], r["period_end"]
                )
                require(
                    calc["result"] == expected
                    and r["display_percent"] == expected["display_percent"],
                    "Reconstructed mean or included rows differ",
                )
                for visual in case_data["visual_checks"]:
                    require(
                        fingerprint(local_path(root, visual["path"])) == visual["sha256"]
                        and visual["reviewer"]
                        and visual["checked_date"] <= data["checked_date"],
                        "Reconstruction visual evidence differs",
                    )
                require(
                    {v["page"] for v in case_data["visual_checks"]} == {29, 38, 39, 40, 41},
                    "Reconstruction lacks complete table and control visual reviews",
                )
            else:
                raise ValueError("Unknown benchmark estimation method")
            v = r["visual_check"]
            require(
                v["page"] == e["page"] and fingerprint(local_path(root, v["path"])) == v["sha256"],
                "Benchmark visual evidence changed",
            )
            require(
                v.get("reviewer")
                and date.fromisoformat(v["checked_date"])
                <= date.fromisoformat(data["checked_date"]),
                "Missing or future benchmark visual review",
            )
    finally:
        for doc in docs.values():
            doc.close()
    for unresolved in data["unresolved_sources"]:
        pdf = local_path(root, unresolved["pdf_path"])
        require(fingerprint(pdf) == unresolved["pdf_sha256"], "Unresolved access response changed")
        with pymupdf.open(pdf) as doc:
            require(len(doc) == unresolved["n_pages"], "Unresolved response page count differs")
    joins = join_benchmarks(candidates, records)
    matched = Counter(j["candidate_id"] for j in joins if j["status"] == "matched")
    fully_matched = sum(matched[c["candidate_id"]] == len(c["services"]) for c in candidates)
    return dict(
        status="partial_verified_series",
        checked_date=data["checked_date"],
        verified_records=len(records),
        verified_half_years=sorted(
            {
                r["period_start"][:4] + ("-H1" if r["period_start"][5:7] == "01" else "-H2")
                for r in records
            }
        ),
        reconstructed_records=sum(
            r.get("estimation_method") == "case_level_reconstruction" for r in records
        ),
        proposed_orders=len(candidates),
        orders_with_all_services_matched=fully_matched,
        service_rows=len(joins),
        matched_service_rows=sum(j["status"] == "matched" for j in joins),
        joins=joins,
        records=records,
        sources=data["sources"],
        unresolved_sources=data["unresolved_sources"],
        registry_sha256=fingerprint(path),
    )
