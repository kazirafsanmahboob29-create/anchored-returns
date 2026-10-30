"""Preserve the Alabama history needed by the additional pre-1985 cases."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import requests

from scripts.fetch_expanded_sources import digest, validate_csv

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("data/external/filing_2026-10-30")
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=ALUR&cosd=1980-01-01&coed=2024-12-31"


def acquire(root=ROOT):
    output = Path(root) / OUTPUT
    if (output / "manifest.json").exists():
        manifest = json.loads((output / "manifest.json").read_text())
        if manifest.get("schema") != "anchored-returns-filing-sources/1":
            raise ValueError("Unrecognized filing source archive")
        if digest((output / "ALUR.csv").read_bytes()) != manifest["sha256"]:
            raise ValueError("Alabama source fingerprint changed")
        validate_csv((output / "ALUR.csv").read_bytes(), "ALUR")
        return manifest
    if output.exists():
        raise ValueError("Use a complete existing archive or a new source folder")
    response = requests.get(URL, timeout=90)
    response.raise_for_status()
    coverage = validate_csv(response.content, "ALUR")
    manifest = {
        "schema": "anchored-returns-filing-sources/1",
        "series_id": "ALUR",
        "state": "Alabama",
        "postal": "AL",
        "region": "South",
        "producing_source": "U.S. Bureau of Labor Statistics, Local Area Unemployment Statistics",
        "distributor": "FRED",
        "definition_url": "https://fred.stlouisfed.org/series/ALUR",
        "url": URL,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "http_status": response.status_code,
        "sha256": digest(response.content),
        **coverage,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".filing-source-", dir=output.parent) as temporary:
        stage = Path(temporary) / "snapshot"
        stage.mkdir()
        (stage / "ALUR.csv").write_bytes(response.content)
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        stage.rename(output)
    return manifest


if __name__ == "__main__":
    print(json.dumps(acquire(), indent=2))
