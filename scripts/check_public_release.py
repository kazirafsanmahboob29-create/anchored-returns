"""Check the distributable source tree and run tests that need no EEI rows."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, is_zipfile

ROOT = Path(__file__).resolve().parents[1]


def distribution_errors(root=ROOT, paths=None):
    root = Path(root)
    withdrawn = set(json.loads((root / "docs/eei_withdrawal.json").read_text())["paths"])
    if paths is None:
        if (root / ".git").exists():
            paths = (
                subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
            )
        else:
            paths = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
    errors = []
    for name in paths:
        if not name:
            continue
        if name in withdrawn or name.startswith("web/research-release/"):
            errors.append(name)
        path = root / name
        if path.is_file() and path.suffix == ".zip" and is_zipfile(path):
            with ZipFile(path) as archive:
                for member in archive.namelist():
                    if member in withdrawn or member.endswith("eei_rate_review_2025_q3.xlsx"):
                        errors.append(name + ": " + member)
    return sorted(set(errors))


def main():
    errors = distribution_errors()
    if errors:
        raise SystemExit(
            "Source files must remain outside the public package:\n" + "\n".join(errors)
        )
    tests = [
        "test_panel_models.py",
        "test_peer_study.py",
        "test_economic_history.py",
        "test_number_finder.py",
        "test_segment.py",
        "test_reliability.py",
        "test_source_access.py",
        "test_rate_case_comparisons.py",
    ]
    filing_fixtures = [
        "test_known_prior_excludes_decisions_during_the_proceeding_and_same_day",
        "test_stale_and_invalid_filing_dates_are_not_filled",
        "test_decision_day_weighted_covariance_matches_statsmodels_wls",
        "test_stage_identity_holds_for_every_coefficient",
    ]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *["tests/" + t for t in tests],
            *["tests/test_filing_study.py::" + t for t in filing_fixtures],
        ],
        cwd=ROOT,
        check=True,
    )
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required for browser calculation tests")
    subprocess.run(
        [
            node,
            "--test",
            "tests/filing.test.mjs",
            "tests/filing-loading.test.mjs",
            "web/tests/market.test.mjs",
            "web/tests/factors.test.mjs",
            "tests/wordpress/live.test.mjs",
        ],
        cwd=ROOT,
        check=True,
    )
    print(
        "Public source and fixture checks passed. Source-dependent replication is a separate local check."
    )


if __name__ == "__main__":
    main()
