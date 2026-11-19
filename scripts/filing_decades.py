"""Refit the unchanged known-prior award specification by decision-year decade."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.filing_study import (
    ROOT, FilingHistory, enrich, fit_stage, make_panel, read_workbook,
    specifications, validate_quarters,
)

PERIODS = ((1985, 1994), (1995, 2004), (2005, 2014), (2015, 2024))
TREASURY = "filing_treasury90"
WORKBOOK = Path("data/external/eei/eei_rate_review_2025_q3.xlsx")


def load_panel(root=ROOT):
    root = Path(root)
    if not (root / WORKBOOK).is_file():
        raise FileNotFoundError(f"Required local EEI workbook is missing: {root / WORKBOOK}")
    raw, controls = read_workbook(root / WORKBOOK)
    validate_quarters(raw, controls)
    return make_panel(enrich(raw, []), FilingHistory(root))


def specification():
    return next(spec for spec in specifications() if spec[0] == "known_prior")


def verify_full_sample(frame, root=ROOT):
    """Check the unchanged full-sample fit against existing aggregate exports."""
    _, flag, features, effects, weight = specification()
    selected = frame[frame[flag] & frame.year.between(1985, 2024)]
    model = fit_stage(selected, "award", features, effects, weight)
    folder = Path(root) / "reports/filing-study"
    coverage = pd.read_csv(folder / "models.csv").set_index("model")
    if len(selected) != coverage.loc["known_prior_award", "n"]:
        raise ValueError("Full-sample observation count changed")
    saved = pd.read_csv(folder / "coefficients.csv")
    saved = saved[saved.model == "known_prior_award"]
    for covariance in ("two_way", "state", "quarter"):
        expected = saved[saved.covariance == covariance].set_index("term")
        actual = pd.DataFrame(model.coefficients(features, covariance)).set_index("term")
        if set(expected.index) != set(actual.index):
            raise ValueError("Full-sample coefficient terms changed")
        columns = ["estimate", "se", "low", "high"]
        if not np.allclose(actual.loc[expected.index, columns].to_numpy(dtype=float),
                           expected[columns].to_numpy(dtype=float),
                           rtol=0, atol=1e-8, equal_nan=True):
            raise ValueError(f"Full-sample coefficients changed: {covariance}")


def analyze(frame):
    _, flag, features, effects, weight = specification()
    records = []
    for start, end in PERIODS:
        selected = frame[frame[flag] & frame.year.between(start, end)]
        residual = selected[TREASURY] - selected.groupby("year")[TREASURY].transform("mean")
        row = {
            "period": f"{start}-{end}", "n": len(selected),
            "treasury_estimate_pp": None, "treasury_low_pp": None, "treasury_high_pp": None,
            "within_year_sd_pp": float(residual.std(ddof=1)) if len(selected) > 1 else None,
            "status": "unavailable", "reason": "",
        }
        try:
            model = fit_stage(selected, "award", features, effects, weight)
            coefficient = model.coefficients([TREASURY], "two_way")[0]
            row["treasury_estimate_pp"] = coefficient["estimate"]
            if all(coefficient[key] is not None and np.isfinite(coefficient[key])
                   for key in ("estimate", "low", "high")):
                row.update(treasury_low_pp=coefficient["low"],
                           treasury_high_pp=coefficient["high"], status="estimated")
            else:
                row.update(status="inference_unavailable", reason=coefficient["variance_status"])
        except ValueError as error:
            row["reason"] = str(error)
        records.append(row)
    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/filing-decades.csv")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Refusing to overwrite: {args.output}")
    try:
        frame = load_panel()
        verify_full_sample(frame)
        result = analyze(frame)
    except (FileNotFoundError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    with args.output.open("x") as stream:
        result.to_csv(stream, index=False)
    print(result.to_string(index=False))
    print("Full-sample aggregate estimates reproduced within absolute tolerance 1e-8.")


if __name__ == "__main__":
    main()
