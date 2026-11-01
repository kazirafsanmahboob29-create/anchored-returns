"""Rebuild local EEI-derived inputs before the current filing and peer studies."""

import argparse
import subprocess

from src.eei_benchmarks import read_workbook
from src.filing_study import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-r", action="store_true", help="Also run native R comparisons")
    args = parser.parse_args()
    source = ROOT / "data/external/eei/eei_rate_review_2025_q3.xlsx"
    if not source.is_file():
        parser.exit(
            1,
            "Obtain the workbook from EEI and run python -m scripts.import_eei /path/to/workbook.xlsx first.\n",
        )
    read_workbook(source)
    from src.expanded_study import build as expanded
    from src.factor_study import build as factors
    from src.filing_study import build as filing
    from src.filing_study import verify
    from src.national_study import build as national
    from src.peer_study import build as peers

    for label, builder in (
        ("National input tables", national),
        ("Earlier estimation inputs", factors),
        ("Historical inputs", expanded),
        ("Filing study", filing),
        ("Peer comparison", peers),
    ):
        print(label, flush=True)
        builder(ROOT)
    if args.with_r:
        for label in ("filing", "peer"):
            subprocess.run(
                [
                    "Rscript",
                    str(ROOT / "analysis" / (label + ".R")),
                    str(ROOT / "reports" / (label + "-study")),
                ],
                cwd=ROOT,
                check=True,
            )
        verify(ROOT, verify_r=True)
    print(
        "Local tables are ready. Serve the folder with python -m http.server 8765 --bind 127.0.0.1"
    )


if __name__ == "__main__":
    main()
