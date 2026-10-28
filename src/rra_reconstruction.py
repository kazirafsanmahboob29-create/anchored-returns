"""Reconstruct half-year means from the complete 2019 RRA decision table.

The parser is specific to the preserved January 2020 edition. It retains rows
without an ROE, and verifies the annual summary before using any half-year.
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re

from .research_ledger import require

ROW = re.compile(
    r"(?m)^(\d\d/\d\d/19)\n([^\n]+)\n([A-Z]{2})\n([\d.]+|—)\n"
    r"([\d.]+|—)\n([\d.]+|—)\n([^\n]+)\n([^\n]+)\n"
)


def parse_2019_table(doc):
    require(len(doc) == 45, "Unexpected 2019 source bundle")
    rows = []
    for page in (40, 41):
        text = doc[page - 1].get_text("text", sort=False)
        gas_start = text.index("01/04/19\nBaltimore Gas and Electric Co.") if page == 40 else 0
        matches = list(ROW.finditer(text))
        # Every visible date row in these two table pages must be parsed.
        require(
            len(matches) == len(re.findall(r"(?m)^\d\d/\d\d/19$", text)),
            "Unparsed decision row in original table",
        )
        for m in matches:
            day, company, state, ror, roe, equity, test_year, notes = m.groups()
            rows.append(
                dict(
                    row_id=f"RRA2019-p{page}-c{m.start()}",
                    service="Electric" if page == 40 and m.start() < gas_start else "Gas",
                    decision_date=datetime.strptime(day, "%m/%d/%y").date().isoformat(),
                    company=company,
                    state=state,
                    roe_percent=None if roe == "—" else roe,
                    limited_issue_rider=bool(re.search(r"\bLIR\b", notes)),
                    evidence=dict(
                        page=page, start_char=m.start(), end_char=m.end(), exact_text=m.group()
                    ),
                )
            )
    return rows


def mean_of(rows):
    require(rows, "No comparable decision rows")
    total = sum(Decimal(r["roe_percent"]) for r in rows)
    mean = total / len(rows)
    return dict(
        observations=len(rows),
        sum_percent=str(total),
        unrounded_mean_percent=str(mean),
        display_percent=str(mean.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        included_row_ids=[r["row_id"] for r in rows],
    )


def reconstruct_2019(doc, stored_rows, service, start, end):
    cover = doc[28].get_text("text", sort=False)
    require(
        "January - December 2019" in cover and "January 31, 2020" in cover,
        "Reconstruction report identity or publication date differs",
    )
    notes = doc[40].get_text("text", sort=False)
    require(
        "Data compiled Jan. 29, 2020." in notes and "LIR\nLimited-issue rider proceeding." in notes,
        "Reconstruction data vintage or rider definition differs",
    )
    rows = parse_2019_table(doc)
    require(rows == stored_rows, "Reconstructed decision rows differ from complete original table")
    # These four summary cells are verified in original Tables 3 and 4.
    # This checks numeric extraction and rider classification independently of H2.
    controls = [
        ("Electric", False, 47, "9.65", 38, "2019\n9.65\n9.60\n47\n9.64\n9.65\n33\n9.68\n9.31\n14"),
        ("Electric", True, 33, "9.64", 38, "2019\n9.65\n9.60\n47\n9.64\n9.65\n33\n9.68\n9.31\n14"),
        ("Gas", False, 32, "9.71", 39, "2019\n9.71\n9.70\n32\n9.72\n9.72\n30\n9.60\n9.60\n2"),
        ("Gas", True, 30, "9.72", 39, "2019\n9.71\n9.70\n32\n9.72\n9.72\n30\n9.60\n9.60\n2"),
    ]
    for svc, exclude, count, mean, page, excerpt in controls:
        require(
            excerpt in doc[page - 1].get_text("text", sort=False), "Annual control evidence differs"
        )
        selected = [
            r
            for r in rows
            if r["service"] == svc
            and r["roe_percent"] is not None
            and (not exclude or not r["limited_issue_rider"])
        ]
        actual = mean_of(selected)
        require(
            actual["observations"] == count and actual["display_percent"] == mean,
            "Reconstruction does not reconcile with annual publisher controls",
        )
    require(
        service in ("Electric", "Gas") and start == "2019-07-01" and end == "2019-12-31",
        "Unsupported case-level reconstruction period",
    )
    selected = [
        r
        for r in rows
        if r["service"] == service
        and r["roe_percent"] is not None
        and not r["limited_issue_rider"]
        and start <= r["decision_date"] <= end
    ]
    return mean_of(selected)
