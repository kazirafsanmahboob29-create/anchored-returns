"""Synthetic observations test import integrity without creating research ratings."""

import copy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from src.research_ledger import CODES, fingerprint
from src.research_reliability import (
    build_packet,
    evaluate_ratings,
    packet_status,
    export_rater_kit,
    rating_preflight,
    PACKET_ID,
)


@pytest.fixture
def packet_bundle(tmp_path):
    directory = tmp_path / "data/research"
    directory.mkdir(parents=True)
    (tmp_path / "project_docs").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "presentation").mkdir()
    (tmp_path / "project_docs/Anchored_Returns_Codebook_v0.1.2.docx").write_bytes(
        b"SYNTHETIC CODEBOOK HASH FIXTURE"
    )
    (tmp_path / "docs/empirical_protocol_v0.1.3.md").write_text("SYNTHETIC AMENDMENT")
    (tmp_path / "presentation/reliability.html").write_text(
        "<script>__PACKET__</script><script>__BLANK__</script>"
    )
    (tmp_path / "source.pdf").write_bytes(b"SYNTHETIC SOURCE HASH FIXTURE")
    lines = [
        "SYNTHETIC Market reasoning.",
        "SYNTHETIC Structural unit.",
        "SYNTHETIC Further market reasoning.",
    ]
    text = "\n".join(lines)
    (tmp_path / "pages.json").write_text(json.dumps([dict(page=1, text=text)]))
    source = dict(
        source_id="SRC",
        pdf_path="source.pdf",
        pdf_sha256=fingerprint(tmp_path / "source.pdf"),
        text_path="pages.json",
        text_sha256=fingerprint(tmp_path / "pages.json"),
        source_url="https://example.org/synthetic",
        n_pages=1,
    )
    cases = []
    passages = []
    offset = 0
    for i, line in enumerate(lines):
        span = dict(page=1, start_char=offset, end_char=offset + len(line), exact_text=line)
        offset += len(line) + 1
        cases.append(
            dict(
                case_id=f"TEST{i}",
                source_ids=["SRC"],
                order_date="2025-01-01",
                coding_status="first_pass_complete",
                reviewed_scopes=[dict(span, source_id="SRC")],
                excluded_spans=[],
            )
        )
        positive = i != 1
        passages.append(
            dict(
                passage_id=f"TEST{i}-U",
                case_id=f"TEST{i}",
                source_id="SRC",
                section="Commission analysis",
                unit_type="paragraph",
                codes={c: int(c == "MKT" and positive) for c in CODES},
                stances={"MKT": "Relied on"} if positive else {},
                primary_code="MKT" if positive else None,
                method="Unspecified" if positive else "n.a.",
                notes="SYNTHETIC RATIONALE NOT FOR RATERS",
                spans=[span],
                text=line,
            )
        )
    ledger = dict(
        schema_version="1.0",
        sample_status="not_finalized",
        coding_origin="assistant_assisted",
        independent_reliability="not_measured",
        coder="Reference coding pass",
        codebook_version="SYNTHETIC TEST",
        coding_date="2026-10-01",
        frame_cutoff="2026-10-01",
        sources=[source],
        cases=cases,
        passages=passages,
        numeric_facts=[],
    )
    (directory / "empirical_ledger_v0.1.3.json").write_text(json.dumps(ledger))
    status = build_packet(tmp_path)
    return tmp_path, status


def synthetic_completed(bundle, identity="Synthetic test rater A"):
    root, status = bundle
    base = root / "data/research/reliability" / PACKET_ID
    data = json.loads((base / "rater/ratings_blank.json").read_text())
    reference = json.loads(
        (root / "data/research/reliability_baselines" / (PACKET_ID + ".json")).read_text()
    )["reference_ratings"]
    data["rater"].update(
        identity=identity,
        started_at_utc=status["frozen_at_utc"],
        completed_at_utc=datetime.now(timezone.utc).isoformat(),
        did_not_consult_reference_labels=True,
    )
    for r, ref in zip(data["ratings"], reference):
        r["codes"] = ref["codes"]
    return data


def write(root, name, data):
    path = root / name
    path.write_text(json.dumps(data))
    return path


def test_packet_preserves_zero_code_units_and_omits_reference_labels(packet_bundle):
    root, status = packet_bundle
    assert status["units"] == 3
    packet = (root / "data/research/reliability" / PACKET_ID / "rater/packet.json").read_text()
    assert "Structural unit" in packet and "SYNTHETIC RATIONALE" not in packet
    assert "primary_code" not in packet and "stances" not in packet and '"MKT":' not in packet
    assert build_packet(root) == status


def test_blank_workspace_is_not_reliability_evidence(packet_bundle):
    root, _ = packet_bundle
    path = root / "data/research/reliability" / PACKET_ID / "rater/ratings_blank.json"
    with pytest.raises(ValueError, match="rater identity"):
        evaluate_ratings(root, path)


def test_preflight_reports_blanks_without_agreement(packet_bundle):
    root, _ = packet_bundle
    path = root / "data/research/reliability" / PACKET_ID / "rater/ratings_blank.json"
    report = rating_preflight(root, path)
    assert report["status"] == "not_ready" and report["blank_code_cells"] == 3 * len(CODES)
    assert report["complete_units"] == 0 and report["agreement"] is None


def test_preflight_rejects_duplicates_boolean_cells_and_wrong_packet(packet_bundle):
    root, _ = packet_bundle
    data = synthetic_completed(packet_bundle)
    path = write(root, "fixture_draft.json", data)
    assert rating_preflight(root, path)["status"] == "ready_for_comparison"
    data["ratings"][0]["codes"]["MKT"] = True
    data["ratings"].append(copy.deepcopy(data["ratings"][0]))
    report = rating_preflight(root, write(root, "fixture_bad.json", data))
    assert report["invalid_code_cells"] == 2 and report["duplicate_units"] == 1
    data["packet_sha256"] = "wrong"
    assert (
        rating_preflight(root, write(root, "fixture_wrong_packet.json", data))["status"]
        == "not_ready"
    )


def test_comparison_types_and_undefined_kappa_are_explicit(packet_bundle):
    root, _ = packet_bundle
    a = write(root, "synthetic_a.json", synthetic_completed(packet_bundle))
    first = evaluate_ratings(root, a)
    assert first["comparison_type"] == "human_assistant"
    assert first["results"]["MKT"]["kappa"] == 1
    assert first["results"]["OWN"]["kappa"] is None and first["main_code_target_met"] is False
    b = write(
        root, "synthetic_b.json", synthetic_completed(packet_bundle, "Synthetic test rater B")
    )
    assert evaluate_ratings(root, a, b)["comparison_type"] == "human_human"
    with pytest.raises(ValueError, match="distinct raters"):
        evaluate_ratings(root, a, a)


@pytest.mark.parametrize(
    "mutation,message",
    [
        (lambda d: d["rater"].update(kind="assistant"), "actual separately"),
        (lambda d: d["rater"].update(identity="Reference coding pass"), "rater identity"),
        (lambda d: d["rater"].update(did_not_consult_reference_labels=False), "blinding"),
        (lambda d: d["rater"].update(started_at_utc="2000-01-01T00:00:00Z"), "predate"),
        (lambda d: d["rater"].update(completed_at_utc="2099-01-01T00:00:00Z"), "future-dated"),
        (lambda d: d["ratings"][0]["codes"].update(MKT=True), "booleans"),
        (lambda d: d["ratings"][0]["codes"].update(MKT=None), "blanks"),
        (lambda d: d["ratings"].pop(), "Missing or extra"),
        (lambda d: d["ratings"].append(copy.deepcopy(d["ratings"][0])), "Duplicate"),
        (lambda d: d.update(packet_sha256="altered"), "different frozen"),
    ],
)
def test_rejects_invalid_separate_observations(packet_bundle, mutation, message):
    root, _ = packet_bundle
    data = synthetic_completed(packet_bundle)
    mutation(data)
    with pytest.raises(ValueError, match=message):
        evaluate_ratings(root, write(root, "synthetic_ratings.json", data))


@pytest.mark.parametrize(
    "target,message",
    [
        ("data/research/reliability/" + PACKET_ID + "/rater/packet.json", "rater packet changed"),
        ("data/research/reliability_baselines/" + PACKET_ID + ".json", "reference changed"),
        ("docs/empirical_protocol_v0.1.3.md", "amendment changed"),
        ("data/research/reliability_baselines/" + PACKET_ID + ".ledger.json", "ledger changed"),
    ],
)
def test_frozen_inputs_cannot_change_during_rating(packet_bundle, target, message):
    root, _ = packet_bundle
    path = root / target
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match=message):
        packet_status(root)


def test_new_case_entries_do_not_change_a_frozen_comparison(packet_bundle):
    root, status = packet_bundle
    path = root / "data/research/empirical_ledger_v0.1.3.json"
    ledger = json.loads(path.read_text())
    ledger["cases"].append(
        dict(
            case_id="LATER",
            source_ids=["SRC"],
            order_date="2025-02-01",
            coding_status="not_started",
            reviewed_scopes=[],
            excluded_spans=[],
        )
    )
    path.write_text(json.dumps(ledger))
    assert build_packet(root) == status
    a = write(root, "synthetic_later_rating.json", synthetic_completed(packet_bundle))
    assert evaluate_ratings(root, a)["results"]["MKT"]["kappa"] == 1


def test_portable_kit_preserves_definitions_and_excludes_reference_labels(packet_bundle):
    root, status = packet_bundle
    output = root / "blinded.zip"
    before = {
        str(p): p.read_bytes() for p in (root / "data/research/reliability_baselines").glob("*")
    }
    report = export_rater_kit(root, output)
    assert report["status"] == "materials_only_no_completed_ratings"
    assert report["packet_sha256"] == status["packet_sha256"]
    with ZipFile(output) as archive:
        names = archive.namelist()
        assert len(names) == 7
        assert not any("baseline" in name or "ledger" in name for name in names)
        html = archive.read(
            "Anchored_Returns_Rater_Kit/data/research/reliability/"
            + PACKET_ID
            + "/rater/index.html"
        )
        assert b"SYNTHETIC RATIONALE" not in html
        assert (
            archive.read(
                "Anchored_Returns_Rater_Kit/project_docs/Anchored_Returns_Codebook_v0.1.2.docx"
            )
            == b"SYNTHETIC CODEBOOK HASH FIXTURE"
        )
        archive.extractall(root / "unpacked")
    assert (root / "unpacked/Anchored_Returns_Rater_Kit/docs/empirical_protocol_v0.1.3.md").exists()
    assert all(Path(p).read_bytes() == data for p, data in before.items())
    with pytest.raises(FileExistsError):
        export_rater_kit(root, output)


@pytest.mark.parametrize(
    "target,mutation,message",
    [
        (
            "ratings_blank.json",
            lambda d: d["rater"].update(identity="Existing rater"),
            "unfilled identity",
        ),
        (
            "ratings_blank.json",
            lambda d: d["ratings"][0]["codes"].update(MKT=1),
            "only blank ratings",
        ),
        ("index.html", None, "blinded template"),
    ],
)
def test_kit_rejects_filled_or_modified_rater_materials(packet_bundle, target, mutation, message):
    root, _ = packet_bundle
    path = root / "data/research/reliability" / PACKET_ID / "rater" / target
    if mutation:
        data = json.loads(path.read_text())
        mutation(data)
        path.write_text(json.dumps(data))
    else:
        path.write_text(path.read_text() + "reference_ratings: leaked")
    with pytest.raises(ValueError, match=message):
        export_rater_kit(root, root / "rejected.zip")
    assert not (root / "rejected.zip").exists()
