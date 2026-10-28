"""M3 contract and failure cases, using invented text rather than pilot labels."""

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.locate_roe import LocatorError, locate_roe


def save_pages(tmp_path, texts, scanned=()):
    path = tmp_path / "TEST-M3.json"
    path.write_text(
        json.dumps(
            [
                dict(page=i, text=text, n_chars=len(text), likely_scanned=i in scanned)
                for i, text in enumerate(texts, 1)
            ]
        )
    )
    return path


def test_body_outranks_contents_and_incidental_mention(tmp_path):
    path = save_pages(
        tmp_path,
        [
            "TABLE OF CONTENTS\nReturn on Equity ............ 90\nDCF ............ 91\nCAPM ............ 92",
            "Customer service. A passing ROE reference.",
            "Unrelated tariff text.",
            "E.\nReturn on Equity\nThe cost of equity is discussed with DCF and CAPM.",
            "The proxy group supports this ROE discussion. DCF and CAPM are compared.",
            "This ROE conclusion addresses the cost of equity.",
            "Unrelated tariff text.",
        ],
    )
    before = path.read_bytes()
    result = locate_roe(path)
    top = result["candidates"][0]
    assert (top["start_page"], top["end_page"]) == (4, 6)
    assert result["suppressed_contents_pages"] == [1]
    assert result["status"] == "suggestions_only"
    assert result["confirmed_range"] is None
    assert result["human_top_hit"] is None
    assert path.read_bytes() == before


def test_all_seven_terms_are_counted_with_word_boundaries(tmp_path):
    path = save_pages(
        tmp_path,
        ["return on equity; cost of equity; cost of capital; ROEs; proxy groups; DCF; ECAPM"],
    )
    counts = locate_roe(path)["candidates"][0]["term_counts"]
    assert counts == {
        "return on equity": 1,
        "cost of equity": 1,
        "cost of capital": 1,
        "ROE": 1,
        "proxy group": 1,
        "DCF": 1,
        "CAPM": 1,
    }
    path = save_pages(tmp_path, ["A roe deer. Macroecology. DCFish. CAPMaker."])
    # ROE is case-insensitive, but one incidental acronym cannot seed a range.
    assert locate_roe(path)["candidates"] == []


def test_line_wrapping_hyphens_and_case_are_search_only(tmp_path):
    path = save_pages(
        tmp_path,
        [
            "RETURN ON EQUI-\nTY\nThe cost of\nequity and proxy\ngroup are discussed with dcf and capm."
        ],
    )
    before = path.read_bytes()
    result = locate_roe(path)
    assert result["candidates"][0]["term_counts"]["return on equity"] == 1
    assert result["candidates"][0]["term_counts"]["cost of equity"] == 1
    assert path.read_bytes() == before


def test_repeated_running_heading_does_not_make_whole_order_a_match(tmp_path):
    path = save_pages(
        tmp_path,
        [
            "RETURN ON EQUITY\nPage 1\nBilling tariff discussion.",
            "RETURN ON EQUITY\nPage 2\nCustomer class discussion.",
            "RETURN ON EQUITY\nPage 3\nMeter replacement discussion.",
            "RETURN ON EQUITY\nPage 4\nThe cost of equity and DCF support a CAPM comparison.",
        ],
    )
    result = locate_roe(path)
    assert [(r["start_page"], r["end_page"]) for r in result["candidates"]] == [(4, 4)]
    assert "return on equity" in result["suppressed_repeated_edge_lines"]


def test_sparse_gap_is_bridged_and_reported(tmp_path):
    path = save_pages(
        tmp_path,
        ["Return on Equity\nDCF and CAPM.", "", "The cost of equity and ROE."],
        scanned=(2,),
    )
    result = locate_roe(path)
    top = result["candidates"][0]
    assert (top["start_page"], top["end_page"]) == (1, 3)
    assert top["gap_pages"] == [2]
    assert top["low_text_pages"] == [2]
    assert result["warnings"]


def test_long_gap_creates_distinct_ranges(tmp_path):
    path = save_pages(
        tmp_path,
        [
            "The cost of equity and ROE.",
            "Tariffs.",
            "Meters.",
            "Fees.",
            "Return on Equity\nDCF and CAPM.",
        ],
    )
    ranges = locate_roe(path)["candidates"]
    assert {(c["start_page"], c["end_page"]) for c in ranges} == {(1, 1), (5, 5)}
    assert ranges[0]["start_page"] == 5


def test_toc_is_a_barrier_even_with_large_gap_setting(tmp_path):
    path = save_pages(
        tmp_path,
        [
            "The cost of equity and ROE.",
            "DCF ........ 40\nCAPM ........ 41",
            "The cost of equity and ROE.",
        ],
    )
    ranges = locate_roe(path, max_gap_pages=5)["candidates"]
    assert [(r["start_page"], r["end_page"]) for r in ranges] == [(1, 1), (3, 3)]


def test_strong_heading_trims_earlier_context_without_hiding_it(tmp_path):
    path = save_pages(
        tmp_path,
        [
            "Cost of Capital\nThe proxy group and cost of capital.",
            "Capital structure and the proxy group. ROE.",
            "E. Return on Equity\nThe cost of equity, DCF and CAPM.",
            "The cost of equity and ROE.",
        ],
    )
    top = locate_roe(path)["candidates"][0]
    assert (top["start_page"], top["end_page"]) == (3, 4)
    assert top["context_start_page"] == 1
    assert top["heading_pages"] == [3]


def test_no_match_is_empty_with_no_invented_range(tmp_path):
    result = locate_roe(save_pages(tmp_path, ["Unrelated tariffs.", "", "Other fees."]))
    assert result["candidates"] == []
    assert result["warnings"]


def test_deterministic_tie_breaking_and_top_n(tmp_path):
    path = save_pages(tmp_path, ["The cost of equity.", "", "", "", "The cost of equity."])
    first = locate_roe(path, top_n=1)
    assert first == locate_roe(path, top_n=1)
    assert first["candidates"][0]["start_page"] == 1
    assert first["total_candidates"] == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("page", 0),
        ("page", True),
        ("page", 2),
        ("page", 1.0),
        ("text", None),
        ("n_chars", 999),
        ("n_chars", True),
        ("likely_scanned", 1),
    ],
)
def test_rejects_invalid_m2_records(tmp_path, field, value):
    path = save_pages(tmp_path, ["Return on Equity"])
    rows = json.loads(path.read_text())
    rows[0][field] = value
    path.write_text(json.dumps(rows))
    with pytest.raises(LocatorError, match="page|text|n_chars|likely_scanned"):
        locate_roe(path)


@pytest.mark.parametrize("payload", ["[]", "{}", "not json", '[{"page":1,"page":2}]'])
def test_rejects_invalid_top_level_or_duplicate_json_keys(tmp_path, payload):
    path = tmp_path / "bad.json"
    path.write_text(payload)
    with pytest.raises(LocatorError):
        locate_roe(path)


def test_rejects_extra_fields_and_out_of_order_pages(tmp_path):
    path = save_pages(tmp_path, ["One.", "Two."])
    rows = json.loads(path.read_text())
    changed = copy.deepcopy(rows)
    changed[0]["code"] = "MKT"
    path.write_text(json.dumps(changed))
    with pytest.raises(LocatorError, match="schema"):
        locate_roe(path)
    path.write_text(json.dumps(rows[::-1]))
    with pytest.raises(LocatorError, match="page"):
        locate_roe(path)


@pytest.mark.parametrize(
    "options",
    [
        dict(top_n=0),
        dict(top_n=True),
        dict(max_gap_pages=-1),
        dict(max_gap_pages=1.5),
        dict(min_page_score=0),
    ],
)
def test_rejects_invalid_parameters(tmp_path, options):
    path = save_pages(tmp_path, ["Return on Equity"])
    with pytest.raises(LocatorError):
        locate_roe(path, **options)


def test_cli_is_read_only_and_reports_failure_cleanly(tmp_path):
    path = save_pages(tmp_path, ["Return on Equity\nThe cost of equity."])
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    command = [sys.executable, "-m", "src.locate_roe", str(path)]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "suggestions_only"
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == before
    path.write_text('{"bad":true}')
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
