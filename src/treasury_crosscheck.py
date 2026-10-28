"""Compare pinned FRED observations with a separate official Treasury XML feed."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from urllib.parse import urlencode, urlparse
import xml.etree.ElementTree as ET

import requests

from .research_ledger import fingerprint, local_path, require
from .treasury import ROOT, load_snapshot, join_orders

ENDPOINT = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
DOCUMENTATION = "https://home.treasury.gov/treasury-daily-interest-rate-xml-feed"
ATOM = "{http://www.w3.org/2005/Atom}"
DATA = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
META = "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}"


def parse_xml(raw, year, checked_date):
    try:
        feed = ET.fromstring(raw)
    except ET.ParseError as error:
        raise ValueError("Treasury returned malformed XML") from error
    require(
        feed.tag == ATOM + "feed"
        and feed.findtext(ATOM + "title") == "DailyTreasuryYieldCurveRateData",
        "Treasury feed identity changed",
    )
    rows = []
    for entry in feed.findall(ATOM + "entry"):
        props = entry.find(ATOM + "content/" + META + "properties")
        require(props is not None, "Treasury XML properties missing")
        day = props.findtext(DATA + "NEW_DATE")
        node = props.find(DATA + "BC_10YEAR")
        require(day and node is not None, "Treasury ten-year field missing")
        actual = date.fromisoformat(day[:10])
        require(
            actual.year == year and actual <= date.fromisoformat(checked_date),
            "Treasury XML date outside the requested year or in the future",
        )
        value = None if node.get(META + "null") == "true" else node.text
        if value is not None:
            amount = Decimal(value)
            require(
                amount.is_finite() and Decimal("-5") <= amount <= Decimal("30"),
                "Invalid Treasury XML yield",
            )
        rows.append(
            dict(
                date=actual.isoformat(),
                printed_percent=value,
                value_fraction=str(Decimal(value) / 100) if value is not None else None,
            )
        )
    require(
        rows and len({r["date"] for r in rows}) == len(rows),
        "Empty or duplicated Treasury XML observations",
    )
    return sorted(rows, key=lambda r: r["date"])


def compare(fred, treasury):
    """Compare each date once. Missingness and source disagreement remain explicit."""
    for rows in (fred, treasury):
        require(len({r["date"] for r in rows}) == len(rows), "Duplicate comparison date")
    left, right = ({r["date"]: r for r in rows} for rows in (fred, treasury))
    output = []
    for day in sorted(set(left) & set(right)):
        f, t = left[day]["value_fraction"], right[day]["value_fraction"]
        difference = None if f is None or t is None else str((Decimal(t) - Decimal(f)) * 10000)
        status = (
            "missing_value"
            if difference is None
            else ("equal" if Decimal(difference) == 0 else "disagreement")
        )
        output.append(
            dict(
                date=day,
                fred_fraction=f,
                treasury_fraction=t,
                treasury_minus_fred_bp=difference,
                status=status,
            )
        )
    return output


def refresh_crosscheck(root=ROOT, *, now=None):
    root = Path(root).resolve()
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    fred_meta, fred = load_snapshot(root)
    joins = join_orders(root)["joins"]
    years = sorted(
        {int(j["target_date"][:4]) for j in joins}
        | {int(fred_meta["latest_nonmissing"]["date"][:4])}
    )
    bundle = root / "data/external/treasury_official" / now.strftime("%Y%m%dT%H%M%S%fZ")

    def fetch(year):
        params = dict(data="daily_treasury_yield_curve", field_tdr_date_value=year)
        try:
            response = requests.get(ENDPOINT, params=params, timeout=(10, 30))
            response.raise_for_status()
        except requests.RequestException:
            raise ValueError(
                "Official Treasury download failed; saved snapshots remain unchanged"
            ) from None
        require(
            urlparse(response.url).hostname == "home.treasury.gov", "Unexpected Treasury redirect"
        )
        raw = response.content
        return (
            year,
            raw,
            parse_xml(raw, year, now.date().isoformat()),
            ENDPOINT + "?" + urlencode(params),
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        downloads = list(pool.map(fetch, years))
    bundle.mkdir(parents=True, exist_ok=False)
    sources, observations = [], []
    for year, raw, rows, url in downloads:
        path = bundle / f"{year}.xml"
        path.write_bytes(raw)
        sources.append(
            dict(
                year=year,
                request_url=url,
                raw_path=str(path.relative_to(root)),
                raw_sha256=fingerprint(path),
                rows=len(rows),
            )
        )
        observations.extend(rows)
    observations.sort(key=lambda r: r["date"])
    normalized = bundle / "observations.json"
    normalized.write_text(json.dumps(observations, indent=2) + "\n")
    comparisons = compare(fred, observations)
    matches = {r["date"]: r for r in comparisons}
    order_checks = [
        dict(
            case_id=j["case_id"],
            target_date=j["target_date"],
            observation_date=j.get("observation_date"),
            comparison=matches.get(j.get("observation_date")),
        )
        for j in joins
    ]
    report = dict(
        schema_version="1.0",
        provider="U.S. Department of the Treasury",
        variable="Daily Treasury Par Yield Curve Rates, BC_10YEAR",
        documentation_url=DOCUMENTATION,
        retrieved_at_utc=now.isoformat(),
        vintage_kind="retrieval_snapshot_not_point_in_time_history",
        checked_date=now.date().isoformat(),
        sources=sources,
        observations_path=str(normalized.relative_to(root)),
        observations_sha256=fingerprint(normalized),
        fred_raw_sha256=fred_meta["raw_sha256"],
        fred_observations_sha256=fred_meta["observations_sha256"],
        overlapping_dates=len(comparisons),
        equal=sum(r["status"] == "equal" for r in comparisons),
        disagreements=[r for r in comparisons if r["status"] == "disagreement"],
        missing_value_dates=sum(r["status"] == "missing_value" for r in comparisons),
        order_checks=order_checks,
        notes="Separate official dissemination paths for nominal ten-year yields. Agreement is a data check, not independent coding reliability or historical real-time availability. Disagreements are retained; neither source overwrites the other.",
    )
    meta = bundle / "metadata.json"
    meta.write_text(json.dumps(report, indent=2) + "\n")
    (bundle.parent / "latest.json").write_text(
        json.dumps(
            dict(metadata_path=str(meta.relative_to(root)), metadata_sha256=fingerprint(meta)),
            indent=2,
        )
        + "\n"
    )
    return dict(
        report,
        latest_nonmissing=next(
            r for r in reversed(observations) if r["value_fraction"] is not None
        ),
    )


def load_crosscheck(root=ROOT):
    root = Path(root).resolve()
    pointer = root / "data/external/treasury_official/latest.json"
    if not pointer.exists():
        return None
    saved = json.loads(pointer.read_text())
    meta = local_path(root, saved["metadata_path"])
    require(fingerprint(meta) == saved["metadata_sha256"], "Treasury cross-check metadata changed")
    report = json.loads(meta.read_text())
    rows = []
    for source in report["sources"]:
        path = local_path(root, source["raw_path"])
        require(fingerprint(path) == source["raw_sha256"], "Official Treasury XML changed")
        actual = parse_xml(path.read_bytes(), source["year"], report["checked_date"])
        require(len(actual) == source["rows"], "Official Treasury row count differs")
        rows.extend(actual)
    rows.sort(key=lambda r: r["date"])
    normalized = local_path(root, report["observations_path"])
    require(
        fingerprint(normalized) == report["observations_sha256"]
        and json.loads(normalized.read_text()) == rows,
        "Official Treasury normalization differs",
    )
    fred_meta, fred = load_snapshot(root)
    require(
        fred_meta["raw_sha256"] == report["fred_raw_sha256"]
        and fred_meta["observations_sha256"] == report["fred_observations_sha256"],
        "Treasury cross-check is stale; run verify-treasury after refreshing FRED",
    )
    actual = compare(fred, rows)
    require(
        report["overlapping_dates"] == len(actual)
        and report["equal"] == sum(r["status"] == "equal" for r in actual)
        and report["disagreements"] == [r for r in actual if r["status"] == "disagreement"]
        and report["missing_value_dates"] == sum(r["status"] == "missing_value" for r in actual),
        "Treasury comparison differs",
    )
    lookup = {r["date"]: r for r in actual}
    expected = [
        dict(
            case_id=j["case_id"],
            target_date=j["target_date"],
            observation_date=j.get("observation_date"),
            comparison=lookup.get(j.get("observation_date")),
        )
        for j in join_orders(root)["joins"]
    ]
    require(expected == report["order_checks"], "Treasury order cross-check differs")
    return dict(
        report, latest_nonmissing=next(r for r in reversed(rows) if r["value_fraction"] is not None)
    )
