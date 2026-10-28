"""Descriptive national electric rate-case study from preserved public inputs."""

from bisect import bisect_right
from collections import defaultdict
from datetime import date
from decimal import Decimal
from hashlib import sha256
import argparse
import csv
import json
from pathlib import Path
import statistics
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

from .eei_benchmarks import read_workbook, validate_quarters, BASE_TYPES, AS_OF
from .treasury import load_snapshot

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = "reports/national-study"
NEW_ENGLAND = ("Connecticut", "Maine", "Massachusetts", "New Hampshire", "Rhode Island", "Vermont")


def fingerprint(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def points(value):
    if value in (None, ""):
        return None
    number = Decimal(value) * 100
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError("Source value is not an exact whole basis point")
    return int(number)


def enrich(rows, treasury):
    observed = [r for r in treasury if r["printed_percent"]]
    days = [r["date"] for r in observed]
    if days != sorted(set(days)):
        raise ValueError("Treasury dates are not unique and sorted")
    output = []
    for record in rows:
        if (
            record["completion_status"] != "Settled"
            or record["authorized_date"] > AS_OF
            or record["case_type"] not in BASE_TYPES
        ):
            continue
        written = record["authorized_date"]
        index = bisect_right(days, written) - 1
        prior = observed[index] if index >= 0 else None
        gap = (
            (date.fromisoformat(written) - date.fromisoformat(prior["date"])).days
            if prior
            else None
        )
        matched = prior is not None and gap <= 7
        output.append(
            dict(
                id=f"EEI-{record['source_row']}",
                source_row=record["source_row"],
                state=record["state"],
                utility=record["utility"],
                docket=record["docket"],
                case_type=record["case_type"],
                authorized_date=written,
                requested_date=record["requested_date"],
                year=int(written[:4]),
                award_bp=points(record["authorized_roe_percent"]),
                request_bp=points(record["requested_roe_percent"]),
                treasury_bp=points(prior["printed_percent"]) if matched else None,
                treasury_date=prior["date"] if matched else None,
                treasury_gap_days=gap if matched else None,
            )
        )
    return sorted(output, key=lambda r: (r["authorized_date"], r["source_row"]))


def average(values):
    return statistics.mean(values) if values else None


def describe(rows):
    awards = [r["award_bp"] for r in rows if r["award_bp"] is not None]
    pairs = [r for r in rows if r["award_bp"] is not None and r["request_bp"] is not None]
    matched = [r for r in rows if r["award_bp"] is not None and r["treasury_bp"] is not None]
    gaps = [r["award_bp"] - r["request_bp"] for r in pairs]
    return dict(
        cases=len(rows),
        awards=len(awards),
        missing_awards=len(rows) - len(awards),
        pairs=len(pairs),
        missing_pair=len(rows) - len(pairs),
        mean_award_bp=average(awards),
        median_award_bp=statistics.median(awards) if awards else None,
        mean_gap_bp=average(gaps),
        median_gap_bp=statistics.median(gaps) if gaps else None,
        awards_below_request=sum(g < 0 for g in gaps),
        awards_equal_request=sum(g == 0 for g in gaps),
        awards_above_request=sum(g > 0 for g in gaps),
        matched_treasury=len(matched),
        mean_matched_award_bp=average([r["award_bp"] for r in matched]),
        mean_treasury_bp=average([r["treasury_bp"] for r in matched]),
        jurisdictions=len(set(r["state"] for r in rows)),
        utility_labels=len(set(r["utility"] for r in rows)),
    )


def select(rows, start, end, state="", case_type=""):
    if not (1980 <= start <= end <= 2025):
        raise ValueError("Invalid study year range")
    return [
        r
        for r in rows
        if start <= r["year"] <= end
        and (
            not state
            or r["state"] == state
            or state == "@NE"
            and r["state"] in NEW_ENGLAND
            or state == "@other"
            and r["state"] not in NEW_ENGLAND
        )
        and (not case_type or r["case_type"] == case_type)
    ]


def regional_context(rows):
    """A larger publisher-table panel, never represented as reviewed order PDFs."""
    region = select(rows, 2010, 2024, "@NE")
    state_rows = []
    for state in NEW_ENGLAND:
        earlier, later = select(rows, 2010, 2014, state), select(rows, 2020, 2024, state)
        a, b = describe(earlier), describe(later)
        state_rows.append(
            dict(
                state=state,
                earlier_cases=a["cases"],
                earlier_awards=a["awards"],
                later_cases=b["cases"],
                later_awards=b["awards"],
                earlier_mean_bp=a["mean_award_bp"],
                later_mean_bp=b["mean_award_bp"],
                change_bp=b["mean_award_bp"] - a["mean_award_bp"]
                if a["awards"] and b["awards"]
                else None,
            )
        )
    return dict(
        coverage=describe(region),
        states=state_rows,
        records=region,
        longer_common=comparison(
            select(rows, 2010, 2014, "@NE"), select(rows, 2020, 2024, "@NE"), "state"
        ),
        longer_utility=comparison(
            select(rows, 2010, 2014, "@NE"), select(rows, 2020, 2024, "@NE"), "utility"
        ),
        recent=comparison(select(rows, 2020, 2021, "@NE"), select(rows, 2023, 2024, "@NE")),
        recent_common=comparison(
            select(rows, 2020, 2021, "@NE"), select(rows, 2023, 2024, "@NE"), "state"
        ),
        definition="New England is CT, ME, MA, NH, RI and VT. Completed electric base-rate publisher observations, including formula implementations. They are not additional source-checked PDFs in the document cohort.",
    )


def comparison(earlier, later, weighting="case"):
    if weighting not in ("case", "state", "utility"):
        raise ValueError("Unknown comparison weighting")
    # All headline differences use the same award/Treasury-matched rows.
    earlier = [r for r in earlier if r["award_bp"] is not None and r["treasury_bp"] is not None]
    later = [r for r in later if r["award_bp"] is not None and r["treasury_bp"] is not None]
    if weighting == "case":
        left, right = describe(earlier), describe(later)
        return dict(
            weighting=weighting,
            earlier_n=len(earlier),
            later_n=len(later),
            common_groups=None,
            award_change_bp=right["mean_award_bp"] - left["mean_award_bp"]
            if earlier and later
            else None,
            treasury_change_bp=right["mean_treasury_bp"] - left["mean_treasury_bp"]
            if earlier and later
            else None,
        )
    groups = []
    group = lambda r: r["state"] + " / " + r["utility"] if weighting == "utility" else r["state"]
    common = sorted(set(group(r) for r in earlier) & set(group(r) for r in later))
    for name in common:
        a, b = (
            describe([r for r in earlier if group(r) == name]),
            describe([r for r in later if group(r) == name]),
        )
        groups.append(
            dict(
                group=name,
                earlier_n=a["awards"],
                later_n=b["awards"],
                award_change_bp=b["mean_award_bp"] - a["mean_award_bp"],
                treasury_change_bp=b["mean_treasury_bp"] - a["mean_treasury_bp"],
            )
        )
    return dict(
        weighting=weighting,
        earlier_n=sum(g["earlier_n"] for g in groups),
        later_n=sum(g["later_n"] for g in groups),
        common_groups=len(common),
        award_change_bp=average([g["award_change_bp"] for g in groups]),
        treasury_change_bp=average([g["treasury_change_bp"] for g in groups]),
        groups=groups,
    )


def build(root=ROOT):
    root = Path(root)
    directory = root / OUTPUT
    directory.mkdir(parents=True, exist_ok=True)
    source = json.loads((root / "data/external/eei/source.json").read_text())
    raw, controls = read_workbook(root / source["path"])
    controls = validate_quarters(raw, controls)
    meta, observations = load_snapshot(root)
    rows = enrich(raw, observations)
    earlier, later = select(rows, 2020, 2021), select(rows, 2023, 2024)
    inputs = [
        source["path"],
        "data/external/eei/source.json",
        "data/external/treasury/latest.json",
        meta["observations_path"],
        meta["raw_path"],
        "src/national_study.py",
        "src/eei_benchmarks.py",
        "analysis/national.R",
        "analysis/national.do",
    ]
    annual = [
        dict(year=y, partial=y == 2025, **describe(select(rows, y, y))) for y in range(1980, 2026)
    ]
    data = dict(
        schema="anchored-returns-national/1",
        title="National electric rate-case study",
        source=source,
        treasury_source=dict(
            url=meta["request_url"],
            retrieved_at_utc=meta["retrieved_at_utc"],
            raw_sha256=meta["raw_sha256"],
            observations_sha256=meta["observations_sha256"],
        ),
        as_of=AS_OF,
        built_date="2026-10-21",
        input_sha256={p: fingerprint(root / p) for p in inputs},
        coverage=dict(
            raw_rows=len(raw),
            pending=sum(r["completion_status"] == "Pending" for r in raw),
            after_as_of=sum(
                r["completion_status"] == "Settled" and r["authorized_date"] > AS_OF for r in raw
            ),
            excluded_case_types=sum(
                r["completion_status"] == "Settled"
                and r["authorized_date"] <= AS_OF
                and r["case_type"] not in BASE_TYPES
                for r in raw
            ),
            **describe(rows),
        ),
        periods=dict(
            earlier=dict(start=2020, end=2021, **describe(earlier)),
            later=dict(start=2023, end=2024, **describe(later)),
        ),
        comparisons=[comparison(earlier, later, w) for w in ("case", "state", "utility")],
        alternate_window=comparison(select(rows, 2019, 2021), later),
        longer_periods=[describe(select(rows, 2010, 2014)), describe(select(rows, 2020, 2024))],
        longer_comparison=comparison(select(rows, 2010, 2014), select(rows, 2020, 2024), "state"),
        annual=annual,
        records=rows,
        quarterly_controls=controls,
        regional=regional_context(rows),
        limitations=[
            "Retrospective publisher table, not a census of every authorization.",
            "Settled means a completed entry; it does not identify a negotiated settlement.",
            "An absent ROE can reflect a decision that did not reset it. Missing values are not assigned awards.",
            "Treasury is a nominal risk-free yield at authorization, not a comparable equity return or historical real-time vintage.",
            "Period differences are descriptive. Timing, utility risk, case mix and regulatory mechanisms remain uncontrolled.",
            "Common utility groups use state plus exact workbook label, not independently resolved legal entities.",
            "The 2025 observations cover only the source vintage through September 30.",
        ],
    )
    for name, table in [("cases", rows), ("annual", annual)]:
        with (directory / (name + ".csv")).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
        import pandas as pd

        frame = pd.DataFrame(table)
        for col in frame.select_dtypes(include=["str", "object"]).columns:
            frame[col] = frame[col].fillna("").astype(str)
        frame.to_stata(directory / (name + ".dta"), write_index=False, version=118)
        restored = pd.read_stata(directory / (name + ".dta"), convert_categoricals=False)
        if len(restored) != len(frame):
            raise ValueError("Stata row count changed")
        for col in frame.select_dtypes(include="number").columns:
            if (
                not frame[col]
                .fillna(-999999)
                .equals(restored[col].fillna(-999999).astype(frame[col].dtype))
            ):
                raise ValueError("Stata numeric round trip changed: " + col)
    for name, table in [
        ("regional_panel", data["regional"]["records"]),
        ("regional_states", data["regional"]["states"]),
    ]:
        with (directory / (name + ".csv")).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    executable = shutil.which("Rscript")
    data["figure_runtime"] = dict(status="not_run", reason="Rscript is unavailable")
    if executable:
        subprocess.run(
            [executable, str(root / "analysis/national.R"), str(directory)],
            check=True,
            capture_output=True,
            text=True,
        )
        data["figure_runtime"] = dict(
            status="passed",
            engine="R",
            script_sha256=fingerprint(root / "analysis/national.R"),
            annual_csv_sha256=fingerprint(directory / "annual.csv"),
            image_sha256=fingerprint(directory / "annual.png"),
            regional_image_sha256=fingerprint(directory / "regional.png"),
        )
    (directory / "study.json").write_text(json.dumps(data, indent=2) + "\n")
    with ZipFile(directory / "national-study.zip", "w", ZIP_DEFLATED) as archive:
        for name in (
            "study.json",
            "cases.csv",
            "annual.csv",
            "cases.dta",
            "annual.dta",
            "regional_panel.csv",
            "regional_states.csv",
        ):
            archive.write(directory / name, name)
        if data["figure_runtime"]["status"] == "passed":
            archive.write(directory / "annual.png", "annual.png")
            archive.write(directory / "regional.png", "regional.png")
        for name in (
            "src/national_study.py",
            "src/eei_benchmarks.py",
            "analysis/national.R",
            "analysis/national.do",
            "docs/national_study.md",
        ):
            if (root / name).is_file():
                archive.write(root / name, name)
        for path in sorted((root / "src").glob("*")):
            if (
                path.is_file()
                and path.suffix in (".py", ".json")
                and str(path.relative_to(root)) not in archive.namelist()
            ):
                archive.write(path, str(path.relative_to(root)))
        pointer = json.loads((root / "data/external/treasury/latest.json").read_text())
        for name in [
            source["path"],
            "data/external/eei/source.json",
            "data/external/treasury/latest.json",
            pointer["metadata_path"],
            meta["observations_path"],
            meta["raw_path"],
            "pyproject.toml",
        ]:
            archive.write(root / name, name)
        archive.writestr(
            "README.md",
            "# Reproducing the national study\n\nThis bundle includes the preserved EEI workbook and Treasury retrieval used in the study. The source files retain their publishers' rights.\n\nInstall Python 3.11 or later and the declared dependencies with `python -m pip install -e .`, then run `python -m src.national_study`. Outputs are written to reports/national-study. Rscript is used when installed. The supplied cases.csv, annual.csv and Stata tables can also be used directly. No original-order PDFs are needed for the national calculation. The broader New England document tools require their separate source archive.\n",
        )
    return data


def render_article(root, template):
    root = Path(root)
    path = root / OUTPUT / "study.json"
    data = json.loads(path.read_text())
    for name, expected in data["input_sha256"].items():
        if fingerprint(root / name) != expected:
            raise ValueError("National study inputs changed; run research national")
    a, b = data["periods"]["earlier"], data["periods"]["later"]
    c, s, u = data["comparisons"]
    old, new = data["longer_periods"]
    long = data["longer_comparison"]
    values = {
        "AWARD_CHANGE": f"{c['award_change_bp']:.0f}",
        "TREASURY_CHANGE": f"{c['treasury_change_bp']:.0f}",
        "EARLY_AWARD": f"{a['mean_award_bp'] / 100:.2f}",
        "LATE_AWARD": f"{b['mean_award_bp'] / 100:.2f}",
        "EARLY_TREASURY": f"{a['mean_treasury_bp'] / 100:.2f}",
        "LATE_TREASURY": f"{b['mean_treasury_bp'] / 100:.2f}",
        "EARLY_N": str(a["awards"]),
        "LATE_N": str(b["awards"]),
        "STATE_N": str(s["common_groups"]),
        "STATE_AWARD": f"{s['award_change_bp']:.0f}",
        "STATE_TREASURY": f"{s['treasury_change_bp']:.0f}",
        "UTILITY_N": str(u["common_groups"]),
        "UTILITY_AWARD": f"{u['award_change_bp']:.0f}",
        "UTILITY_TREASURY": f"{u['treasury_change_bp']:.0f}",
        "LONG_EARLY": f"{old['mean_award_bp'] / 100:.2f}",
        "LONG_LATE": f"{new['mean_award_bp'] / 100:.2f}",
        "LONG_CHANGE": f"{old['mean_award_bp'] - new['mean_award_bp']:.0f}",
        "LONG_N": str(long["common_groups"]),
        "LONG_LOWER": str(sum(g["award_change_bp"] < 0 for g in long["groups"])),
        "OLD_MISSING": f"{old['missing_awards'] / old['cases'] * 100:.2f}",
        "NEW_MISSING": f"{new['missing_awards'] / new['cases'] * 100:.2f}",
    }
    regional = data["regional"]
    values.update(
        NE_CASES=str(regional["coverage"]["cases"]),
        NE_AWARDS=str(regional["coverage"]["awards"]),
        NE_RECENT=f"{regional['recent']['award_change_bp']:.0f}",
        NE_TREASURY=f"{regional['recent']['treasury_change_bp']:.0f}",
        NE_COMMON_N=str(regional["longer_utility"]["common_groups"]),
        NE_COMMON_LOWER=str(
            sum(g["award_change_bp"] < 0 for g in regional["longer_utility"]["groups"])
        ),
        NE_COMMON_CHANGE=f"{abs(regional['longer_utility']['award_change_bp']):.1f}",
        NE_STATE_TABLE="".join(
            "<tr><td>"
            + r["state"]
            + "</td><td>"
            + str(r["earlier_awards"])
            + " / "
            + str(r["earlier_cases"])
            + "</td><td>"
            + str(r["later_awards"])
            + " / "
            + str(r["later_cases"])
            + "</td><td>"
            + ("Unavailable" if r["change_bp"] is None else f"{r['change_bp']:+.2f} bp")
            + "</td></tr>"
            for r in regional["states"]
        ),
    )
    for name, value in values.items():
        template = template.replace("__" + name + "__", value)
    if data["figure_runtime"]["status"] == "passed":
        if fingerprint(root / OUTPUT / "annual.png") != data["figure_runtime"]["image_sha256"]:
            raise ValueError("National R figure changed")
        if (
            fingerprint(root / OUTPUT / "regional.png")
            != data["figure_runtime"]["regional_image_sha256"]
        ):
            raise ValueError("Regional R figure changed")
    return template


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = build()
    print(
        json.dumps(
            {k: result[k] for k in ("as_of", "coverage", "periods", "comparisons")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
