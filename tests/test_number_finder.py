"""M5 read-only extraction and conservative attribution, using synthetic text."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.number_finder import NumberFinderError, find_numbers, format_table


def save(tmp_path, texts, scanned=()):
    path = tmp_path / "TEST-M5.json"
    path.write_text(
        json.dumps(
            [
                dict(page=i, text=t, n_chars=len(t), likely_scanned=i in scanned)
                for i, t in enumerate(texts, 1)
            ]
        )
    )
    return path


def run(tmp_path, text, **kwargs):
    return find_numbers(save(tmp_path, [text]), start_page=1, end_page=1, **kwargs)


def test_formats_ranges_words_and_units(tmp_path):
    text = "ROE ranges from 8.5 to 10.25 percent; nine percent; 9.5%; .25 per cent; ten point five percent. ROE adjustment -25 basis points."
    rows = run(tmp_path, text)["candidates"]
    assert [(r["value"], r["unit"]) for r in rows] == [
        ("8.5", "percent"),
        ("10.25", "percent"),
        ("9", "percent"),
        ("9.5", "percent"),
        ("0.25", "percent"),
        ("10.5", "percent"),
        ("-25", "basis_points"),
    ]
    assert rows[0]["unit_inferred_from_range"]
    assert rows[-1]["fraction"] == "-0.0025"
    assert rows[3]["fraction"] == "0.095"


def test_dash_range_does_not_make_negative_endpoint(tmp_path):
    rows = run(tmp_path, "ROE 8–10%; ROE 8-10 percent; ROE −0.25%.")["candidates"]
    assert [r["value"] for r in rows] == ["8", "10", "8", "10", "-0.25"]


def test_ocr_typo_not_silently_repaired(tmp_path):
    rows = run(tmp_path, "ROE l0.5 percent and 9.O% and 9,5 percent.")["candidates"]
    assert rows == []


def test_keep_nearby_non_roe_percentages_and_repeated_occurrences(tmp_path):
    rows = run(
        tmp_path,
        "The Company requests ROE of 9.5 percent with 50 percent common equity. Its ROE is 9.5 percent.",
    )["candidates"]
    assert [r["value"] for r in rows] == ["9.5", "50", "9.5"]
    assert len({r["candidate_id"] for r in rows}) == 3
    assert all(r["verification_status"] == "candidate_only" for r in rows)


def test_window_exact_boundary_and_far_values(tmp_path):
    r = run(tmp_path, "ROE" + " " * 300 + "9.5%", window_chars=300)
    assert len(r["candidates"]) == 1
    assert not run(tmp_path, "ROE" + " " * 301 + "9.5%", window_chars=300)["candidates"]


def test_cross_page_term_and_page_range_fence(tmp_path):
    p = save(tmp_path, ["The return on equity is", "9.5 percent.", "ROE 8 percent."])
    rows = find_numbers(p, start_page=1, end_page=2)["candidates"]
    assert len(rows) == 1 and rows[0]["page"] == 2 and rows[0]["nearest_roe_term"]["page"] == 1
    assert not find_numbers(p, start_page=2, end_page=2)["candidates"]


def test_sentence_retains_decimal_and_abbreviation_and_raw_offsets(tmp_path):
    text = "Earlier statement. Dr. Jones recommends an ROE of 9.50\npercent. Later statement."
    row = run(tmp_path, text)["candidates"][0]
    assert row["sentence"] == "Dr. Jones recommends an ROE of 9.50 percent."
    assert row["raw_match"] == text[row["start_char"] : row["end_char"]]
    assert row["sentence_raw"] == text[row["sentence_start_char"] : row["sentence_end_char"]]


def test_multiple_parties_is_ambiguous_not_award(tmp_path):
    row = run(tmp_path, "The Commission rejects the Company’s proposed ROE of 10.5 percent.")[
        "candidates"
    ][0]
    assert row["attribution_guess"] == "ambiguous"
    assert set(row["attribution_candidates"]) == {"commission", "utility"}
    assert "rejection_or_negation_nearby" in row["flags"]


@pytest.mark.parametrize(
    "actor,expected",
    [
        ("The Company", "utility"),
        ("The OCA", "consumer_advocate"),
        ("The OCC", "consumer_advocate"),
        ("The Department of Energy", "staff"),
        ("The Department of Public Service", "staff"),
        ("The Attorney General", "consumer_advocate"),
        ("The ALJ", "alj"),
        ("The Commission", "commission"),
        ("The Authority", "commission"),
        ("PURA", "commission"),
        ("A witness", "unknown"),
    ],
)
def test_actor_guesses_are_evidenced_not_automatic_verified_fields(tmp_path, actor, expected):
    row = run(tmp_path, actor + " recommends a 9.5 percent ROE.")["candidates"][0]
    assert row["attribution_guess"] == expected
    assert row["verification_status"] == "candidate_only"


def test_percentage_points_and_basis_points_distinct(tmp_path):
    rows = run(tmp_path, "ROE increased 0.25 percentage points; ROE reduced 25-basis points.")[
        "candidates"
    ]
    assert [r["unit"] for r in rows] == ["percentage_points", "basis_points"]
    assert all(r["fraction"] == "0.0025" for r in rows)
    assert all("change_not_level" in r["flags"] for r in rows)


def test_word_hyphenated_roe_and_fullwidth_percent(tmp_path):
    rows = run(tmp_path, "RETURN ON EQUI-\nTY of 9.5％. The cost of common equity is ten percent.")[
        "candidates"
    ]
    assert [r["value"] for r in rows] == ["9.5", "10"]


def test_low_text_warning_and_no_mutations(tmp_path):
    p = save(tmp_path, ["ROE 9.5%"], scanned=(1,))
    before = p.read_bytes()
    r = find_numbers(p, start_page=1, end_page=1)
    assert r["low_text_pages"] == [1]
    assert "low_text_source_page" in r["candidates"][0]["flags"]
    assert p.read_bytes() == before


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(start_page=0, end_page=1),
        dict(start_page=1, end_page=2),
        dict(start_page=True, end_page=1),
        dict(start_page=1, end_page=0),
        dict(start_page=1, end_page=1, window_chars=-1),
        dict(start_page=1, end_page=1, window_chars=True),
    ],
)
def test_bad_ranges_and_config_rejected(tmp_path, kwargs):
    with pytest.raises(NumberFinderError):
        find_numbers(save(tmp_path, ["ROE 9.5%"]), **kwargs)


def test_bad_m2_and_no_match_are_distinct(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}")
    with pytest.raises(NumberFinderError):
        find_numbers(p, start_page=1, end_page=1)
    assert run(tmp_path, "No ROE number is printed.")["candidates"] == []


def test_cli_prints_complete_table_or_json_without_files(tmp_path):
    p = save(tmp_path, ["The Company requests a 9.5% ROE."])
    cmd = [
        sys.executable,
        "-m",
        "src.number_finder",
        str(p),
        "--start-page",
        "1",
        "--end-page",
        "1",
    ]
    before = {x.name: x.read_bytes() for x in tmp_path.iterdir()}
    result = subprocess.run(cmd, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "| 1 |" in result.stdout and "The Company requests" in result.stdout
    result = subprocess.run(cmd + ["--format", "json"], text=True, capture_output=True)
    assert json.loads(result.stdout)["status"] == "candidates_only"
    assert {x.name: x.read_bytes() for x in tmp_path.iterdir()} == before
    result = subprocess.run(cmd + ["--window-chars", "-2"], text=True, capture_output=True)
    assert result.returncode == 2 and not result.stdout and "Traceback" not in result.stderr


def test_markdown_escape_does_not_modify_source_text(tmp_path):
    r = run(tmp_path, "ROE 9.5% | <script>alert(1)</script>.")
    text = format_table(r)
    assert "\\|" in text and "&lt;script&gt;" in text
    assert "<script>" in r["candidates"][0]["sentence"]
