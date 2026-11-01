"""Financial comparisons using facts extracted from original rate-case decisions."""

import json
from pathlib import Path

import numpy as np


def equity_return_allowance(rate_base, equity_share, roe):
    """Annual equity component in dollars, before any revenue tax gross-up."""
    inputs = np.asarray([rate_base, equity_share, roe], dtype=float)
    if not np.isfinite(inputs).all():
        raise ValueError("All financial inputs must be finite.")
    if rate_base < 0 or not 0 <= equity_share <= 1 or not 0 <= roe <= 1:
        raise ValueError("Use a nonnegative dollar base and decimal shares and rates.")
    return float(np.prod(inputs))


def roe_sensitivity(rate_base, equity_share, change_bp):
    """Signed change in the annual equity component for an ROE change in bp."""
    if not np.isfinite(change_bp):
        raise ValueError("The basis-point change must be finite.")
    # Validate the base and share without restricting the direction of the change.
    return equity_return_allowance(rate_base, equity_share, 1.0) * change_bp / 10000


def load_schedules(directory):
    """Resolve fact references while preserving source locations and missing values."""
    directory = Path(directory)
    facts = json.loads((directory / "facts.json").read_text())["facts"]
    sources = json.loads((directory / "sources.json").read_text())["sources"]
    schedules = json.loads((directory / "schedules.json").read_text())["schedules"]
    proceedings = json.loads((directory / "proceedings.json").read_text())["proceedings"]
    fact_map = {f["fact_id"]: f for f in facts}
    source_map = {s["source_id"]: s for s in sources}
    case_map = {p["proceeding_id"]: p for p in proceedings}
    if len(fact_map) != len(facts) or len(source_map) != len(sources):
        raise ValueError("Fact and source identifiers must be unique.")
    for fact in facts:
        if fact["source_id"] not in source_map or not fact["location"]:
            raise ValueError(f"Missing source or location for {fact['fact_id']}")
        if fact["value"] is None and not fact.get("missing_reason"):
            raise ValueError(f"Missing-value explanation needed for {fact['fact_id']}")
    output = []
    for schedule in schedules:
        row = dict(schedule)
        case = case_map[row["proceeding_id"]]
        row.update(state=case["state"], decision_date=case["decision_date"])
        row["evidence"] = {}
        for field, fact_id in schedule["facts"].items():
            fact = fact_map[fact_id]
            if fact["proceeding_id"] != row["proceeding_id"]:
                raise ValueError(f"Fact belongs to a different case: {fact_id}")
            row[field] = fact["value"]
            row["evidence"][field] = {
                "fact_id": fact_id,
                "source_url": source_map[fact["source_id"]]["source_url"],
                "location": fact["location"],
                "missing_reason": fact.get("missing_reason"),
            }
        roe, share = row["applied_roe"], row["approved_equity_share"]
        row["equity_allowance_per_100"] = (
            equity_return_allowance(100, share, roe)
            if roe is not None and share is not None
            else None
        )
        rb = row["approved_rate_base_usd"]
        row["annual_equity_allowance_usd"] = (
            equity_return_allowance(rb, share, roe)
            if rb is not None and share is not None and roe is not None
            else None
        )
        output.append(row)
    return output
