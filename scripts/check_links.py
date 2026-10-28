"""Check Markdown paths and anchors; optionally report public HTTP link status."""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[\"'][^\n]*?[\"'])?\s*\)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)


def prose(text):
    # Preserve line numbers while excluding executable examples from link checks.
    text = re.sub(
        r"^(`{3,}|~{3,}).*?^\1[^\n]*$",
        lambda m: "\n" * m[0].count("\n"),
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return re.sub(r"`[^`\n]+`", "", text)


def anchors(text):
    ids, seen = set(), Counter()
    for match in re.finditer(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", prose(text), re.MULTILINE):
        label = re.sub(r"<[^>]*>", "", html.unescape(match[1])).lower()
        label = re.sub(r"[^\w\- ]", "", label).replace(" ", "-")
        count = seen[label]
        ids.add(f"{label}-{count}" if count else label)
        seen[label] += 1
    ids.update(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', text))
    return ids


def audit(root=ROOT, *, include_export=False):
    root = Path(root).resolve()
    errors, remote = [], {}
    links = documents = 0
    for source in sorted(root.rglob("*.md")):
        if any(
            part in {".git", ".venv", "node_modules"} for part in source.relative_to(root).parts
        ):
            continue
        # The frozen service export has its own file manifest and runtime routes.
        # Its copied documentation is not the maintained repository documentation.
        if not include_export and source.is_relative_to(root / "web/research-release"):
            continue
        documents += 1
        text = source.read_text(encoding="utf-8")
        body = prose(text)
        destinations = [
            m[1].strip("<>") for pattern in (INLINE_LINK, REFERENCE) for m in pattern.finditer(body)
        ]
        destinations += re.findall(r'<(?:a|img)\b[^>]*?(?:href|src)=["\']([^"\']+)', body)
        # Include plain public URLs as well as Markdown links. Local server examples
        # require a running process and cannot be treated as dead public pages.
        destinations += re.findall(r"https?://[^\s<>\)\]\"`]+", body)
        for destination in sorted(set(destinations)):
            destination = html.unescape(destination).rstrip(".,;*")
            url = urlsplit(destination)
            if url.scheme in {"http", "https"}:
                if url.hostname not in {"localhost", "127.0.0.1", "::1"}:
                    if any(marker in destination for marker in ("SERIES_ID", "{", "}")):
                        continue
                    clean = urlunsplit((url.scheme, url.netloc, url.path, url.query, ""))
                    remote.setdefault(clean, set()).add(str(source.relative_to(root)))
                continue
            if url.scheme:
                continue
            links += 1
            target = (
                (
                    root / unquote(url.path).lstrip("/")
                    if url.path.startswith("/")
                    else source.parent / unquote(url.path)
                )
                if url.path
                else source
            )
            problem = None
            if not target.exists():
                problem = "missing path"
            elif (
                url.fragment
                and target.suffix.lower() == ".md"
                and unquote(url.fragment) not in anchors(target.read_text(encoding="utf-8"))
            ):
                problem = "missing heading or anchor"
            if problem:
                errors.append(
                    {
                        "source": str(source.relative_to(root)),
                        "target": destination,
                        "problem": problem,
                    }
                )
    return {
        "documents": documents,
        "internal_links": links,
        "errors": errors,
        "external_urls": {url: sorted(sources) for url, sources in sorted(remote.items())},
    }


def check_http(item):
    url, sources = item
    result = subprocess.run(
        [
            "curl",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            "25",
            "--output",
            os.devnull,
            "--write-out",
            "%{http_code}\n%{url_effective}",
            url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    fields = result.stdout.splitlines()
    status = int(fields[0]) if fields and fields[0].isdigit() else 0
    if result.returncode:
        state = "request_failed"
    elif status in {404, 410}:
        state = "missing"
    elif 200 <= status < 300:
        state = "reachable"
    elif status in {401, 403, 429}:
        state = "access_restricted"
    elif status == 405:
        state = "method_not_supported"
    else:
        state = "review_required"
    return {
        "url": url,
        "http_status": status,
        "state": state,
        "final_url": fields[1] if len(fields) > 1 else None,
        "error": result.stderr.strip() or None,
        "sources": sources,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external", action="store_true", help="Also request public URLs using curl"
    )
    parser.add_argument(
        "--include-export",
        action="store_true",
        help="Also inspect copied documentation in the frozen service export",
    )
    parser.add_argument("--output", type=Path, help="Save the complete JSON report")
    args = parser.parse_args()
    report = audit(include_export=args.include_export)
    if args.external:
        if not shutil.which("curl"):
            parser.error("curl is required for --external; internal checks do not need it")
        with ThreadPoolExecutor(max_workers=6) as executor:
            report["http"] = list(executor.map(check_http, report["external_urls"].items()))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {key: report[key] for key in ("documents", "internal_links", "errors")}
    summary["public_urls"] = len(report["external_urls"])
    if "http" in report:
        summary["http_states"] = dict(Counter(row["state"] for row in report["http"]))
    print(json.dumps(summary, indent=2))
    # Publisher access controls are an audit result, not a broken-link assertion.
    raise SystemExit(
        bool(report["errors"] or any(row["state"] == "missing" for row in report.get("http", [])))
    )


if __name__ == "__main__":
    main()
