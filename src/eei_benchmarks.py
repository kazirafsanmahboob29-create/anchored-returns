"""Reconstruct a separate electric benchmark series from EEI's public workbook.

The series uses the complete source table, preserves missing values and excludes
limited-issue riders and transmission cases from its base-rate comparison. It is
retrospective context. It does not replace the original-report RRA series.
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path
from posixpath import normpath
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile


SOURCE_ID = "EEI-RATE-REVIEW-2025-Q3"
SOURCE_SHA256 = "b901b35640b222ae8ab6df8aca7c5b04d51c38d961b72354704ec8ecc5753895"
SOURCE_SHEET = "All Rate Cases 2025Q3"
AS_OF = "2025-09-30"
ROOT_DIRECTORY = "data/external/eei"
BASE_TYPES = frozenset(("Distribution", "Vertically Integrated"))
ALL_TYPES = BASE_TYPES | {"Limited-Issue Rider", "Transmission"}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sheet_cells(archive, name):
    """Read cached source cells without evaluating formulas or running macros."""
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
    matches = [s for s in workbook.findall("m:sheets/m:sheet", NS) if s.attrib["name"] == name]
    _require(len(matches) == 1, f"Missing or ambiguous EEI worksheet: {name}")
    target = targets[matches[0].attrib[f"{{{REL}}}id"]]
    path = target.lstrip("/") if target.startswith("/") else normpath("xl/" + target)
    _require(path.startswith("xl/"), "Invalid EEI worksheet location")
    strings = []
    if "xl/sharedStrings.xml" in archive.namelist():
        shared = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in shared]
    cells = {}
    for c in ET.fromstring(archive.read(path)).findall(".//m:sheetData/m:row/m:c", NS):
        ref, kind = c.attrib["r"], c.attrib.get("t")
        v = c.find("m:v", NS)
        if kind == "inlineStr":
            value = "".join(t.text or "" for t in c.findall(".//m:t", NS))
        elif v is None or v.text is None:
            value = None
        elif kind == "s":
            value = strings[int(v.text)]
        elif kind in ("str", "e", "b"):
            value = v.text
        else:
            try:
                value = Decimal(v.text)
            except InvalidOperation as error:
                raise ValueError(f"Invalid numeric EEI cell: {ref}") from error
        cells[ref] = value
    return cells


def _source_date(value, ref):
    _require(isinstance(value, Decimal) and value.is_finite(), f"Invalid EEI source date: {ref}")
    # Some source dates include a time of day. The calendar date is the displayed
    # reporting unit; the positive Excel serial's integer part preserves that day.
    result = date(1899, 12, 30) + timedelta(days=int(value))
    _require(date(1970, 1, 1) <= result <= date(2100, 1, 1), f"Out-of-range EEI source date: {ref}")
    return result.isoformat()


def _number(value, ref):
    if value is None or value == "NA":
        return None
    _require(
        isinstance(value, Decimal) and value.is_finite() and 0 < value < 30,
        f"Invalid or non-positive EEI ROE: {ref}",
    )
    # Every source ROE cell is displayed to two decimal places. Excel's stored
    # binary-float serialization occasionally differs in the final 15th digit.
    # Reject real extra precision rather than silently rounding it away.
    displayed = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    _require(
        abs(value - displayed) < Decimal("1e-10"),
        f"EEI ROE precision differs from two-decimal source format: {ref}",
    )
    return str(displayed)


def read_workbook(path, expected_sha256=SOURCE_SHA256):
    """Return every source observation plus published quarterly check values."""
    path = Path(path)
    _require(
        sha256(path.read_bytes()).hexdigest() == expected_sha256, "EEI workbook fingerprint changed"
    )
    with ZipFile(path) as archive:
        cells = _sheet_cells(archive, SOURCE_SHEET)
        summary = _sheet_cells(archive, "Summary")
        settings = _sheet_cells(archive, "Settings")
    _require(
        _source_date(settings.get("F6"), "Settings!F6") == AS_OF, "EEI reporting vintage changed"
    )
    expected = {
        "A3": "Status",
        "B3": "State",
        "C3": "Company",
        "E3": "Docket",
        "F3": "Service",
        "G3": "Case Type",
        "H3": "Date",
        "K3": "ROE %",
        "N3": "Date",
        "Q3": "ROE %",
    }
    _require(all(cells.get(k) == v for k, v in expected.items()), "EEI observation headers changed")
    row_numbers = sorted(
        {
            int(re.search(r"\d+$", ref).group())
            for ref in cells
            if ref.startswith("A") and ref[1:].isdigit() and int(ref[1:]) >= 4
        }
    )
    rows = []
    for row in row_numbers:
        get = lambda col: cells.get(f"{col}{row}")
        if get("A") is None:
            continue
        _require(get("A") in ("Settled", "Pending"), "Unknown EEI completion status")
        _require(
            get("F") == "Electric" and get("G") in ALL_TYPES, "EEI service or case type changed"
        )
        _require(
            all(isinstance(get(c), str) and get(c).strip() for c in ("B", "C", "E")),
            "EEI observation identity is incomplete",
        )
        authorized = (
            _source_date(get("N"), f"N{row}") if get("N") != "NA" and get("N") is not None else None
        )
        _require(
            get("A") != "Settled" or authorized is not None,
            "Completed EEI observation lacks an authorization date",
        )
        rows.append(
            dict(
                source_id=SOURCE_ID,
                source_sheet=SOURCE_SHEET,
                source_row=row,
                completion_status=get("A"),
                state=get("B"),
                utility=get("C"),
                docket=get("E"),
                service="Electric",
                case_type=get("G"),
                requested_date=_source_date(get("H"), f"H{row}")
                if get("H") != "NA" and get("H") is not None
                else None,
                requested_roe_percent=_number(get("K"), f"K{row}"),
                authorized_date=authorized,
                authorized_roe_percent=_number(get("Q"), f"Q{row}"),
            )
        )
    keys = [(r["state"], r["utility"], r["docket"], r["authorized_date"]) for r in rows]
    _require(len(keys) == len(set(keys)), "Duplicate EEI observation identity")
    controls = []
    for ref, value in summary.items():
        if (
            ref.startswith("E")
            and ref[1:].isdigit()
            and isinstance(value, str)
            and re.fullmatch(r"20\d{2}-Q[1-4]", value)
        ):
            row = ref[1:]
            if "2018-Q1" <= value <= "2025-Q3":
                controls.append(
                    dict(
                        period=value,
                        source_sheet="Summary",
                        source_row=int(row),
                        expected_n=int(summary["N" + row]),
                        expected_mean_percent=str(summary["O" + row]),
                    )
                )
    _require(len(controls) == 31, "EEI quarterly controls are incomplete")
    return rows, sorted(controls, key=lambda c: c["period"])


def summarize(rows):
    """Calculate an equal-observation mean from exact source decimal values."""
    values = [
        Decimal(r["authorized_roe_percent"])
        for r in rows
        if r["authorized_roe_percent"] is not None
    ]
    _require(all(v.is_finite() and 0 < v < 30 for v in values), "Invalid EEI ROE value")
    total, count = sum(values, Decimal(0)), len(values)
    mean = total / count if count else None
    return dict(
        n_decisions=len(rows),
        n_observed=count,
        n_missing=len(rows) - count,
        sum_percent=str(total),
        unrounded_percent=str(mean) if mean is not None else None,
        display_percent=str(mean.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        if mean is not None
        else None,
        value_fraction=str(mean / 100) if mean is not None else None,
        included_source_rows=[
            r["source_row"] for r in rows if r["authorized_roe_percent"] is not None
        ],
        missing_source_rows=[r["source_row"] for r in rows if r["authorized_roe_percent"] is None],
    )


def validate_quarters(rows, controls):
    result = []
    for control in controls:
        year, quarter = int(control["period"][:4]), int(control["period"][-1])
        selected = [
            r
            for r in rows
            if r["completion_status"] == "Settled"
            and r["authorized_date"]
            and int(r["authorized_date"][:4]) == year
            and (int(r["authorized_date"][5:7]) - 1) // 3 + 1 == quarter
        ]
        actual = summarize(selected)
        _require(
            actual["n_observed"] == control["expected_n"],
            f"EEI quarterly observation count differs: {control['period']}",
        )
        _require(
            abs(Decimal(actual["unrounded_percent"]) - Decimal(control["expected_mean_percent"]))
            < Decimal("1e-10"),
            f"EEI quarterly mean differs: {control['period']}",
        )
        result.append(
            {
                **control,
                "actual_n": actual["n_observed"],
                "actual_mean_percent": actual["unrounded_percent"],
                "status": "passed",
            }
        )
    return result


def reconstruct(rows):
    records = []
    for year in range(2018, 2026):
        for half in (1, 2):
            start = f"{year}-{1 if half == 1 else 7:02d}-01"
            end = f"{year}-06-30" if half == 1 else f"{year}-12-31"
            if end > AS_OF:
                continue
            completed = [
                r
                for r in rows
                if r["completion_status"] == "Settled"
                and r["authorized_date"] is not None
                and start <= r["authorized_date"] <= end
            ]
            if not completed:
                continue
            for scope in ("all_completed_electric", "base_rate_electric"):
                selected = (
                    completed
                    if scope == "all_completed_electric"
                    else [r for r in completed if r["case_type"] in BASE_TYPES]
                )
                records.append(
                    dict(
                        benchmark_id=f"EEI-{year}-H{half}-{scope}",
                        source_id=SOURCE_ID,
                        source_vintage="2025 Q3",
                        service="Electric",
                        period_start=start,
                        period_end=end,
                        statistic="mean_authorized_roe",
                        scope=scope,
                        riders_excluded=scope == "base_rate_electric",
                        transmission_excluded=scope == "base_rate_electric",
                        included_case_types=sorted(
                            ALL_TYPES if scope == "all_completed_electric" else BASE_TYPES
                        ),
                        n_excluded_case_types=len(completed) - len(selected),
                        source_observation_count=len(completed),
                        published_date=None,
                        retrospective=True,
                        estimation_method="case_weighted_reconstruction_from_EEI_workbook",
                        **summarize(selected),
                    )
                )
    return records


def join_eei_benchmarks(candidates, records):
    """Offer same-half-year EEI context without claiming original-date availability."""
    lookup = {
        (r["service"], r["period_start"], r["period_end"]): r
        for r in records
        if r["scope"] == "base_rate_electric"
    }
    _require(
        len(lookup) == sum(r["scope"] == "base_rate_electric" for r in records),
        "Ambiguous EEI benchmark period",
    )
    joins = []
    for candidate in candidates:
        day = date.fromisoformat(candidate["order_date"])
        year, half = (day.year, 1) if day.month >= 7 else (day.year - 1, 2)
        start = f"{year}-{1 if half == 1 else 7:02d}-01"
        end = f"{year}-06-30" if half == 1 else f"{year}-12-31"
        for service in candidate["services"]:
            record = lookup.get((service, start, end))
            joins.append(
                dict(
                    candidate_id=candidate["candidate_id"],
                    service=service,
                    order_date=candidate["order_date"],
                    required_period_start=start,
                    required_period_end=end,
                    status="matched_retrospective_context" if record else "missing_EEI_context",
                    benchmark_id=record["benchmark_id"] if record else None,
                    display_percent=record["display_percent"] if record else None,
                    value_fraction=record["value_fraction"] if record else None,
                    n_observed=record["n_observed"] if record else None,
                    published_date=None,
                    available_at_written_date=None,
                    retrospective=True,
                    reason="Publication date is unverified. EEI context remains separate from the original-report RRA series."
                    if record
                    else "No same-service, complete-half-year EEI base-rate record.",
                )
            )
    return joins


def eei_report(root, candidates=None):
    root = Path(root)
    directory = root / ROOT_DIRECTORY
    metadata = json.loads((directory / "source.json").read_text())
    _require(
        metadata["source_id"] == SOURCE_ID and metadata["sha256"] == SOURCE_SHA256,
        "EEI source identity changed",
    )
    rows, controls = read_workbook(directory / metadata["filename"])
    validated = validate_quarters(rows, controls)
    records = reconstruct(rows)
    output = dict(
        source_id=SOURCE_ID,
        source_vintage="2025 Q3",
        as_of=AS_OF,
        checked_date=metadata["retrieved_date"],
        retrospective=True,
        row_count=len(rows),
        n_completed=sum(r["completion_status"] == "Settled" for r in rows),
        n_pending=sum(r["completion_status"] == "Pending" for r in rows),
        n_completed_after_source_as_of=sum(
            r["completion_status"] == "Settled" and r["authorized_date"] > AS_OF for r in rows
        ),
        records=records,
        sources=[metadata],
        controls=validated,
        rows=rows,
        note="A separate electric-only contextual series reconstructed from a public EEI workbook. Publication timing and exact equivalence to historical RRA report vintages are unverified.",
    )
    if candidates is not None:
        output["joins"] = join_eei_benchmarks(candidates, records)
    return output
