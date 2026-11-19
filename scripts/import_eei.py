"""Install a user-obtained EEI workbook after checking the recorded version."""

import argparse
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import requests

ROOT = Path(__file__).resolve().parents[1]


def install(source, root=ROOT):
    root = Path(root)
    metadata = json.loads((root / "data/external/eei/source.json").read_text())
    content = Path(source).read_bytes()
    if sha256(content).hexdigest() != metadata["sha256"]:
        raise ValueError(
            "This is not the recorded 2025 Q3 workbook; the existing source was not changed"
        )
    destination = root / metadata["path"]
    if destination.exists() and destination.read_bytes() != content:
        raise ValueError("A different local workbook already exists; preserve it separately")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", help="Workbook obtained from EEI")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Retrieve the recorded public URL for a use permitted by EEI's terms",
    )
    args = parser.parse_args()
    if (args.source is None) == (not args.download):
        parser.error("Supply a local workbook or --download")
    try:
        if args.download:
            metadata = json.loads((ROOT / "data/external/eei/source.json").read_text())
            response = requests.get(metadata["url"], timeout=60)
            response.raise_for_status()
            with TemporaryDirectory(prefix="eei-download-") as folder:
                source = Path(folder) / "download.xlsx"
                source.write_bytes(response.content)
                print(install(source))
        else:
            print(install(args.source))
    except (ValueError, OSError, requests.RequestException) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
