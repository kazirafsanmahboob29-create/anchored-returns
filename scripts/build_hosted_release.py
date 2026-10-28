"""Export a checked, portable research release without local service state."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from src.research_server import ResearchApp, markdown_html


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def export(root, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    app = ResearchApp(root, prepare=False)
    previous_manifest = destination / "release-manifest.json"
    previous_files = (
        set(json.loads(previous_manifest.read_text())["files"])
        if previous_manifest.exists()
        else set()
    )
    public = destination / "public"
    public.mkdir(parents=True, exist_ok=True)
    records = app.payload

    # Derived JSON has portable paths. Original input bytes remain unchanged.
    def portable(value):
        if isinstance(value, dict):
            return {k: portable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [portable(v) for v in value]
        if isinstance(value, str):
            return value.replace(str(root) + "/", "")
        return value

    records = portable(records)
    sources = (
        records["sources"] + records["benchmarks"]["sources"] + records["audit"]["context_sources"]
    )
    source_by_path = {s["pdf_path"]: s for s in sources}
    selected = {name for name in app.files if not name.startswith("reports/")}
    parent = str(Path(records["analysis"]["manifest_path"]).parent)
    selected.update(name for name in app.files if name.startswith(parent + "/"))
    selected.update(name for name in app.files if name.startswith("reports/national-study/"))
    selected.update(name for name in app.files if name.startswith("reports/factor-study/"))
    selected.add("reports/independent_coding_kit_2026-10-03.zip")
    selected.add("reports/sample_and_benchmarks_2026-10-04.md")
    selected.add("reports/research_release_2026-10-20.md")
    selected.update(records["inputs"])
    for pointer_name in (
        "data/external/treasury/latest.json",
        "data/external/treasury_official/latest.json",
    ):
        pointer = json.loads((root / pointer_name).read_text())
        selected.add(pointer_name)
        selected.add(pointer["metadata_path"])
        meta = json.loads((root / pointer["metadata_path"]).read_text())
        selected.update(meta[k] for k in ("raw_path", "observations_path") if k in meta)
        selected.update(s["raw_path"] for s in meta.get("sources", []))
    selected.discard("docs/research_access_requests.md")
    # Additional records linked directly by the validated page are included.
    for name in re.findall(r'href="\.\./([^"#?]+)', app.html.decode()):
        if name in app.files:
            selected.add(name)
    selected.add("presentation/favicon.svg")
    selected.add("analysis/figures.R")
    selected.add("analysis/figures.do")
    release = {}
    for name in sorted(selected):
        source = root / name
        if not source.is_file() or name == "presentation/index.html":
            continue
        target = public / name
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        if name in source_by_path:
            expected = source_by_path[name]["pdf_sha256"]
            if digest(raw) != expected:
                raise ValueError("Source PDF fingerprint changed: " + name)
        if source.suffix == ".md":
            raw = markdown_html(portable(raw.decode()), source.stem.replace("_", " "))
        elif source.suffix == ".json":
            transformed = portable(json.loads(raw))
            if transformed != json.loads(raw):
                raw = (json.dumps(transformed, indent=2) + "\n").encode()
        target.write_bytes(raw)
        release[name] = {"sha256": digest(raw), "bytes": len(raw)}
    (public / "downloads").mkdir(exist_ok=True)
    raw = app.analysis_zip()
    (public / "downloads/anchored-returns-analysis.zip").write_bytes(raw)
    release["downloads/anchored-returns-analysis.zip"] = {"sha256": digest(raw), "bytes": len(raw)}
    with ZipFile(public / "downloads/anchored-returns-tools.zip", "w", ZIP_DEFLATED) as archive:
        for directory, pattern in [
            ("src", "*.py"),
            ("tests", "*.py"),
            ("analysis", "*"),
            ("scripts", "*.py"),
        ]:
            for path in sorted((root / directory).glob(pattern)):
                if path.is_file():
                    archive.write(path, str(path.relative_to(root)))
        for path in sorted((root / "src").glob("*.json")):
            archive.write(path, str(path.relative_to(root)))
        for path in sorted((root / "presentation/workspace").glob("*.mjs")):
            archive.write(path, str(path.relative_to(root)))
        for path in sorted((root / "presentation/national").glob("*")):
            if path.suffix in (".mjs", ".css"):
                archive.write(path, str(path.relative_to(root)))
        for path in sorted((root / "presentation/factors").glob("*")):
            if path.suffix in (".mjs", ".css"):
                archive.write(path, str(path.relative_to(root)))
        for name in [
            "research",
            "pyproject.toml",
            "requirements-lock.txt",
            "README.md",
            ".gitignore",
        ]:
            archive.write(root / name, name)
        for name in sorted(selected):
            if (
                name.endswith((".json", ".csv", ".md", ".docx", ".xlsx"))
                and not name.startswith(("reports/analysis/", "analysis/"))
                and name != "README.md"
            ):
                archive.writestr(
                    name,
                    portable((root / name).read_text()).encode()
                    if name.endswith((".json", ".csv", ".md"))
                    else (root / name).read_bytes(),
                )
        archive.writestr(
            "HOSTED_RELEASE.md",
            "This source package contains the research tools and preserved records. Original PDFs are available from the hosted source library and the official URLs in the source catalog. R and Stata analysis tables are supplied in the separate research bundle.\n",
        )
    tool_raw = (public / "downloads/anchored-returns-tools.zip").read_bytes()
    release["downloads/anchored-returns-tools.zip"] = {
        "sha256": digest(tool_raw),
        "bytes": len(tool_raw),
    }
    sources.extend(
        {
            "pdf_path": str(Path(parent) / name),
            "title": Path(name).stem.replace("_", " "),
            "pdf_sha256": sha,
        }
        for name, sha in app.analysis_manifest["file_sha256"].items()
        if name.endswith(".pdf")
    )
    for name in previous_files - set(release):
        stale = (public / name).resolve()
        if stale.is_relative_to(public.resolve()) and stale.is_file():
            stale.unlink()
    (destination / "release-data.json").write_text(json.dumps(records, indent=2) + "\n")
    from src.treasury_crosscheck import load_crosscheck

    official = load_crosscheck(root)
    (destination / "market-seed.json").write_text(
        json.dumps(
            {
                "latest": official["latest_nonmissing"],
                "equal": official["equal"],
                "overlapping_dates": official["overlapping_dates"],
                "missing": official["missing_value_dates"],
                "disagreements": official["disagreements"],
            },
            indent=2,
        )
        + "\n"
    )
    (destination / "source-index.json").write_text(
        json.dumps({s["pdf_path"]: s for s in sources}, indent=2) + "\n"
    )
    (destination / "release-manifest.json").write_text(
        json.dumps(
            {
                "evidence_date": records["date"],
                "research_status": "provisional_measurement_pilot",
                "files": release,
            },
            indent=2,
        )
        + "\n"
    )
    shutil.copy(root / "presentation/template.html", destination / "template.html")
    shutil.copy(root / "presentation/app.js", destination / "research-app.js")
    shutil.copy(root / "presentation/styles.css", destination / "research-styles.css")
    print(
        json.dumps(
            {
                "files": len(release),
                "pdfs": len(sources),
                "bytes": sum(r["bytes"] for r in release.values()),
                "destination": str(destination),
            }
        )
    )


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("destination", type=Path)
    selected = args.parse_args()
    export(Path(__file__).resolve().parents[1], selected.destination)
