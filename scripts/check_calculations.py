"""Run calculation and application tests that do not need original order PDFs."""

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYTHON_TESTS = (
    "test_research_insights.py",
    "test_research_sample.py",
    "test_eei_benchmarks.py",
    "test_national_study.py",
    "test_factor_study.py",
    "test_prediction_audit.py",
    "test_research_checks.py",
    "test_wordpress.py",
    "test_research_reliability.py",
    "test_research_server.py",
    "test_number_finder.py",
    "test_segment.py",
    "test_reliability.py",
    "test_snapshot_startup.py",
)
JS_DIRECTORIES = ("workspace", "national", "factors", "wordpress")


def main():
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Node.js 24 is required for the browser calculation tests.")

    # Use this interpreter so a virtual environment and CI run the same checks.
    commands = [
        [sys.executable, "-m", "pytest", "-q", *[f"tests/{p}" for p in PYTHON_TESTS]],
        [
            node,
            "--test",
            *[
                str(p.relative_to(ROOT))
                for name in JS_DIRECTORIES
                for p in sorted((ROOT / "tests" / name).glob("*.test.mjs"))
            ],
        ],
        [node, "--test", "web/tests/market.test.mjs", "web/tests/factors.test.mjs"],
    ]
    for command in commands:
        print("Running:", " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
    print("Calculation and application checks passed.")


if __name__ == "__main__":
    main()
