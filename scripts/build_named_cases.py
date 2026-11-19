"""Render the five public-order schedules discussed in Section 5."""

import argparse
import csv
from decimal import Decimal
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOCKETS = ("2018-00194", "22-08-08", "17-05", "23-150")


def normalized(value):
    return re.sub(r"[^0-9a-z]", "", value.lower())


def percent(value):
    return f"{Decimal(value):.2%}" if value else "—"


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-rebuild", type=Path, required=True)
    args = parser.parse_args()
    reports = ROOT / "reports/comparability"
    registers = ROOT / "data/research/comparability-v1/phase2"
    proceedings = json.loads((registers / "proceedings.json").read_text())["proceedings"]
    state_mapping = json.loads(
        (ROOT / "data/external/expanded_2026-10-28/state_mapping.json").read_text()
    )
    postal = {r["state"]: r["postal"] for r in state_mapping}

    def state_code(value):
        return postal.get(value, value)

    schedules = rows(reports / "pilot_financials.csv")
    filing = args.local_rebuild / "reports/filing-study"
    panel = rows(filing / "panel.csv")
    saved = {r["id"]: r["with_request"] for r in rows(filing / "predictions.csv")}
    selected = []
    for docket in DOCKETS:
        matching = [p for p in proceedings if normalized(docket) in map(normalized, p["dockets"])]
        if len(matching) != 1:
            raise ValueError(f"Expected one public proceeding for {docket}")
        order = matching[0]
        for row in schedules:
            if row["proceeding_id"] != order["proceeding_id"]:
                continue
            # The joint Massachusetts order has two utilities with the same award.
            utility = ""
            if docket == "17-05":
                label = normalized(row["label"])
                if "nstar" in label:
                    utility = "nstar"
                elif "wmeco" in label:
                    utility = "westernmass"
                else:
                    raise ValueError("Unrecognized utility in joint D.P.U. 17-05 schedule")
            candidates = [
                p["id"] for p in panel
                if state_code(p["state"]) == state_code(row["state"])
                and p["authorized_date"] == row["decision_date"]
                and normalized(docket) in normalized(p["docket"])
                and utility in normalized(p["utility"])
                and p["award_bp"] and row["applied_roe"]
                and Decimal(p["award_bp"]) == Decimal(row["applied_roe"]) * 10000
            ]
            prediction = saved.get(candidates[0]) if len(candidates) == 1 else None
            selected.append((docket, row, prediction))
    if len(selected) != 5:
        raise ValueError("Expected five public financial schedules")
    matched = sum(prediction is not None for _, _, prediction in selected)
    show_predictions = matched > len(selected) / 2
    headers = ["Schedule", "Docket", "Order-reported request", "Base ROE", "Applied ROE",
               "Approved equity share", "Approved rate base"]
    if show_predictions:
        headers += ["Prediction", "Prediction minus applied award (bp)"]
    lines = ["# Financial schedules discussed in Section 5", "",
             "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for docket, row, prediction in selected:
        rate_base = row["approved_rate_base_usd"]
        values = [row["label"], docket, percent(row["order_reported_request"]),
                  percent(row["base_roe"]), percent(row["applied_roe"]),
                  percent(row["approved_equity_share"]),
                  f"${Decimal(rate_base):,.0f}" if rate_base else "—"]
        if show_predictions:
            if prediction is None:
                values += ["—", "—"]
            else:
                error = (Decimal(prediction) - Decimal(row["applied_roe"]) * 100) * 100
                values += [f"{Decimal(prediction):.2f}%", f"{error:+.2f}"]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    if not show_predictions:
        lines.extend([
            f"The local filing rebuild yielded an unambiguous saved prediction for {matched} of the five schedules, so the table omits the prediction column.",
            "",
            "Central Maine Power is the worked example in [Section 5](../../paper/manuscript.md#5-reading-the-decisions-behind-the-numbers). "
            "Using the paper’s rounded values, the prediction minus the applied award is 9.36% − 8.25% = +111 basis points.",
            "",
        ])
    (reports / "section-5-schedules.md").write_text("\n".join(lines))
    print(f"{matched} of {len(selected)} schedules matched saved predictions.")


if __name__ == "__main__":
    main()
