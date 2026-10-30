"""Preserve official economic histories for the dated historical expansion."""

import argparse
import csv
import hashlib
import io
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import requests

from src.eei_benchmarks import read_workbook
from src.national_study import enrich

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("data/external/expanded_2026-10-28")
START, END = "1980-01-01", "2024-12-31"
CORE = ("DGS10", "T10Y3M", "CPIAUCNS", "STLFSI4")
REGIONS = {
    "Northeast": "CT ME MA NH RI VT NJ NY PA",
    "Midwest": "IN IL MI OH WI IA KS MN MO NE ND SD",
    "South": "DE DC FL GA MD NC SC VA WV AL KY MS TN AR LA OK TX",
    "West": "AZ CO ID MT NV NM UT WY AK CA HI OR WA",
}
STATE_URL = "https://www2.census.gov/geo/docs/reference/state.txt"
REGION_URL = (
    "https://www.census.gov/programs-surveys/economic-census/guidance-geographies/levels.html"
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_csv(raw, series):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames not in (["observation_date", series], ["DATE", series]):
        raise ValueError("Wrong economic series: " + series)
    rows = list(reader)
    days = [r.get("observation_date", r.get("DATE")) for r in rows]
    if not days or days != sorted(set(days)):
        raise ValueError("Economic dates must be nonempty, unique and sorted")
    numeric = 0
    for row, day in zip(rows, days):
        datetime.strptime(day, "%Y-%m-%d")
        if not START <= day <= END:
            raise ValueError("Source date lies outside the requested historical window")
        value = row[series]
        if value not in ("", "."):
            number = float(value)
            if not -100 < number < 1000:
                raise ValueError("Nonfinite or out-of-range economic value")
            if series.endswith("UR") and not 0 <= number <= 100:
                raise ValueError("State unemployment must be a percentage between zero and 100")
            numeric += 1
        if (series.endswith("UR") or series == "CPIAUCNS") and not day.endswith("-01"):
            raise ValueError("Monthly histories must use first-of-month reference dates")
    if numeric < 100:
        raise ValueError("Economic history is unexpectedly short: " + series)
    return {
        "rows": len(rows),
        "numeric_rows": numeric,
        "first_date": days[0],
        "last_date": days[-1],
    }


def acquire(root=ROOT, output=None):
    root = Path(root)
    output = Path(output) if output is not None else root / SOURCE
    marker = output / "manifest.json"
    if marker.exists():
        saved = json.loads(marker.read_text())
        if saved.get("schema") != "anchored-returns-expanded-sources/1":
            raise ValueError("Unrecognized economic source archive")
        for name, expected in saved["files"].items():
            if digest((output / name).read_bytes()) != expected:
                raise ValueError("Saved economic input changed: " + name)
        return saved
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a fresh source directory; a previous retrieval is incomplete")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish only after the entire retrieval succeeds. A failure leaves no snapshot.
    with tempfile.TemporaryDirectory(prefix=".economic-retrieval-", dir=output.parent) as stage:
        staged = Path(stage) / "snapshot"
        result = _retrieve(root, staged)
        staged.rename(output)
        return result


def _retrieve(root, output):
    output.mkdir()
    marker = output / "manifest.json"
    response = requests.get(STATE_URL, timeout=60)
    response.raise_for_status()
    state_raw = response.content
    state_rows = list(csv.DictReader(io.StringIO(state_raw.decode()), delimiter="|"))
    if not state_rows or set(state_rows[0]) != {"STATE", "STUSAB", "STATE_NAME", "STATENS"}:
        raise ValueError("Census state schema changed")
    by_name = {r["STATE_NAME"]: r for r in state_rows}
    rows, _ = read_workbook(root / "data/external/eei/eei_rate_review_2025_q3.xlsx")
    states = sorted({r["state"] for r in enrich(rows, []) if 1985 <= r["year"] <= 2024})
    region_by_postal = {code: region for region, codes in REGIONS.items() for code in codes.split()}
    mapping = []
    for state in states:
        record = by_name[state]
        postal = record["STUSAB"]
        mapping.append(
            {
                "state": state,
                "postal": postal,
                "fips": record["STATE"],
                "region": region_by_postal[postal],
                "series_id": postal + "UR",
            }
        )
    (output / "census_state.txt").write_bytes(state_raw)
    (output / "state_mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    specs = [
        (
            s,
            "macro",
            "Federal Reserve Board"
            if s == "DGS10"
            else "U.S. Bureau of Labor Statistics"
            if s == "CPIAUCNS"
            else "Federal Reserve Bank of St. Louis",
        )
        for s in CORE
    ]
    specs += [(r["series_id"], "states", "U.S. Bureau of Labor Statistics") for r in mapping]

    def fetch(spec):
        series, folder, agency = spec
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={START}&coed={END}"
        result = requests.get(url, timeout=90)
        result.raise_for_status()
        raw = result.content
        coverage = validate_csv(raw, series)
        record = {
            "series_id": series,
            "provider": agency,
            "distributor": "FRED",
            "url": url,
            "definition_url": "https://fred.stlouisfed.org/series/" + series,
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "sha256": digest(raw),
            "bytes": len(raw),
            "http_status": result.status_code,
            "content_type": result.headers.get("Content-Type"),
            **coverage,
        }
        target = output / folder
        target.mkdir(exist_ok=True)
        (target / (series + ".csv")).write_bytes(raw)
        (target / (series + ".metadata.json")).write_text(json.dumps(record, indent=2) + "\n")
        return {"path": folder + "/" + series + ".csv", **record}

    with ThreadPoolExecutor(max_workers=4) as pool:
        histories = list(pool.map(fetch, specs))
    files = {
        p.relative_to(output).as_posix(): digest(p.read_bytes())
        for p in sorted(output.rglob("*"))
        if p.is_file()
    }
    manifest = {
        "schema": "anchored-returns-expanded-sources/1",
        "requested_start": START,
        "requested_end": END,
        "state_source_url": STATE_URL,
        "region_definition_url": REGION_URL,
        "states": len(mapping),
        "series": sorted(histories, key=lambda r: r["series_id"]),
        "files": files,
    }
    marker.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="New directory for a separate retrieval vintage"
    )
    args = parser.parse_args()
    result = acquire(output=args.output)
    print(
        json.dumps(
            {
                "states": result["states"],
                "series": len(result["series"]),
                "numeric_observations": sum(r["numeric_rows"] for r in result["series"]),
            }
        )
    )
