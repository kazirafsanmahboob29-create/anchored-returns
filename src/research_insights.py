"""Descriptive comparisons from source-checked records, with explicit coverage."""

from decimal import Decimal
from statistics import median

from .research_ledger import require

AWARD_FIELDS = {
    "awarded_roe",
    "awarded_roe_as_issued",
    "commission_awarded_roe",
    "awarded_roe_after_performance_reductions",
    "formula_implemented_roe",
}
STANCES = ("Relied on", "Considered", "Rejected")
DISPLAY_CODES = ("MKT", "PEER", "OWN")


def number(value):
    return (
        format(value, "f").rstrip("0").rstrip(".")
        if "." in format(value, "f")
        else format(value, "f")
    )


def original_fact(facts, case, fields, unit="percent"):
    rows = [
        f
        for f in facts
        if f["case_id"] == case["case_id"]
        and f["field"] in fields
        and f["event_date"] == case["order_date"]
        and f["relation"] == "equal"
        and f["unit"] == unit
    ]
    if not rows:
        return None
    require(
        len({Decimal(f["value"]) for f in rows}) == 1,
        "Conflicting original numeric values: " + case["case_id"],
    )
    row = rows[0]
    return {
        key: row[key]
        for key in (
            "field",
            "value",
            "unit",
            "page",
            "event_date",
            "source_url",
            "pdf_path",
            "pdf_sha256",
        )
    }


def sensitivity(outcomes, coding_rows):
    """Descriptive checks only; deleting an order is not a confidence interval."""
    paired = [r for r in outcomes if r["award_minus_request_bp"] is not None]
    values = [Decimal(r["award_minus_request_bp"]) for r in paired]
    omissions = [
        dict(
            omitted_case_id=r["case_id"],
            remaining_pairs=len(values) - 1,
            median_bp=number(median(values[:i] + values[i + 1 :])),
        )
        for i, r in enumerate(paired)
        if len(values) > 1
    ]
    weighting = []
    units = sum(r["commission_units"] for r in coding_rows)
    for code in DISPLAY_CODES:
        order_shares = [
            Decimal(r["codes"][code]["stances"]["Relied on"]) / Decimal(r["commission_units"])
            for r in coding_rows
        ]
        pooled = sum(r["codes"][code]["stances"]["Relied on"] for r in coding_rows)
        weighting.append(
            dict(
                code=code,
                reliance_units=pooled,
                commission_units=units,
                orders=len(coding_rows),
                pooled_percent=number(Decimal(pooled) * 100 / units) if units else None,
                equal_order_percent=number(sum(order_shares) * 100 / len(order_shares))
                if order_shares
                else None,
            )
        )
    return dict(
        request_gap=dict(
            pairs=len(values),
            median_bp=number(median(values)) if values else None,
            below_request=sum(v < 0 for v in values),
            equal_request=sum(v == 0 for v in values),
            above_request=sum(v > 0 for v in values),
            leave_one_out=omissions,
            leave_one_out_low_bp=min(
                (r["median_bp"] for r in omissions), key=Decimal, default=None
            ),
            leave_one_out_high_bp=max(
                (r["median_bp"] for r in omissions), key=Decimal, default=None
            ),
        ),
        reliance_weighting=weighting,
        limits="Leave-one-order-out results describe these entered pairs, not sampling uncertainty. Equal-order weighting gives each completed order the same weight; pooled weighting gives each text unit the same weight. Neither resolves selection bias or coding reliability.",
    )


def benchmark_comparisons(outcomes, benchmark_joins, benchmark_records):
    """Compare exact benchmarks using written dates, preserving settlement timing limits."""
    by_case = {r["case_id"]: r for r in outcomes}
    lookup = {r["benchmark_id"]: r for r in benchmark_records}
    rows = []
    for joined in benchmark_joins:
        outcome = by_case.get(joined["candidate_id"])
        if not outcome or not outcome["award"] or joined["status"] != "matched":
            continue
        record = lookup[joined["benchmark_id"]]
        require(
            record["riders_excluded"] is True and record["service"] == joined["service"],
            "Benchmark comparison scope differs",
        )
        available = joined["available_at_written_date"] is True
        rows.append(
            dict(
                case_id=outcome["case_id"],
                utility=outcome["utility"],
                service=joined["service"],
                award=outcome["award"],
                benchmark=record,
                award_kind=outcome["award_kind"],
                comparison_basis="original_written_date",
                timing_note=(
                    "Approved settlement. Publication by the written report date does not establish "
                    "availability when the return was agreed."
                    if outcome["award_kind"] == "approved_settlement"
                    else ""
                ),
                published_at_decision=available,
                award_minus_benchmark_bp=number(
                    (
                        Decimal(outcome["award"]["value"])
                        - Decimal(record.get("display_percent") or record["printed_percent"])
                    )
                    * 100
                )
                if available
                else None,
            )
        )
    return rows


def build_insights(cases, facts, passages, *, benchmark_joins=(), benchmark_records=()):
    """Keep missing facts distinct from zero and first-pass labels from validated findings."""
    outcomes = []
    adjustments = []
    for case in cases:
        request = original_fact(facts, case, {"company_requested_roe"})
        award = original_fact(facts, case, AWARD_FIELDS)
        settlement = original_fact(facts, case, {"approved_settlement_roe"})
        require(not (award and settlement), "Independent award and settlement roles conflict")
        award_kind = (
            "approved_settlement"
            if settlement
            else "formula_implementation"
            if award and award["field"] == "formula_implemented_roe"
            else "commission_determined"
        )
        award = award or settlement
        base = original_fact(facts, case, {"base_authorized_roe"})
        adjustment = original_fact(facts, case, {"performance_adjustment"}, unit="basis_points")
        delta = (
            None
            if request is None or award is None
            else number((Decimal(award["value"]) - Decimal(request["value"])) * 100)
        )
        outcomes.append(
            dict(
                case_id=case["case_id"],
                utility=case["utility"],
                state=case["state"],
                docket=case["docket"],
                order_date=case["order_date"],
                request=request,
                award=award,
                award_kind=award_kind if award else None,
                award_minus_request_bp=delta,
            )
        )
        if base and award and adjustment:
            require(
                Decimal(base["value"]) + Decimal(adjustment["value"]) / 100
                == Decimal(award["value"]),
                "Base return and adjustment do not reconcile: " + case["case_id"],
            )
            adjustments.append(
                dict(
                    case_id=case["case_id"],
                    utility=case["utility"],
                    base=base,
                    adjustment=adjustment,
                    award=award,
                )
            )
    complete = [c for c in cases if c["coding_status"] == "first_pass_complete"]
    rows = []
    for case in complete:
        units = [
            p
            for p in passages
            if p["case_id"] == case["case_id"] and p["section"] == "Commission analysis"
        ]
        require(units, "A completed case needs recorded Commission-analysis units")
        counts = {}
        for code in DISPLAY_CODES:
            ids = {stance: [] for stance in STANCES}
            for p in units:
                flag = p["codes"][code]
                require(type(flag) is int and flag in (0, 1), "Invalid binary insight input")
                if flag:
                    stance = p["stances"].get(code)
                    require(stance in STANCES, "Commission code needs an evaluative stance")
                    ids[stance].append(p["passage_id"])
            counts[code] = dict(
                stances={s: len(ids[s]) for s in STANCES},
                present=sum(len(v) for v in ids.values()),
                unit_ids=ids,
            )
        rows.append(
            dict(
                case_id=case["case_id"],
                utility=case["utility"],
                state=case["state"],
                docket=case["docket"],
                commission_units=len(units),
                codes=counts,
            )
        )
    totals = {
        code: dict(
            stances={s: sum(r["codes"][code]["stances"][s] for r in rows) for s in STANCES},
            present=sum(r["codes"][code]["present"] for r in rows),
            orders_with_reliance=sum(r["codes"][code]["stances"]["Relied on"] > 0 for r in rows),
        )
        for code in DISPLAY_CODES
    }
    return dict(
        status="descriptive_entered_records",
        data_kind="real_source_records",
        entered_orders=len(cases),
        request_award_pairs=sum(r["award_minus_request_bp"] is not None for r in outcomes),
        coded_orders=len(complete),
        commission_units=sum(r["commission_units"] for r in rows),
        outcomes=outcomes,
        adjustments=adjustments,
        coding_rows=rows,
        code_totals=totals,
        sensitivity=sensitivity(outcomes, rows),
        benchmark_comparisons=benchmark_comparisons(outcomes, benchmark_joins, benchmark_records),
        scope="Entered candidate records only. Coding counts use complete first passes and Commission-analysis paragraphs and footnotes, including zero-code units.",
        limits=[
            "These records are not the finalized 15-order sample.",
            "The coded stances are first-pass interpretations; independent reliability is unmeasured.",
            "Counts refer to text units, not independent decisions. Codes can co-occur.",
            "Request differences are descriptive and do not identify a causal mechanism.",
        ],
    )
