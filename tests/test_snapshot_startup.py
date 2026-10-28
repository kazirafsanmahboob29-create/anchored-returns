"""A source-only checkout should open the preserved research tools."""

from pathlib import Path
from threading import Thread
import urllib.request

from src.research import main
from src.research_server import make_server


ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_flag_skips_evidence_rebuild(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.research_server.serve",
        lambda root, **options: calls.append((root, options)),
    )
    assert main(["serve", "--snapshot", "--port", "8768"]) == 0
    assert calls == [(ROOT, {"port": 8768, "prepare": False})]


def test_packaged_release_serves_models_without_original_pdfs():
    server = make_server(ROOT, port=0, prepare=False)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        for path in (
            "/presentation/index.html",
            "/presentation/models.html",
            "/presentation/factors/compute.mjs",
            "/reports/factor-study/study.json",
        ):
            with urllib.request.urlopen(base + path, timeout=10) as response:
                assert response.status == 200
                assert response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
