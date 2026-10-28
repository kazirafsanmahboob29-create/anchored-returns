"""Exercise the app's HTTP and publication contracts with isolated fixtures."""

from contextlib import contextmanager
import hashlib
from io import BytesIO
import json
from pathlib import Path
from threading import Event, Thread
import time
from zipfile import ZipFile

import pytest
import requests
import fitz

from src.research_server import make_server, markdown_html, PUBLISH_PATHS


@pytest.fixture
def site_root(tmp_path):
    for folder in ("presentation", "reports", "docs", "analysis", "data/research"):
        (tmp_path / folder).mkdir(parents=True)
    # Isolated transport fixture, never registered as research evidence.
    with fitz.open() as pdf:
        first = pdf.new_page()
        first.insert_text((72, 72), "SYNTHETIC HTTP TEST PAGE <script>")
        second = pdf.new_page()
        second.insert_text((72, 72), "SYNTHETIC SECOND PAGE")
        pdf.save(tmp_path / "data/research/test.pdf")
    (tmp_path / "docs/test.md").write_text(
        "# Fixture\n\nA **public** paragraph.\n\n| Key | Value |\n|---|---|\n| A | 1 |\n"
    )
    (tmp_path / "presentation/styles.css").write_text("body { color: #123; }")
    (tmp_path / ".env").write_text("SYNTHETIC_SECRET_MUST_NOT_BE_SERVED")
    (tmp_path / "reports/private.bin").write_bytes(b"SYNTHETIC UNLISTED FILE")
    payload = dict(
        date="2026-10-03",
        stats={"documents": 1},
        treasury=None,
        sources=[
            {
                "pdf_path": "data/research/test.pdf",
                "title": "Isolated transport fixture",
                "pdf_sha256": hashlib.sha256(
                    (tmp_path / "data/research/test.pdf").read_bytes()
                ).hexdigest(),
            }
        ],
        benchmarks={"sources": []},
        reliability={"status": "packet_not_built"},
    )
    html = '<script id="research-data" type="application/json">' + json.dumps(payload) + "</script>"
    (tmp_path / "presentation/index.html").write_text(html)
    (tmp_path / "reports/presentation_build.json").write_text(
        json.dumps({"output_sha256": hashlib.sha256(html.encode()).hexdigest()})
    )
    return tmp_path


@contextmanager
def running(root, runner=None):
    server = make_server(root, port=0, prepare=False, refresh_runner=runner)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def headers(server):
    return {
        "Origin": f"http://127.0.0.1:{server.server_port}",
        "Content-Type": "application/json",
        "X-Research-Token": server.app.token,
    }


def test_public_context_registry_and_reader_preserve_original_checksums(site_root):
    folder = site_root / "data/external"
    folder.mkdir()
    pdf = folder / "context.pdf"
    pdf.write_bytes((site_root / "data/research/test.pdf").read_bytes())
    record = dict(
        pdf_path="data/external/context.pdf",
        pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
        title="Synthetic context transport fixture",
        source_url="https://documents.dps.ny.gov/public/test-fixture",
    )
    (folder / "rra_context_sources.json").write_text(json.dumps({"sources": [record]}))
    payload = dict(
        date="2026-10-03",
        stats={},
        treasury=None,
        sources=[],
        benchmarks={"sources": []},
        reliability={"status": "packet_not_built"},
        audit={"context_sources": [record]},
    )
    html = '<script id="research-data" type="application/json">' + json.dumps(payload) + "</script>"
    (site_root / "presentation/index.html").write_text(html)
    (site_root / "reports/presentation_build.json").write_text(
        json.dumps({"output_sha256": hashlib.sha256(html.encode()).hexdigest()})
    )
    with running(site_root) as (_server, url):
        assert requests.get(url + "/data/external/rra_context_sources.json").status_code == 200
        response = requests.get(
            url + "/reader", params={"file": "data/external/context.pdf", "page": 2}
        )
        assert response.status_code == 200 and record["pdf_sha256"] in response.text
        pdf.write_bytes(b"SYNTHETIC CHANGED BYTES")
        rejected = requests.get(
            url + "/reader", params={"file": "data/external/context.pdf", "page": 2}
        )
        assert rejected.status_code == 404 and "Source page unavailable" in rejected.text


def wait_finished(app):
    deadline = time.monotonic() + 3
    while app.status()["job"]["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.01)
    assert app.status()["job"]["status"] != "running"


def test_serves_current_records_with_no_cache_and_readable_documents(site_root):
    with running(site_root) as (server, url):
        status = requests.get(url + "/api/status").json()
        assert status["counts"] == {"documents": 1} and status["service"] == "anchored-returns"
        response = requests.get(url + "/presentation/index.html")
        assert response.headers["Cache-Control"] == "no-store"
        assert "application/json" in response.text
        response = requests.get(url + "/docs/test.md")
        assert response.status_code == 200 and "<table>" in response.text
        assert "<h1>Fixture</h1>" in response.text and "<strong>public</strong>" in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/.env",
        "/.git/config",
        "/src/research_server.py",
        "/reports/private.bin",
        "/docs/%2e%2e/%2e%2e/.env",
    ],
)
def test_static_surface_is_an_allowlist(site_root, path):
    with running(site_root) as (_server, url):
        response = requests.get(url + path)
        assert response.status_code == 404
        assert "SYNTHETIC_SECRET" not in response.text


def test_host_and_cross_origin_post_do_not_start_jobs(site_root):
    with running(site_root) as (server, url):
        assert (
            requests.get(url + "/api/status", headers={"Host": "evil.example"}).status_code == 403
        )
        h = headers(server)
        h["Origin"] = "https://evil.example"
        assert requests.post(url + "/api/refresh", headers=h, data="{}").status_code == 403
        h = headers(server)
        h["X-Research-Token"] = "wrong"
        assert requests.post(url + "/api/refresh", headers=h, data="{}").status_code == 403
        assert server.app.job is None


@pytest.mark.parametrize("body", ['{"command":"arbitrary"}', "[]", ""])
def test_refresh_accepts_only_the_fixed_empty_operation(site_root, body):
    with running(site_root) as (server, url):
        assert (
            requests.post(url + "/api/refresh", headers=headers(server), data=body).status_code
            == 400
        )
        assert server.app.job is None


def test_single_refresh_and_success_are_visible_to_reader(site_root):
    entered = Event()
    release = Event()
    calls = []

    def runner(app):
        calls.append(1)
        app.set_phase("Checking isolated test sources")
        entered.set()
        release.wait(2)
        return {"fixture": "isolated HTTP test"}

    with running(site_root, runner) as (server, url):
        first = requests.post(url + "/api/refresh", headers=headers(server), data="{}")
        assert first.status_code == 202 and entered.wait(1)
        second = requests.post(url + "/api/refresh", headers=headers(server), data="{}")
        assert second.status_code == 409 and first.json()["id"] == second.json()["id"]
        assert (
            requests.get(url + "/api/status").json()["job"]["phase"]
            == "Checking isolated test sources"
        )
        release.set()
        wait_finished(server.app)
        assert server.app.job["status"] == "completed" and len(calls) == 1
        assert (site_root / "reports/service_jobs" / server.app.job["id"] / "status.json").is_file()


def test_failure_restores_all_active_pointers_without_deleting_downloads(site_root):
    before = {
        name: (site_root / name).read_bytes() if (site_root / name).exists() else None
        for name in PUBLISH_PATHS
    }

    def runner(app):
        for name in PUBLISH_PATHS:
            path = app.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"SYNTHETIC INCOMPLETE UPDATE")
        (app.root / "reports/retained_download.bin").write_bytes(b"SYNTHETIC DOWNLOAD")
        raise ValueError("SYNTHETIC SECRET EXCEPTION TEXT")

    with running(site_root, runner) as (server, url):
        assert (
            requests.post(url + "/api/refresh", headers=headers(server), data="{}").status_code
            == 202
        )
        wait_finished(server.app)
        assert server.app.job["status"] == "failed"
        assert "SECRET" not in json.dumps(server.app.job)
        assert (site_root / "reports/retained_download.bin").exists()
        for name, raw in before.items():
            path = site_root / name
            assert (path.read_bytes() if path.exists() else None) == raw
        assert (
            "SYNTHETIC INCOMPLETE UPDATE" not in requests.get(url + "/presentation/index.html").text
        )


def test_saved_pdf_supports_partial_reads_and_head(site_root):
    raw = (site_root / "data/research/test.pdf").read_bytes()
    with running(site_root) as (_server, url):
        response = requests.get(url + "/data/research/test.pdf", headers={"Range": "bytes=0-4"})
        assert response.status_code == 206 and response.content == b"%PDF-"
        assert response.headers["Content-Range"] == f"bytes 0-4/{len(raw)}"
        response = requests.get(url + "/data/research/test.pdf", headers={"Range": "bytes=-7"})
        assert response.content == raw[-7:]
        assert (
            requests.get(
                url + "/data/research/test.pdf", headers={"Range": f"bytes={len(raw) + 1}-"}
            ).status_code
            == 416
        )
        response = requests.head(url + "/data/research/test.pdf")
        assert response.status_code == 200 and not response.content
        assert response.headers["Content-Length"] == str(len(raw))


def test_markdown_preserves_code_and_removes_active_markup():
    raw = markdown_html(
        "# Safe\n\n<script>bad()</script> [unsafe](javascript:bad)\n\n```sh\n<x>\n```", "Safe"
    ).decode()
    assert "<script>" not in raw and 'href="javascript:' not in raw
    assert "&lt;script&gt;" in raw and "<pre><code>&lt;x&gt;</code></pre>" in raw


def test_reader_opens_cited_page_and_renders_preserved_pdf(site_root):
    params = {"file": "data/research/test.pdf", "page": "2"}
    with running(site_root) as (_server, url):
        response = requests.get(url + "/reader", params=params)
        assert response.status_code == 200 and "PDF page 2 of 2" in response.text
        assert "SYNTHETIC SECOND PAGE" in response.text
        assert "Previous page" in response.text and "Last page" in response.text
        assert (
            hashlib.sha256((site_root / "data/research/test.pdf").read_bytes()).hexdigest()
            in response.text
        )
        image = requests.get(url + "/api/source-page", params=params)
        assert image.status_code == 200 and image.headers["Content-Type"] == "image/png"
        pixmap = fitz.Pixmap(image.content)
        assert 500 < pixmap.width <= 1600 and 500 < pixmap.height <= 2200
        first = requests.get(url + "/reader", params={"file": params["file"], "page": "1"})
        assert "&lt;script&gt;" in first.text and "<script>" not in first.text


@pytest.mark.parametrize(
    "query",
    [
        "file=../../.env&page=1",
        "file=docs/test.md&page=1",
        "file=data/research/test.pdf&page=0",
        "file=data/research/test.pdf&page=3",
        "file=data/research/test.pdf&page=1&page=2",
        "file=data/research/test.pdf&page=abc",
        "file=data/research/test.pdf&extra=1",
    ],
)
def test_reader_rejects_unlisted_files_and_invalid_pages(site_root, query):
    with running(site_root) as (_server, url):
        response = requests.get(url + "/reader?" + query)
        assert response.status_code == 404 and "SYNTHETIC_SECRET" not in response.text


def test_reader_refuses_changed_source_bytes(site_root):
    with running(site_root) as (_server, url):
        with (site_root / "data/research/test.pdf").open("ab") as stream:
            stream.write(b"\nSYNTHETIC MODIFICATION")
        for endpoint in ("reader", "api/source-page"):
            response = requests.get(
                url + "/" + endpoint, params={"file": "data/research/test.pdf", "page": "1"}
            )
            assert response.status_code == 404 and "MODIFICATION" not in response.text


def test_real_download_contains_executable_scripts_and_typed_data_without_source_pdfs():
    root = Path(__file__).resolve().parents[1]
    with running(root) as (_server, url):
        response = requests.get(url + "/api/analysis.zip")
        assert response.status_code == 200
        with ZipFile(BytesIO(response.content)) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert "Anchored_Returns_Analysis/data/outcomes.dta" in names
            assert "Anchored_Returns_Analysis/data/outcomes.csv" in names
            assert "Anchored_Returns_Analysis/figures.R" in names
            assert "Anchored_Returns_Analysis/figures.do" in names
            assert not any("baseline" in n or "raw_orders" in n or "ratings" in n for n in names)
