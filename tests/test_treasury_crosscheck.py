"""Synthetic feed fixtures verify identity, missingness and discrepancy handling."""

import pytest

from src.treasury_crosscheck import parse_xml, compare


def xml(entries, title="DailyTreasuryYieldCurveRateData"):
    return (
        f'<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" '
        'xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">'
        f"<title>{title}</title>"
        + "".join(
            f"<entry><content><m:properties><d:NEW_DATE>{day}T00:00:00</d:NEW_DATE>"
            + (
                f"<d:BC_10YEAR>{value}</d:BC_10YEAR>"
                if value is not None
                else '<d:BC_10YEAR m:null="true"/>'
            )
            + "</m:properties></content></entry>"
            for day, value in entries
        )
        + "</feed>"
    ).encode()


def test_xml_sorts_feed_order_and_preserves_decimal_and_null():
    rows = parse_xml(xml([("2025-01-03", "4.40"), ("2025-01-02", None)]), 2025, "2025-01-04")
    assert [r["date"] for r in rows] == ["2025-01-02", "2025-01-03"]
    assert rows[0]["value_fraction"] is None
    assert rows[1]["value_fraction"] == "0.044"


@pytest.mark.parametrize(
    "entries,title,pattern",
    [
        ([("2025-01-02", "4.4")], "DailyTreasuryRealYieldCurveRateData", "identity"),
        ([("2024-01-02", "4.4")], "DailyTreasuryYieldCurveRateData", "year"),
        ([("2025-01-05", "4.4")], "DailyTreasuryYieldCurveRateData", "future"),
        (
            [("2025-01-02", "4.4"), ("2025-01-02", "4.4")],
            "DailyTreasuryYieldCurveRateData",
            "duplicated",
        ),
        ([], "DailyTreasuryYieldCurveRateData", "Empty"),
    ],
)
def test_unusable_feed_is_rejected(entries, title, pattern):
    with pytest.raises(ValueError, match=pattern):
        parse_xml(xml(entries, title), 2025, "2025-01-04")


def test_compare_records_one_bp_disagreement_without_replacing_values():
    fred = [
        dict(date="2025-01-02", value_fraction="0.044"),
        dict(date="2025-01-03", value_fraction=None),
    ]
    treasury = [
        dict(date="2025-01-02", value_fraction="0.0441"),
        dict(date="2025-01-03", value_fraction="0.043"),
        dict(date="2025-01-04", value_fraction="0.04"),
    ]
    rows = compare(fred, treasury)
    assert len(rows) == 2
    assert rows[0]["status"] == "disagreement" and rows[0]["treasury_minus_fred_bp"] == "1.0000"
    assert rows[1]["status"] == "missing_value" and rows[1]["treasury_minus_fred_bp"] is None
    assert fred[0]["value_fraction"] == "0.044"
    with pytest.raises(ValueError, match="Duplicate"):
        compare(fred + fred, treasury)
