from datetime import datetime, timezone
import json

import pymupdf
import pytest
import requests

from src.source_acquisition import acquire

NOW = datetime(2026, 10, 2, 18, tzinfo=timezone.utc)


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "data/research"
    path.mkdir(parents=True)
    source = dict(
        source_id="CAND-MA-TEST",
        state="MA",
        docket="TEST",
        order_date="2025-01-01",
        title="Synthetic source acquisition fixture",
        source_url="https://www.mass.gov/synthetic.pdf",
        landing_url="https://www.mass.gov/synthetic",
    )
    (path / "source_queue.json").write_text(json.dumps({"sources": [source]}))
    (path / "source_catalog.json").write_text(json.dumps({"sources": [], "n_documents": 0}))
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "SYNTHETIC TEST DOCUMENT")
    content = document.tobytes()
    document.close()

    class Response:
        url = source["source_url"]

        def raise_for_status(self):
            pass

    class Session:
        calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            r = Response()
            r.content = content
            return r

    return tmp_path, source, Session()


def test_register_extract_publish_and_repeat_without_network(project):
    root, source, session = project
    result = acquire(source["source_id"], root, session=session, now=NOW)
    assert result["status"] == "acquired" and result["source"]["n_pages"] == 1
    assert "SYNTHETIC" in json.loads((root / result["source"]["text_path"]).read_text())[0]["text"]
    assert (
        acquire(source["source_id"], root, session=session, now=NOW)["status"] == "already_acquired"
    )
    assert session.calls == 1


@pytest.mark.parametrize(
    "url", ["https://unreviewed.example/test.pdf", "http://www.mass.gov/test.pdf"]
)
def test_unreviewed_endpoint_fails_before_network(project, url):
    root, source, session = project
    source["source_url"] = url
    (root / "data/research/source_queue.json").write_text(json.dumps({"sources": [source]}))
    with pytest.raises(ValueError, match="reviewed official"):
        acquire(source["source_id"], root, session=session, now=NOW)
    assert session.calls == 0


def test_html_or_unreviewed_redirect_does_not_enter_library(project):
    root, source, _ = project

    class Response:
        url = source["source_url"]
        content = b"<html>access denied</html>"

        def raise_for_status(self):
            pass

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    with pytest.raises(ValueError, match="non-PDF"):
        acquire(source["source_id"], root, session=Session(), now=NOW)
    assert json.loads((root / "data/research/source_catalog.json").read_text())["n_documents"] == 0
    assert not list((root / "data/research").rglob("*.pdf"))
    Response.url = "https://unreviewed.example/redirect.pdf"
    with pytest.raises(ValueError, match="redirect"):
        acquire(source["source_id"], root, session=Session(), now=NOW)


def test_saved_source_mutation_fails_and_is_not_redownloaded(project):
    root, source, session = project
    result = acquire(source["source_id"], root, session=session, now=NOW)
    (root / result["source"]["pdf_path"]).write_bytes(b"CHANGED")
    with pytest.raises(ValueError, match="changed"):
        acquire(source["source_id"], root, session=session, now=NOW)
    assert session.calls == 1


def test_failed_network_does_not_create_registration(project):
    root, source, _ = project

    class Failed:
        def get(self, *args, **kwargs):
            raise requests.HTTPError("HTTP 403")

    with pytest.raises(ValueError, match="download failed"):
        acquire(source["source_id"], root, session=Failed(), now=NOW)
    assert not (root / "data/empirical_manifest.csv").exists()


def test_unknown_queue_id_cannot_choose_arbitrary_file(project):
    root, _, session = project
    with pytest.raises(ValueError, match="uniquely listed"):
        acquire("../../outside", root, session=session, now=NOW)
    assert session.calls == 0


def test_interrupted_extraction_resumes_next_day_without_redownload(project, monkeypatch):
    import src.source_acquisition as acquisition

    root, source, session = project
    original_extract = acquisition.extract_case

    def failed_extract(*args, **kwargs):
        raise OSError("Interrupted extraction")

    monkeypatch.setattr(acquisition, "extract_case", failed_extract)
    with pytest.raises(OSError, match="Interrupted"):
        acquire(source["source_id"], root, session=session, now=NOW)
    monkeypatch.setattr(acquisition, "extract_case", original_extract)
    later = datetime(2026, 10, 3, 18, tzinfo=timezone.utc)
    result = acquire(source["source_id"], root, session=session, now=later)
    assert result["status"] == "acquired"
    assert result["source"]["download_date"] == "2026-10-02"
    assert "acquisition_2026-10-02/" in result["source"]["pdf_path"]
    assert session.calls == 1


def test_invalid_pdf_does_not_create_registration(project):
    root, source, _ = project

    class Response:
        url = source["source_url"]
        content = b"%PDF-1.7\ninvalid document"

        def raise_for_status(self):
            pass

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    with pytest.raises(ValueError, match="invalid"):
        acquire(source["source_id"], root, session=Session(), now=NOW)
    assert not (root / "data/empirical_manifest.csv").exists()
    assert not list((root / "data/research").rglob("*.pdf"))


def test_supporting_event_is_not_published_as_a_final_order(project):
    root, source, session = project
    source.update(
        source_id="SUPP-MA-TEST-MINUTES",
        order_date="",
        event_date="2025-01-01",
        source_kind="official_draft_minutes",
        review_status="supporting_only",
        role="Synthetic draft meeting minutes; not a final reasoned order.",
    )
    (root / "data/research/source_queue.json").write_text(json.dumps({"sources": [source]}))
    record = acquire(source["source_id"], root, session=session, now=NOW)["source"]
    assert record["order_date"] == "" and record["event_date"] == "2025-01-01"
    assert record["source_kind"] == "official_draft_minutes"
    assert record["review_status"] == "supporting_only" and record["role"] == source["role"]


def test_minutes_cannot_receive_a_written_order_date(project):
    root, source, session = project
    source.update(
        source_id="SUPP-MA-TEST-MINUTES",
        event_date="2025-01-01",
        source_kind="official_draft_minutes",
        review_status="supporting_only",
        role="Draft minutes",
    )
    (root / "data/research/source_queue.json").write_text(json.dumps({"sources": [source]}))
    with pytest.raises(ValueError, match="event dates"):
        acquire(source["source_id"], root, session=session, now=NOW)
    assert session.calls == 0


@pytest.mark.parametrize(
    "changes", [{"event_date": "2027-01-01"}, {"review_status": "candidate_pending_review"}]
)
def test_invalid_supporting_classification_or_future_event_fails_before_download(project, changes):
    root, source, session = project
    source.update(
        source_id="SUPP-MA-TEST-MINUTES",
        order_date="",
        event_date="2025-01-01",
        source_kind="official_draft_minutes",
        review_status="supporting_only",
        role="Draft minutes",
    )
    source.update(changes)
    (root / "data/research/source_queue.json").write_text(json.dumps({"sources": [source]}))
    with pytest.raises(ValueError):
        acquire(source["source_id"], root, session=session, now=NOW)
    assert session.calls == 0


def test_candidate_decision_cannot_use_only_a_filing_event_date(project):
    root, source, session = project
    source.update(order_date="", event_date="2025-01-01")
    (root / "data/research/source_queue.json").write_text(json.dumps({"sources": [source]}))
    with pytest.raises(ValueError, match="written order date"):
        acquire(source["source_id"], root, session=session, now=NOW)
    assert session.calls == 0
