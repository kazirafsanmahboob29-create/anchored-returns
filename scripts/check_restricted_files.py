"""Reject prohibited paths and file types in the Git index."""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    withdrawn = set(json.loads((ROOT / "docs/eei_withdrawal.json").read_text())["paths"])
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    blocked = sorted(
        name for name in set(tracked)
        if name in withdrawn or Path(name).suffix.lower() in {".dta", ".zip", ".xlsx"}
    )
    for name in blocked:
        print(name)
    if not blocked:
        print("No restricted files are tracked.")
    return int(bool(blocked))


if __name__ == "__main__":
    raise SystemExit(main())
