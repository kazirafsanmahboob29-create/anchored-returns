"""Portable publishing checks using the real compiled research release."""

import base64, gzip, hashlib, json, re, subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WP = ROOT / "wordpress"


def load_payload():
    page = (WP / "workbench.html").read_text()
    raw = gzip.decompress(base64.b64decode(re.search(r'data-payload="([^"]+)"', page)[1]))
    assert hashlib.sha256(raw).hexdigest() == re.search(r'data-sha256="([^"]+)"', page)[1]
    return json.loads(raw)


def test_build_reproduces_a_verified_self_hosted_bundle():
    subprocess.run(
        ["python3", str(ROOT / "scripts/build_wordpress.py")], check=True, capture_output=True
    )
    payload = load_payload()
    for path, asset in payload["files"].items():
        assert base64.b64decode(asset["base64"]) == (ROOT / path).read_bytes()
    assert len(payload["facts"]) == 68
    assert len(payload["regional"]["records"]) == 27
    assert payload["packet"]["unit_count"] == 67
    assert all(
        set(unit) == {"unit_id", "text", "source_url", "pdf_sha256", "pages", "context"}
        for unit in payload["packet"]["units"]
    )
    assert all(
        value is None for row in payload["blank"]["ratings"] for value in row["codes"].values()
    )


def test_public_fragments_have_no_platform_dependency_or_unresolved_asset():
    payload = load_payload()
    for name in ["home.html", "project.html", "coursework.html", "template.html", "footer.html"]:
        text = (WP / name).read_text()
        assert "{{assets}}" not in text and "{{site}}" not in text
        if name != "footer.html":
            assert "—" not in text
        for path in [] if name == "footer.html" else re.findall(r'ar-file:([^"<>]+)', text):
            assert path in payload["files"], path
        for url in re.findall(r'href="([^"]+)"', text):
            query = parse_qs(urlsplit(url.replace("&amp;", "&")).query)
            if "download" in query:
                assert query["download"][0] in payload["files"]
    # Data belong only to the application page, not every portfolio page.
    assert len((WP / "footer.html").read_bytes()) < 150_000
    assert "data-payload=" not in (WP / "footer.html").read_text()
    assert "data-payload=" in (WP / "workbench.html").read_text()


def test_cohort_and_calculation_inputs_are_the_published_records():
    payload = load_payload()
    study = json.loads(
        base64.b64decode(payload["files"]["reports/factor-study/study.json"]["base64"])
    )
    assert study["coverage"]["complete"] == 533
    assert study["coverage"]["entries"] == 777
    assert all(row.get("pdf_sha256") for row in payload["facts"])
    assert len({row["fact_id"] for row in payload["facts"]}) == 68
    assert all(value.startswith("https://") for value in payload["media"].values())
