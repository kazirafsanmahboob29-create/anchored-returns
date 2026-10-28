"""Source-linked regional summaries of the versioned original-order cohort."""

import csv
from decimal import Decimal
import json
from pathlib import Path
from statistics import mean, median

from .research_insights import AWARD_FIELDS, original_fact

STATES = ("CT", "MA", "ME", "NH", "RI", "VT")


def records(payload):
    rows = []
    sources = {r["source_id"]: r for r in payload["sources"]}
    for c in payload["cohort"]["members"]:
        case = dict(case_id=c["candidate_id"], order_date=c["order_date"])
        award = original_fact(payload["facts"], case, AWARD_FIELDS | {"approved_settlement_roe"})
        request = original_fact(payload["facts"], case, {"company_requested_roe"})
        rows.append(
            dict(
                case_id=c["candidate_id"],
                state=c["state"],
                utility=c["utility"],
                docket=c["docket"],
                order_date=c["order_date"],
                services=c["services"],
                stratum=c["stratum"],
                proceeding_group=c["proceeding_group"],
                award_bp=float(Decimal(award["value"]) * 100) if award else None,
                request_bp=float(Decimal(request["value"]) * 100) if request else None,
                source_id=c["source_ids"][0],
                award_page=award["page"] if award else None,
                pdf_path=award["pdf_path"] if award else sources[c["source_ids"][0]]["pdf_path"],
                source_url=award["source_url"] if award else None,
                pdf_sha256=award["pdf_sha256"] if award else None,
            )
        )
    return rows


def summarize(rows, service="", include_settlements=False, include_formulas=False):
    selected = [
        r
        for r in rows
        if (not service or service in r["services"])
        and (
            r["stratum"] == "primary"
            or include_settlements
            and r["stratum"] == "settlement"
            or include_formulas
            and r["stratum"] == "formula"
        )
    ]
    result = []
    for state in STATES:
        group = [r for r in selected if r["state"] == state]
        awards = [r["award_bp"] for r in group if r["award_bp"] is not None]
        result.append(
            dict(
                state=state,
                orders=len(group),
                awards=len(awards),
                missing=len(group) - len(awards),
                proceedings=len({r["proceeding_group"] for r in group}),
                median_bp=median(awards) if awards else None,
                mean_bp=mean(awards) if awards else None,
                min_bp=min(awards) if awards else None,
                max_bp=max(awards) if awards else None,
                early=sum(r["order_date"] < "2022-01-01" for r in group),
                later=sum(r["order_date"] >= "2023-01-01" for r in group),
            )
        )
    return result


def render_regional(root, template, payload):
    root = Path(root)
    rows = records(payload)
    data = dict(
        schema="anchored-returns-regional/1",
        version=payload["cohort"]["version"],
        cutoff=payload["cohort"]["cutoff"],
        manifest_sha256=payload["cohort"]["manifest_sha256"],
        records=rows,
        primary=summarize(rows),
        all=summarize(rows, include_settlements=True, include_formulas=True),
        note="Bounded original-document cohort. State summaries are descriptive, not estimates of jurisdiction effects. Joint-service orders remain one document; settlements and formula implementations are optional and separately identified.",
    )
    directory = root / "reports/national-study"
    (directory / "regional.json").write_text(json.dumps(data, indent=2) + "\n")
    with (directory / "regional.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(dict(r, services=";".join(r["services"])) for r in rows)
    values = dict(
        REGIONAL_TOTAL=str(len(rows)),
        REGIONAL_PRIMARY=str(payload["cohort"]["primary"]),
        REGIONAL_SETTLEMENTS=str(payload["cohort"]["supplemental"]),
        REGIONAL_FORMULAS=str(payload["cohort"]["formula"]),
        REGIONAL_AWARDS=str(sum(r["award_bp"] is not None for r in rows)),
        REGIONAL_DATA=json.dumps(data, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("&", "\\u0026"),
    )
    for name, value in values.items():
        template = template.replace("__" + name + "__", value)
    return template
