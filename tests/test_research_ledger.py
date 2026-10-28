"""Integrity failures that would invalidate the new empirical evidence release."""

import copy
import json

import pytest

from src.research_ledger import CODES, LedgerError, fingerprint, validate_ledger


@pytest.fixture
def bundle(tmp_path):
    # Synthetic fixtures only; no dependence on the researcher's local PDFs.
    text = "The witness recommends 9.35 percent.\nHeading\nWe adopt the estimate."
    (tmp_path / "source.pdf").write_bytes(b"SYNTHETIC PDF FINGERPRINT FIXTURE")
    (tmp_path / "pages.json").write_text(json.dumps([{"page": 1, "text": text}]))
    (tmp_path / "visual.png").write_bytes(b"SYNTHETIC VISUAL FINGERPRINT FIXTURE")

    def span(a, b):
        return dict(page=1, start_char=a, end_char=b, exact_text=text[a:b])

    first = text.index("\n")
    last = text.index("We adopt")
    ledger = dict(
        schema_version="1.0",
        sample_status="not_finalized",
        coding_origin="assistant_assisted",
        independent_reliability="not_measured",
        coder="Synthetic test coder",
        codebook_version="test",
        coding_date="2026-10-01",
        frame_cutoff="2026-10-01",
        sources=[
            dict(
                source_id="SRC",
                pdf_path="source.pdf",
                pdf_sha256=fingerprint(tmp_path / "source.pdf"),
                text_path="pages.json",
                text_sha256=fingerprint(tmp_path / "pages.json"),
                n_pages=1,
                source_url="https://example.org/synthetic",
            )
        ],
        cases=[
            dict(
                case_id="TEST",
                source_ids=["SRC"],
                order_date="2025-03-13",
                coding_status="first_pass_complete",
                reviewed_scopes=[dict(span(0, len(text)), source_id="SRC")],
                excluded_spans=[dict(span(first + 1, last - 1), source_id="SRC", reason="Heading")],
            )
        ],
        passages=[],
        numeric_facts=[],
    )
    for index, (a, b, section, stance) in enumerate(
        [
            (0, first, "Positions of parties", "Summarized only"),
            (last, len(text), "Commission analysis", "Relied on"),
        ]
    ):
        ledger["passages"].append(
            dict(
                passage_id=f"U{index}",
                case_id="TEST",
                source_id="SRC",
                unit_type="paragraph",
                section=section,
                codes={c: int(c == "MKT") for c in CODES},
                stances={"MKT": stance},
                primary_code="MKT",
                method="Unspecified",
                notes="Synthetic rationale",
                spans=[span(a, b)],
                text=text[a:b],
            )
        )
    ledger["numeric_facts"] = [
        dict(
            fact_id="F1",
            case_id="TEST",
            source_id="SRC",
            relation="equal",
            printed_unit="percent",
            printed_value="9.35",
            value_fraction="0.0935",
            event_date="2025-03-13",
            spans=[span(0, first)],
            visual_check=dict(
                page=1,
                path="visual.png",
                sha256=fingerprint(tmp_path / "visual.png"),
                reviewer="Synthetic reviewer",
                checked_date="2026-10-01",
            ),
            notes="Synthetic fact",
        )
    ]
    return tmp_path, ledger


def run(bundle, ledger=None):
    root, original = bundle
    path = root / "ledger.json"
    path.write_text(json.dumps(original if ledger is None else ledger))
    return validate_ledger(path, root=root)


def test_valid_cross_voice_bundle(bundle):
    result = run(bundle)
    assert (result["n_cases"], result["n_passages"], result["n_new_numeric_facts"]) == (1, 2, 1)
    assert result["coverage"][0]["nonwhitespace_coverage"] == "complete"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda d: d["passages"][0]["spans"][0].update(exact_text="invented"), "evidence differs"),
        (lambda d: d["passages"][0]["stances"].update(MKT="Relied on"), "Party summaries"),
        (lambda d: d["passages"][0].update(primary_code="OWN"), "Primary code"),
        (lambda d: d["passages"][0]["stances"].update(PEER="Considered"), "Each active code"),
        (lambda d: d["passages"][0]["codes"].update(MKT=True), "binary integers"),
        (lambda d: d["cases"][0].update(excluded_spans=[]), "Unaccounted source"),
        (lambda d: d["passages"].append(copy.deepcopy(d["passages"][0])), "Duplicate passage"),
        (lambda d: d["numeric_facts"][0].update(value_fraction="9.35"), "conversion"),
        (
            lambda d: d["numeric_facts"][0].update(printed_value="9.3", value_fraction="0.093"),
            "Printed number",
        ),
        (lambda d: d["numeric_facts"][0]["visual_check"].update(page=2), "different page"),
        (lambda d: d["sources"][0].update(pdf_path="../outside.pdf"), "escapes project"),
        (lambda d: d["cases"][0].update(coding_status="not_started"), "Coding status"),
        (lambda d: d.update(independent_reliability="measured"), "Reliability"),
        (lambda d: d["numeric_facts"][0].update(event_date="2027-01-01"), "Future numeric"),
    ],
)
def test_rejects_broken_evidence(bundle, mutation, message):
    data = copy.deepcopy(bundle[1])
    mutation(data)
    with pytest.raises(LedgerError, match=message):
        run(bundle, data)


def test_fingerprints_detect_source_mutation(bundle):
    (bundle[0] / "source.pdf").write_bytes(b"CHANGED")
    with pytest.raises(LedgerError, match="fingerprint changed"):
        run(bundle)


def test_zero_code_structural_unit_is_preserved(bundle):
    unit = bundle[1]["passages"][1]
    unit.update(codes=dict.fromkeys(CODES, 0), stances={}, primary_code=None, method="n.a.")
    assert run(bundle)["n_passages"] == 2


def test_uncoded_case_never_reports_complete_coverage(bundle):
    data = bundle[1]
    data["cases"].append(
        dict(
            case_id="UNREVIEWED",
            source_ids=["SRC"],
            order_date="2025-03-13",
            coding_status="not_started",
            reviewed_scopes=[],
            excluded_spans=[],
        )
    )
    assert run(bundle)["coverage"][1]["nonwhitespace_coverage"] == "not_reviewed"


def test_sample_cutoff_does_not_prohibit_later_coding_or_source_review(bundle):
    data = bundle[1]
    data["release_date"] = "2026-10-02"
    data["passages"][0]["coding_date"] = "2026-10-02"
    data["numeric_facts"][0]["visual_check"]["checked_date"] = "2026-10-02"
    assert run(bundle)["status"] == "passed"
    data["passages"][0]["coding_date"] = "2026-10-03"
    with pytest.raises(LedgerError, match="exceeds release"):
        run(bundle)
