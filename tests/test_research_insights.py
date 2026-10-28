"""Measurement contracts for the real-record descriptive view. Fixtures are synthetic."""

import pytest

from src.research_insights import build_insights
from src.research_ledger import LedgerError


def case(identity="TEST", status="first_pass_complete"):
    return dict(
        case_id=identity,
        utility="Synthetic test utility",
        state="ME",
        docket="TEST",
        order_date="2025-01-03",
        coding_status=status,
    )


def fact(field, value, *, identity="TEST", date="2025-01-03", unit="percent", relation="equal"):
    return dict(
        case_id=identity,
        field=field,
        value=value,
        event_date=date,
        unit=unit,
        relation=relation,
        source_url="https://example.org/synthetic",
        pdf_path="synthetic.pdf",
        pdf_sha256="fixture",
        page=1,
    )


def unit(identity, *, case_id="TEST", section="Commission analysis", code=None, stance="Relied on"):
    return dict(
        passage_id=identity,
        case_id=case_id,
        section=section,
        unit_type="footnote",
        codes={c: int(c == code) for c in ("MKT", "PEER", "OWN")},
        stances={code: stance} if code else {},
    )


def test_exact_basis_point_conversion_and_original_role_selection():
    facts = [
        fact("company_requested_roe", "9.94"),
        fact("awarded_roe", "9.05"),
        fact("utility_witness_recommended_roe", "10.50"),
        fact("compliance_confirmed_roe", "9.04", date="2025-02-01"),
    ]
    row = build_insights([case()], facts, [unit("U1")])["outcomes"][0]
    assert row["award_minus_request_bp"] == "-89"
    assert row["request"]["value"] == "9.94"
    assert row["award"]["value"] == "9.05"


def test_missing_request_is_not_zero_and_base_is_not_award():
    report = build_insights([case()], [fact("base_authorized_roe", "9.25")], [unit("U1")])
    row = report["outcomes"][0]
    assert row["request"] is None and row["award"] is None
    assert row["award_minus_request_bp"] is None and report["request_award_pairs"] == 0


def test_equal_values_retain_a_real_zero_difference():
    row = build_insights(
        [case()], [fact("company_requested_roe", "9.35"), fact("awarded_roe", "9.35")], [unit("U1")]
    )["outcomes"][0]
    assert row["award_minus_request_bp"] == "0"


def test_bound_and_wrong_units_do_not_become_exact_request():
    report = build_insights(
        [case()],
        [
            fact("company_requested_roe", "9.00", relation="at_least"),
            fact("company_requested_roe", "900", unit="basis_points"),
            fact("awarded_roe", "9.00"),
        ],
        [unit("U1")],
    )
    assert report["outcomes"][0]["request"] is None


def test_conflicting_original_awards_are_rejected():
    with pytest.raises(LedgerError, match="Conflicting original"):
        build_insights(
            [case()],
            [fact("awarded_roe", "9.04"), fact("awarded_roe_as_issued", "9.05")],
            [unit("U1")],
        )


def test_commission_denominator_includes_zero_units_and_excludes_party_positions():
    report = build_insights(
        [case()],
        [],
        [
            unit("zero"),
            unit("reliance", code="OWN"),
            unit("rejection", code="OWN", stance="Rejected"),
            unit("party", code="MKT", section="Positions of parties", stance="Summarized only"),
        ],
    )
    assert report["commission_units"] == 3
    assert report["code_totals"]["OWN"]["present"] == 2
    assert report["code_totals"]["OWN"]["stances"] == {
        "Relied on": 1,
        "Considered": 0,
        "Rejected": 1,
    }
    assert report["code_totals"]["MKT"]["present"] == 0
    assert report["coding_rows"][0]["codes"]["OWN"]["unit_ids"]["Rejected"] == ["rejection"]


def test_incomplete_cases_do_not_enter_coding_denominator():
    report = build_insights(
        [case(), case("PARTIAL", "not_started")],
        [],
        [unit("complete"), unit("partial", case_id="PARTIAL", code="MKT")],
    )
    assert report["entered_orders"] == 2
    assert report["coded_orders"] == 1 and report["commission_units"] == 1
    assert report["code_totals"]["MKT"]["present"] == 0


def test_invalid_commission_stance_is_not_counted_as_reliance():
    with pytest.raises(LedgerError, match="evaluative stance"):
        build_insights([case()], [], [unit("bad", code="MKT", stance="Summarized only")])


def test_management_adjustment_reconciles_base_and_operative_award():
    facts = [
        fact("base_authorized_roe", "9.25"),
        fact("performance_adjustment", "-100", unit="basis_points"),
        fact("awarded_roe", "8.25"),
    ]
    assert len(build_insights([case(status="not_started")], facts, [])["adjustments"]) == 1
    facts[-1]["value"] = "9.25"
    with pytest.raises(LedgerError, match="do not reconcile"):
        build_insights([case(status="not_started")], facts, [])


def test_missing_award_does_not_create_a_comparison():
    row = build_insights([case()], [fact("company_requested_roe", "10.00")], [unit("U1")])[
        "outcomes"
    ][0]
    assert row["award"] is None and row["award_minus_request_bp"] is None


def test_original_operative_performance_award_and_settlement_keep_their_roles():
    rows = build_insights(
        [case(status="not_started")],
        [
            fact("company_requested_roe", "10.2"),
            fact("awarded_roe_before_performance_reductions", "9.1"),
            fact("awarded_roe_after_performance_reductions", "8.63"),
        ],
        [],
    )["outcomes"]
    assert rows[0]["award"]["value"] == "8.63" and rows[0]["award_minus_request_bp"] == "-157"
    row = build_insights(
        [case(status="not_started")], [fact("approved_settlement_roe", "9.275")], []
    )["outcomes"][0]
    assert row["award_kind"] == "approved_settlement" and row["award_minus_request_bp"] is None
    with pytest.raises(ValueError, match="roles conflict"):
        build_insights(
            [case(status="not_started")],
            [fact("approved_settlement_roe", "9.275"), fact("awarded_roe", "9.275")],
            [],
        )


def test_leave_one_out_medians_preserve_zero_and_exclude_missing_pairs():
    cases = [
        case("A", "not_started"),
        case("B", "not_started"),
        case("C", "not_started"),
        case("MISSING", "not_started"),
    ]
    facts = []
    for identity, award in [("A", "9"), ("B", "10"), ("C", "11")]:
        facts += [
            fact("company_requested_roe", "10", identity=identity),
            fact("awarded_roe", award, identity=identity),
        ]
    facts.append(fact("awarded_roe", "8", identity="MISSING"))
    g = build_insights(cases, facts, [])["sensitivity"]["request_gap"]
    assert g["pairs"] == 3 and g["median_bp"] == "0"
    assert (g["below_request"], g["equal_request"], g["above_request"]) == (1, 1, 1)
    assert g["leave_one_out_low_bp"] == "-50" and g["leave_one_out_high_bp"] == "50"
    assert {r["omitted_case_id"] for r in g["leave_one_out"]} == {"A", "B", "C"}


def test_empty_and_single_pair_do_not_invent_an_omission_range():
    for facts in ([], [fact("company_requested_roe", "10"), fact("awarded_roe", "9")]):
        g = build_insights([case(status="not_started")], facts, [])["sensitivity"]["request_gap"]
        assert g["leave_one_out"] == [] and g["leave_one_out_low_bp"] is None


def test_unit_and_order_weighting_use_distinct_denominators():
    report = build_insights(
        [case("A"), case("B")],
        [],
        [unit("A1", case_id="A", code="MKT")] + [unit("B" + str(i), case_id="B") for i in range(3)],
    )
    m = report["sensitivity"]["reliance_weighting"][0]
    assert m["pooled_percent"] == "25" and m["equal_order_percent"] == "50"
    assert m["commission_units"] == 4 and m["orders"] == 2


def test_benchmark_difference_requires_exact_match_and_publication_at_decision():
    from src.research_insights import benchmark_comparisons

    outcomes = build_insights([case(status="not_started")], [fact("awarded_roe", "9")], [])[
        "outcomes"
    ]
    record = dict(
        benchmark_id="SYNTHETIC", service="Electric", riders_excluded=True, printed_percent="9.5"
    )
    j = dict(
        candidate_id="TEST",
        service="Electric",
        benchmark_id="SYNTHETIC",
        status="matched",
        available_at_written_date=True,
    )
    assert benchmark_comparisons(outcomes, [j], [record])[0]["award_minus_benchmark_bp"] == "-50"
    j["available_at_written_date"] = False
    assert benchmark_comparisons(outcomes, [j], [record])[0]["award_minus_benchmark_bp"] is None
    j["status"] = "missing_exact_comparable_half_year"
    assert benchmark_comparisons(outcomes, [j], [record]) == []
