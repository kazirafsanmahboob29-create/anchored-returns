"""Retrieve and pin FRED DGS10, then match dates without future observations.

The public CSV endpoint needs no credentials. The official JSON API is optional
when FRED_API_KEY is configured; keys never enter saved URLs or metadata.
"""

from bisect import bisect_right
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import io
import json
import os
from pathlib import Path
from urllib.parse import urlencode

import requests

from .research_ledger import fingerprint, local_path, require

ROOT = Path(__file__).resolve().parents[1]
SERIES_URL = "https://fred.stlouisfed.org/series/DGS10"
CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
API_URL = "https://api.stlouisfed.org/fred/series/observations"


def observations(rows, start, end):
    """Reject unordered, malformed or out-of-period values; preserve missingness."""
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    require(start <= end, "Treasury period is reversed")
    output, previous = [], None
    for day, printed in rows:
        try:
            actual = date.fromisoformat(day)
        except (ValueError, TypeError) as error:
            raise ValueError("Malformed Treasury observation date") from error
        require(start <= actual <= end, "Treasury observation outside requested period")
        require(
            previous is None or actual > previous, "Treasury dates must be unique and ascending"
        )
        previous = actual
        if printed in ("", ".", "NA"):
            value = None
        else:
            try:
                value = Decimal(printed)
            except (InvalidOperation, TypeError) as error:
                raise ValueError("Malformed Treasury yield") from error
            require(
                value.is_finite() and Decimal("-5") <= value <= Decimal("30"),
                "Treasury yield is nonfinite or outside the explicit plausibility check",
            )
        output.append(
            dict(
                date=day,
                printed_percent=printed,
                value_fraction=str(value / 100) if value is not None else None,
            )
        )
    require(
        bool(output) and any(r["value_fraction"] is not None for r in output),
        "Treasury feed has no usable observations",
    )
    return output


def parse_csv(content, start, end):
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    require(
        reader.fieldnames == ["observation_date", "DGS10"],
        "FRED CSV schema changed or server returned non-CSV content",
    )
    rows = []
    for row in reader:
        require(
            set(row) == {"observation_date", "DGS10"} and all(v is not None for v in row.values()),
            "Malformed FRED CSV row",
        )
        rows.append((row["observation_date"], row["DGS10"]))
    return observations(rows, start, end)


def match_date(rows, target_date, *, max_gap_days=7, coverage_end=None):
    """Latest nonmissing observation on/before date, inside snapshot coverage."""
    require(type(max_gap_days) is int and max_gap_days >= 0, "Invalid Treasury gap limit")
    target = date.fromisoformat(target_date)
    days = [date.fromisoformat(r["date"]) for r in rows]
    require(
        bool(days) and days == sorted(set(days)),
        "Treasury snapshot dates must be unique and ascending",
    )
    end = date.fromisoformat(coverage_end) if coverage_end else days[-1]
    require(end >= days[-1], "Treasury coverage end precedes saved observations")
    if target < days[0] or target > end:
        return dict(
            target_date=target_date,
            status="outside_observation_coverage",
            observation_date=None,
            value_fraction=None,
            gap_days=None,
        )
    index = bisect_right(days, target) - 1
    while index >= 0 and rows[index]["value_fraction"] is None:
        index -= 1
    if index < 0:
        return dict(
            target_date=target_date,
            status="no_prior_nonmissing_observation",
            observation_date=None,
            value_fraction=None,
            gap_days=None,
        )
    gap = (target - days[index]).days
    # A stale value remains evidence, but it is withheld from the analytical input.
    return dict(
        target_date=target_date,
        status="matched" if gap <= max_gap_days else "stale_requires_review",
        observation_date=days[index].isoformat(),
        gap_days=gap,
        observed_fraction=rows[index]["value_fraction"],
        value_fraction=rows[index]["value_fraction"] if gap <= max_gap_days else None,
    )


def refresh(root=ROOT, *, start="2010-01-01", end=None, transport="csv", session=None, now=None):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    require(now.tzinfo is not None, "Snapshot time needs a timezone")
    now = now.astimezone(timezone.utc)
    end = end or now.date().isoformat()
    require(
        date.fromisoformat(start) <= date.fromisoformat(end) <= now.date(),
        "Invalid or future Treasury request period",
    )
    require(transport in ("csv", "api"), "Unknown Treasury transport")
    client = session or requests.Session()
    params = {"id": "DGS10", "cosd": start, "coed": end}
    endpoint = CSV_URL
    if transport == "api":
        key = os.environ.get("FRED_API_KEY")
        require(
            bool(key), "FRED API transport needs FRED_API_KEY; public CSV transport needs no key"
        )
        endpoint = API_URL
        params = dict(
            series_id="DGS10",
            observation_start=start,
            observation_end=end,
            file_type="json",
            sort_order="asc",
            limit=100000,
            api_key=key,
        )
    try:
        response = client.get(endpoint, params=params, timeout=(10, 30))
        response.raise_for_status()
    except requests.RequestException:
        # Requests exception URLs can contain credentials. Never expose that text.
        raise ValueError("FRED download failed; retained snapshots remain unchanged") from None
    raw = response.content
    if transport == "csv":
        rows = parse_csv(raw, start, end)
    else:
        data = json.loads(raw)
        require(
            isinstance(data.get("observations"), list)
            and data.get("count") == len(data["observations"]),
            "FRED API returned incomplete observations",
        )
        require(
            data.get("units") == "lin" and data.get("order_by") == "observation_date",
            "Unexpected FRED API transformation",
        )
        rows = observations([(r["date"], r["value"]) for r in data["observations"]], start, end)
    bundle = root / "data/external/treasury" / now.strftime("%Y%m%dT%H%M%S%fZ")
    bundle.mkdir(parents=True, exist_ok=False)
    raw_path = bundle / ("raw.csv" if transport == "csv" else "raw.json")
    normalized = bundle / "observations.json"
    raw_path.write_bytes(raw)
    normalized.write_text(json.dumps(rows, indent=2) + "\n")
    safe_params = {k: v for k, v in params.items() if k != "api_key"}
    report = dict(
        schema_version="1.0",
        provider="Federal Reserve Bank of St. Louis",
        series="DGS10",
        underlying_source="Federal Reserve Board H.15",
        series_url=SERIES_URL,
        transport=transport,
        request_url=endpoint + "?" + urlencode(safe_params),
        requested_start=start,
        requested_end=end,
        retrieved_at_utc=now.isoformat(),
        vintage_kind="retrieval_snapshot_not_point_in_time_history",
        first_observation=rows[0]["date"],
        last_observation=rows[-1]["date"],
        latest_nonmissing=next(r for r in reversed(rows) if r["value_fraction"] is not None),
        rows=len(rows),
        missing=sum(r["value_fraction"] is None for r in rows),
        raw_path=str(raw_path.relative_to(root)),
        raw_sha256=fingerprint(raw_path),
        observations_path=str(normalized.relative_to(root)),
        observations_sha256=fingerprint(normalized),
        notes="Daily percent converted with Decimal to fraction. Historical values may be revised by FRED; this is a retrieval vintage, not information known at each order date.",
    )
    meta_path = bundle / "metadata.json"
    meta_path.write_text(json.dumps(report, indent=2) + "\n")
    pointer = root / "data/external/treasury/latest.json"
    pointer.write_text(
        json.dumps(
            {
                "metadata_path": str(meta_path.relative_to(root)),
                "metadata_sha256": fingerprint(meta_path),
            },
            indent=2,
        )
        + "\n"
    )
    return report


def load_snapshot(root=ROOT):
    root = Path(root).resolve()
    pointer = json.loads((root / "data/external/treasury/latest.json").read_text())
    path = local_path(root, pointer["metadata_path"])
    require(fingerprint(path) == pointer["metadata_sha256"], "Treasury metadata changed")
    meta = json.loads(path.read_text())
    require(
        meta["series"] == "DGS10" and meta["transport"] in ("csv", "api"),
        "Unexpected Treasury snapshot series or transport",
    )
    raw = local_path(root, meta["raw_path"])
    normalized = local_path(root, meta["observations_path"])
    require(
        fingerprint(raw) == meta["raw_sha256"]
        and fingerprint(normalized) == meta["observations_sha256"],
        "Treasury snapshot changed",
    )
    rows = json.loads(normalized.read_text())
    if meta["transport"] == "csv":
        actual = parse_csv(raw.read_bytes(), meta["requested_start"], meta["requested_end"])
    else:
        data = json.loads(raw.read_text())
        actual = observations(
            [(r["date"], r["value"]) for r in data["observations"]],
            meta["requested_start"],
            meta["requested_end"],
        )
    require(
        actual == rows
        and len(rows) == meta["rows"]
        and sum(r["value_fraction"] is None for r in rows) == meta["missing"],
        "Treasury normalization or counts differ",
    )
    require(
        meta["first_observation"] == rows[0]["date"]
        and meta["last_observation"] == rows[-1]["date"]
        and meta["latest_nonmissing"]
        == next(r for r in reversed(rows) if r["value_fraction"] is not None),
        "Treasury summary differs from source observations",
    )
    return meta, rows


def order_dates(root):
    """Preserved original candidate dates; subsequent events are separate."""
    catalog = json.loads((root / "data/research/source_catalog.json").read_text())
    allowed = {s["source_id"]: s for s in catalog["sources"]}
    baseline = json.loads((root / "data/research/assistant_verified_case_facts.json").read_text())
    result = {}
    for f in baseline["facts"]:
        sid = f["case_id"]
        if sid in allowed:
            original = allowed[sid].get("order_date")
            require(original, "Candidate source lacks original written date")
            result[sid] = original
    ledger = json.loads((root / "data/research/empirical_ledger_v0.1.3.json").read_text())
    for case in ledger["cases"]:
        if case["case_id"] in result:
            require(result[case["case_id"]] == case["order_date"], "Original written date conflict")
        result[case["case_id"]] = case["order_date"]
    return result


def join_orders(root=ROOT, *, write=False):
    root = Path(root).resolve()
    meta, rows = load_snapshot(root)
    joins = [
        dict(
            case_id=cid,
            event="original_written_order",
            **match_date(rows, day, coverage_end=meta["requested_end"]),
        )
        for cid, day in sorted(order_dates(root).items())
    ]
    report = dict(
        schema_version="1.0",
        source_url=SERIES_URL,
        retrieved_at_utc=meta["retrieved_at_utc"],
        observations_sha256=meta["observations_sha256"],
        n_orders=len(joins),
        matched=sum(j["status"] == "matched" for j in joins),
        joins=joins,
        prior_current_intervals=0,
        missing_prior_dates="Prior original decision links remain unresolved; no interval or pass-through regression is calculated.",
    )
    if write:
        path = root / "data/research/treasury_order_joins.json"
        path.write_text(json.dumps(report, indent=2) + "\n")
    return report
