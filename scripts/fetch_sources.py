"""Restore fingerprint-checked source files from an archive or recorded URLs."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


def restore(root, *, archive=None, download=False):
    root = Path(root).resolve()
    manifest = json.loads((root / "data/source_files.json").read_text())
    bundle = ZipFile(archive) if archive else None
    missing, restored = [], []
    try:
        for record in manifest["files"]:
            relative = record["path"]
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Source path escapes the repository")
            valid = lambda raw: hashlib.sha256(raw).hexdigest() == record["sha256"]
            if target.is_file() and valid(target.read_bytes()):
                continue
            raw = None
            if bundle and relative in bundle.namelist():
                raw = bundle.read(relative)
            elif download and record.get("url"):
                import requests

                try:
                    response = requests.get(record["url"], timeout=(10, 60))
                    response.raise_for_status()
                    raw = response.content
                except requests.RequestException:
                    missing.append(relative)
                    continue
            if raw is None or not valid(raw):
                missing.append(relative)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            restored.append(relative)
        web = root / "web/research-release"
        if web.is_dir():
            source_index = json.loads((web / "source-index.json").read_text())
            for relative, record in source_index.items():
                source = root / relative
                if (
                    source.is_file()
                    and hashlib.sha256(source.read_bytes()).hexdigest() == record["pdf_sha256"]
                ):
                    target = web / "public" / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
    finally:
        if bundle:
            bundle.close()
    return dict(
        status="passed" if not missing else "sources_missing",
        files=len(manifest["files"]),
        restored=len(restored),
        missing=missing,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = restore(
        Path(__file__).resolve().parents[1], archive=args.archive, download=args.download
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
