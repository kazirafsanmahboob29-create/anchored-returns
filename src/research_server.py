"""Loopback research app with preserved snapshots and fixed refresh operations."""

from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import mimetypes
from pathlib import Path
import re
import secrets
from threading import Lock, Thread
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from zipfile import ZipFile, ZIP_DEFLATED

from .research_ledger import fingerprint, local_path, require
from .research_overview import build_overview


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_RECORDS = (
    "data/research/empirical_ledger_v0.1.3.json",
    "data/research/assistant_verified_case_facts.json",
    "data/research/source_catalog.json",
    "data/research/sample_screening.json",
    "data/external/rra_historical_benchmarks.json",
    "data/external/rra_context_sources.json",
)
PUBLISH_PATHS = (
    "data/external/treasury/latest.json",
    "data/research/treasury_order_joins.json",
    "data/external/treasury_official/latest.json",
    "reports/analysis/latest.json",
    "presentation/index.html",
    "reports/presentation_build.json",
)


def inline(text):
    text = escape(text)

    def link(match):
        title, url = match.groups()
        if urlsplit(url).scheme not in ("", "http", "https"):
            return title
        return f'<a href="{url}" rel="noopener noreferrer">{title}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)


def markdown_html(text, title):
    """Render the project's headings, prose, lists, tables and fenced examples."""
    lines = text.splitlines()
    blocks, paragraph = [], []

    def flush():
        if paragraph:
            blocks.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append("<pre><code>" + escape("\n".join(code)) + "</code></pre>")
        elif re.match(r"^#{1,6} ", line):
            flush()
            level = len(line) - len(line.lstrip("#"))
            blocks.append(f"<h{level}>" + inline(line[level + 1 :]) + f"</h{level}>")
        elif (
            line.startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\|[\s:|\-]+\|$", lines[i + 1])
        ):
            flush()
            cells = lambda row: row.strip().strip("|").split("|")
            headers = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            blocks.append(
                '<div class="doc-table"><table><thead><tr>'
                + "".join("<th>" + inline(c.strip()) + "</th>" for c in headers)
                + "</tr></thead><tbody>"
                + "".join(
                    "<tr>" + "".join("<td>" + inline(c.strip()) + "</td>" for c in row) + "</tr>"
                    for row in rows
                )
                + "</tbody></table></div>"
            )
            continue
        elif re.match(r"^(?:[-*] |\d+\. )", line):
            flush()
            ordered = bool(re.match(r"^\d+\. ", line))
            items = []
            pattern = r"^\d+\. " if ordered else r"^[-*] "
            while i < len(lines) and re.match(pattern, lines[i]):
                items.append(re.sub(pattern, "", lines[i]))
                i += 1
            tag = "ol" if ordered else "ul"
            blocks.append(
                f"<{tag}>"
                + "".join("<li>" + inline(item) + "</li>" for item in items)
                + f"</{tag}>"
            )
            continue
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
        i += 1
    flush()
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{escape(title)} · Anchored Returns</title><link rel="stylesheet" href="/presentation/styles.css"></head>'
        '<body class="document-page"><header class="document-header"><a href="/presentation/index.html">'
        "← Anchored Returns</a><span>Kazi Rafsan Mahboob · Research documents</span></header>"
        '<main class="document-content">' + "".join(blocks) + "</main></body></html>"
    ).encode()


class ResearchApp:
    def __init__(self, root=ROOT, *, prepare=True, refresh_runner=None):
        self.root = Path(root).resolve()
        self.lock = Lock()
        self.token = secrets.token_urlsafe(32)
        self.job = None
        self.worker = None
        self.refresh_runner = refresh_runner or self.refresh_sources
        if prepare:
            build_overview(self.root)
        self.load_published()

    def load_published(self):
        raw = (self.root / "presentation/index.html").read_bytes()
        audit = json.loads((self.root / "reports/presentation_build.json").read_text())
        require(
            fingerprint(self.root / "presentation/index.html") == audit["output_sha256"],
            "Published site changed; rebuild it before serving",
        )
        payload = json.loads(
            re.search(
                rb'<script id="research-data" type="application/json">(.*?)</script>', raw, re.S
            ).group(1)
        )
        files = {
            "README.md",
            "presentation/index.html",
            "presentation/project.html",
            "presentation/styles.css",
            "presentation/favicon.svg",
            *PUBLIC_RECORDS,
        }
        files.update(
            str(p.relative_to(self.root))
            for folder in ("docs", "analysis")
            for p in (self.root / folder).glob("*.md")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "analysis").glob("*")
            if p.suffix in (".R", ".do")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "reports").iterdir()
            if p.is_file() and p.suffix in (".md", ".json", ".txt")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "reports").glob("independent_coding_kit_*.zip")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "data/research/releases").glob("*/proposed_sample.json")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "presentation/workspace").glob("*.mjs")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "presentation/national").glob("*")
            if p.suffix in (".mjs", ".css")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "reports/national-study").glob("*")
            if p.suffix in (".json", ".csv", ".dta", ".png", ".zip")
        )
        files.add("presentation/models.html")
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "presentation/factors").glob("*")
            if p.suffix in (".mjs", ".css")
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "reports/factor-study").glob("*")
            if p.suffix in (".json", ".csv", ".dta", ".png", ".zip")
        )
        factor_allowlist = (
            self.root / "data/external/factor_research_2026-10-26/publication_allowlist.json"
        )
        if factor_allowlist.exists():
            factor_files = json.loads(factor_allowlist.read_text())
            files.update(r["path"] for r in factor_files["allowed_data_files"])
            files.update(factor_files["allowed_documentation_files"])
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "data/external/eei").glob("*")
            if p.is_file()
        )
        files.update(
            str(p.relative_to(self.root))
            for p in (self.root / "data/external/bls_cpi/2026-10-26").glob("*.json")
        )
        files.update(s["pdf_path"] for s in payload["sources"])
        files.update(s["pdf_path"] for s in payload["benchmarks"]["sources"])
        files.update(
            r["reconstruction"]["path"]
            for r in payload["benchmarks"].get("records", [])
            if r.get("estimation_method") == "case_level_reconstruction"
        )
        if any(
            r.get("estimation_method") == "case_level_reconstruction"
            for r in payload["benchmarks"].get("records", [])
        ):
            files.add("data/external/rra/rra_2019_decisions.csv")
        files.update(s["pdf_path"] for s in payload.get("audit", {}).get("context_sources", []))
        packet = payload["reliability"].get("packet_id")
        if packet:
            files.update(
                f"data/research/reliability/{packet}/rater/{name}"
                for name in ("index.html", "packet.json", "ratings_blank.json")
            )
            files.add("project_docs/Anchored_Returns_Codebook_v0.1.2.docx")
        analysis = payload.get("analysis")
        manifest = None
        if analysis and analysis["status"] == "current":
            manifest = json.loads(local_path(self.root, analysis["manifest_path"]).read_text())
            parent = Path(analysis["manifest_path"]).parent
            files.add(analysis["manifest_path"])
            files.update(str(parent / path) for path in manifest["file_sha256"])
        self.html, self.payload, self.files, self.analysis_manifest = raw, payload, files, manifest

    def status(self):
        with self.lock:
            return dict(
                service="anchored-returns",
                version="1.0",
                csrf_token=self.token,
                evidence_date=self.payload["date"],
                counts=self.payload["stats"],
                treasury=self.payload["treasury"]
                and dict(
                    latest=self.payload["treasury"]["latest"],
                    retrieved_at_utc=self.payload["treasury"]["retrieved_at_utc"],
                ),
                analysis_available=self.analysis_manifest is not None,
                job=None if self.job is None else dict(self.job),
            )

    def analysis_zip(self):
        with self.lock:
            manifest = self.analysis_manifest
            require(manifest is not None, "A current analysis release is not available")
            parent = local_path(self.root, self.payload["analysis"]["manifest_path"]).parent
            paths = [parent / name for name in manifest["file_sha256"]]
            require(
                sum(p.stat().st_size for p in paths) < 50_000_000,
                "Analysis bundle exceeds the download limit",
            )
            buffer = BytesIO()
            with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
                for path in paths:
                    require(
                        fingerprint(path) == manifest["file_sha256"][str(path.relative_to(parent))],
                        "Analysis artifact changed",
                    )
                    archive.write(
                        path, "Anchored_Returns_Analysis/" + str(path.relative_to(parent))
                    )
                archive.write(parent / "manifest.json", "Anchored_Returns_Analysis/manifest.json")
                archive.write(
                    self.root / "analysis/README.md", "Anchored_Returns_Analysis/README.md"
                )
                for name in ("figures.R", "figures.do"):
                    require(
                        fingerprint(self.root / "analysis" / name)
                        == manifest["script_sha256"][name],
                        "Analysis script changed",
                    )
                    archive.write(
                        self.root / "analysis" / name, "Anchored_Returns_Analysis/" + name
                    )
            return buffer.getvalue()

    def source_page(self, query, *, image=False):
        """Read one page from an allowed, fingerprint-checked saved PDF."""
        import fitz

        fields = parse_qs(query, keep_blank_values=True)
        require(
            set(fields) <= {"file", "page"}
            and "file" in fields
            and all(len(values) == 1 for values in fields.values()),
            "Invalid reader query",
        )
        name = fields["file"][0]
        page = fields.get("page", ["1"])[0]
        require(re.fullmatch(r"[1-9]\d{0,5}", page) is not None, "Invalid page number")
        with self.lock:
            require(name in self.files and Path(name).suffix == ".pdf", "PDF not available")
            sources = (
                self.payload["sources"]
                + self.payload["benchmarks"]["sources"]
                + self.payload.get("audit", {}).get("context_sources", [])
            )
            record = next((s for s in sources if s["pdf_path"] == name), {})
            expected = record.get("pdf_sha256")
            if not expected and self.analysis_manifest:
                parent = str(Path(self.payload["analysis"]["manifest_path"]).parent) + "/"
                if name.startswith(parent):
                    expected = self.analysis_manifest["file_sha256"].get(name[len(parent) :])
        path = local_path(self.root, name)
        digest = fingerprint(path)
        require(expected is not None and digest == expected, "PDF fingerprint changed")
        with fitz.open(path) as document:
            number = int(page)
            require(number <= len(document), "Page is outside the document")
            selected = document[number - 1]
            if image:
                scale = min(1.7, 1600 / selected.rect.width, 2200 / selected.rect.height)
                return selected.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes(
                    "png"
                )
            count, text = len(document), selected.get_text()
        title = record.get("title") or record.get("publisher") or path.stem.replace("_", " ")

        def url(n, endpoint="reader"):
            return "/" + endpoint + "?" + urlencode({"file": name, "page": n})

        previous = (
            f'<a class="button secondary" href="{escape(url(number - 1))}">Previous page</a>'
            if number > 1
            else '<span class="small">First page</span>'
        )
        following = (
            f'<a class="button secondary" href="{escape(url(number + 1))}">Next page</a>'
            if number < count
            else '<span class="small">Last page</span>'
        )
        source = record.get("landing_url") or record.get("source_url")
        official = (
            f'<a href="{escape(source)}" target="_blank" rel="noopener noreferrer">Official record / publisher ↗</a>'
            if source and urlsplit(source).scheme in ("http", "https")
            else ""
        )
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Page {number} · {escape(title)}</title><link rel="stylesheet" href="/presentation/styles.css"></head>'
            '<body class="document-page"><header class="document-header"><a href="/presentation/index.html#evidence">← Anchored Returns</a>'
            '<span>Kazi Rafsan Mahboob · Source reader</span></header><main class="source-reader">'
            f'<div class="eyebrow">Saved evidence · PDF page {number} of {count}</div><h1>{escape(title)}</h1>'
            '<p class="small">Page numbers follow the saved PDF, including cover sheets. The image displays the original document page.</p>'
            f'<nav class="reader-controls" aria-label="PDF page navigation">{previous}'
            f'<form action="/reader" method="get"><input type="hidden" name="file" value="{escape(name)}">'
            f'<label for="source-page">Page</label><input id="source-page" name="page" type="number" min="1" max="{count}" value="{number}" required>'
            f'<span>of {count}</span><button class="button secondary" type="submit">Go</button></form>{following}</nav>'
            f'<div class="reader-sheet"><img src="{escape(url(number, "api/source-page"))}" alt="Original PDF page {number} of {count}: {escape(title)}"></div>'
            f'<details class="reader-text"><summary>Native text from this page</summary><pre>{escape(text or "No native text is available on this page.")}</pre></details>'
            f'<div class="source-links"><a href="/{escape(name)}" download>Download saved PDF ↓</a>{official}</div>'
            f'<p class="small reader-fingerprint">PDF SHA-256 <code>{digest}</code></p></main></body></html>'
        ).encode()

    def set_phase(self, phase):
        with self.lock:
            self.job["phase"] = phase
            self.save_job()

    def save_job(self):
        path = self.root / "reports/service_jobs" / self.job["id"] / "status.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.job, indent=2) + "\n")

    def start_refresh(self):
        with self.lock:
            if self.job and self.job["status"] == "running":
                return dict(self.job), False
            self.job = dict(
                id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
                status="running",
                phase="Starting source refresh",
                started_at_utc=datetime.now(timezone.utc).isoformat(),
            )
            self.save_job()
            result = dict(self.job)
        self.worker = Thread(target=self.run_refresh, daemon=False)
        self.worker.start()
        return result, True

    def run_refresh(self):
        before = {
            name: (self.root / name).read_bytes() if (self.root / name).exists() else None
            for name in PUBLISH_PATHS
        }
        try:
            result = self.refresh_runner(self)
            with self.lock:
                self.load_published()
                self.job.update(
                    status="completed", phase="Sources checked and site updated", result=result
                )
        except Exception as error:
            # Preserve newly downloaded bundles for diagnosis, but restore the
            # last complete set of active pointers and the published page.
            for name, raw in before.items():
                path = self.root / name
                if raw is not None:
                    path.write_bytes(raw)
                elif path.exists():
                    path.unlink()
            with self.lock:
                self.job.update(
                    status="failed",
                    phase="Refresh did not complete",
                    error_type=type(error).__name__,
                    error="The refresh failed. The previous complete site and active snapshots were retained. See the project source checks before retrying.",
                )
        finally:
            with self.lock:
                self.job["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
                self.save_job()

    @staticmethod
    def refresh_sources(app):
        from .treasury import refresh, join_orders
        from .treasury_crosscheck import refresh_crosscheck
        from .research_analysis import analyze

        app.set_phase("Downloading Federal Reserve observations")
        fred = refresh(app.root)
        join_orders(app.root, write=True)
        app.set_phase("Comparing official Treasury observations")
        comparison = refresh_crosscheck(app.root)
        app.set_phase("Checking evidence and generating R and Python figures")
        analysis = analyze(app.root)
        build_overview(app.root)
        return dict(
            fred_latest=fred["latest_nonmissing"],
            fred_rows=fred["rows"],
            same_date_comparisons=comparison["overlapping_dates"],
            disagreements=len(comparison["disagreements"]),
            analysis_path=str(Path(analysis["output_path"]).relative_to(app.root)),
        )


class ResearchHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def reply(self, code, raw, content_type="application/json", *, head=False, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(raw)

    def json_reply(self, code, result):
        self.reply(code, (json.dumps(result) + "\n").encode())

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_GET(self, *, head=False):
        if not self.valid_host():
            return self.reply(403, b"Host not permitted", "text/plain", head=head)
        app = self.server.app
        path = unquote(urlsplit(self.path).path).lstrip("/")
        if path == "api/status":
            return self.reply(200, json.dumps(app.status()).encode(), head=head)
        if path in ("reader", "api/source-page"):
            try:
                is_image = path == "api/source-page"
                raw = app.source_page(urlsplit(self.path).query, image=is_image)
                return self.reply(
                    200, raw, "image/png" if is_image else "text/html; charset=utf-8", head=head
                )
            except (ValueError, OSError, RuntimeError):
                return self.reply(
                    404,
                    b"Source page unavailable. Check the document and PDF page number.",
                    "text/plain",
                    head=head,
                )
        if path == "api/analysis.zip":
            try:
                raw = app.analysis_zip()
            except (ValueError, OSError):
                return self.reply(409, b"Current analysis unavailable", "text/plain", head=head)
            return self.reply(
                200,
                raw,
                "application/zip",
                head=head,
                extra={
                    "Content-Disposition": 'attachment; filename="anchored-returns-analysis.zip"'
                },
            )
        if path in ("", "presentation/index.html"):
            with app.lock:
                raw = app.html
            return self.reply(200, raw, "text/html; charset=utf-8", head=head)
        with app.lock:
            allowed = path in app.files
        if not allowed:
            return self.reply(404, b"Record not available", "text/plain", head=head)
        try:
            target = local_path(app.root, path)
            if not target.is_file():
                raise ValueError("Missing file")
            if target.suffix == ".md":
                raw = markdown_html(target.read_text(), target.stem.replace("_", " "))
                return self.reply(200, raw, "text/html; charset=utf-8", head=head)
            size = target.stat().st_size
            start, end, code = 0, size - 1, 200
            if "Range" in self.headers:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers["Range"])
                if not match or not any(match.groups()):
                    return self.reply(
                        416, b"", head=head, extra={"Content-Range": f"bytes */{size}"}
                    )
                a, b = match.groups()
                start = int(a) if a else max(0, size - int(b))
                end = min(int(b), size - 1) if a and b else size - 1
                if start > end or start >= size:
                    return self.reply(
                        416, b"", head=head, extra={"Content-Range": f"bytes */{size}"}
                    )
                code = 206
            self.send_response(code)
            self.send_header(
                "Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream"
            )
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if not head:
                with target.open("rb") as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = stream.read(min(remaining, 1_048_576))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
        except (ValueError, OSError):
            self.reply(404, b"Record not available", "text/plain", head=head)

    def do_POST(self):
        port = self.server.server_port
        allowed = (f"http://127.0.0.1:{port}", f"http://localhost:{port}")
        if (
            not self.valid_host()
            or self.headers.get("Origin") not in allowed
            or self.headers.get("X-Research-Token") != self.server.app.token
        ):
            return self.json_reply(403, {"error": "Local site approval required"})
        if urlsplit(self.path).path != "/api/refresh":
            return self.json_reply(404, {"error": "Unknown operation"})
        if (
            self.headers.get("Content-Type") != "application/json"
            or self.headers.get("Content-Length") != "2"
            or self.rfile.read(2) != b"{}"
        ):
            return self.json_reply(400, {"error": "This operation accepts an empty JSON object"})
        job, started = self.server.app.start_refresh()
        self.json_reply(202 if started else 409, job)


def make_server(root=ROOT, *, port=8765, prepare=True, refresh_runner=None):
    app = ResearchApp(root, prepare=prepare, refresh_runner=refresh_runner)
    server = ThreadingHTTPServer(("127.0.0.1", port), ResearchHandler)
    server.app = app
    return server


def serve(root=ROOT, *, port=8765, prepare=True):
    # A cloned repository can serve the checked release before PDFs are restored.
    # Rebuilding evidence still uses the normal source and fingerprint checks.
    server = make_server(root, port=port, prepare=prepare)
    print(
        f"Anchored Returns: http://127.0.0.1:{server.server_port}/presentation/index.html",
        flush=True,
    )
    print("Keep this terminal running. Press Ctrl+C to stop the local service.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if server.app.worker and server.app.worker.is_alive():
            print("Completing the active refresh before stopping.", flush=True)
            server.app.worker.join()
