"""Compare the paper's Treasury estimates without changing its original models."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.filing_study import STAGE_FEATURES
from src.panel_models import fit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/treasury-comparison"
INPUTS = (
    "reports/filing-study/panel.csv",
    "reports/factor-study/estimation.csv",
)
OLD_FEATURES = [
    "old_treasury90",
    "old_curve90",
    "old_inflation",
    "old_stress",
    "duration",
    "distribution",
    "old_prior",
]


def samples(root):
    filing = pd.read_csv(root / INPUTS[0])
    earlier = pd.read_csv(root / INPUTS[1])
    if not filing.id.is_unique or not earlier.id.is_unique:
        raise ValueError("Record IDs must identify one row")
    full = filing[filing.prior_eligible].copy()
    recent = full[full.year.between(2010, 2024)].copy()
    common = recent.merge(earlier, on="id", suffixes=("", "_old"), validate="one_to_one")
    for key in ("state", "authorized_date", "requested_date"):
        if not (common[key] == common[key + "_old"]).all():
            raise ValueError("Matched case identities differ")
    if not np.allclose(common.award, common.roe, rtol=0, atol=1e-12):
        raise ValueError("Matched awards differ")
    rename = {
        key: "old_" + key for key in ("treasury90", "curve90", "inflation", "stress", "prior")
    }
    common = common.rename(columns=rename)
    original = earlier.rename(columns={**rename, "roe": "award"})
    return {"full": full, "recent": recent, "common": common, "original": original}


def specifications():
    stage = STAGE_FEATURES + ["known_prior"]
    return [
        ("filing_full", "full", stage, "filing_treasury90"),
        ("filing_recent", "recent", stage, "filing_treasury90"),
        ("filing_common", "common", stage, "filing_treasury90"),
        (
            "omit_treasury_update",
            "common",
            [x for x in stage if x != "update_treasury90"],
            "filing_treasury90",
        ),
        (
            "decision_conditions",
            "common",
            [
                "decision_treasury90",
                "decision_inflation",
                "decision_unemployment",
                "duration",
                "distribution",
                "known_prior",
            ],
            "decision_treasury90",
        ),
        (
            "original_controls_filing_prior",
            "common",
            [x for x in OLD_FEATURES if x != "old_prior"] + ["known_prior"],
            "old_treasury90",
        ),
        ("original_controls_decision_prior", "common", OLD_FEATURES, "old_treasury90"),
        ("original_full", "original", OLD_FEATURES, "old_treasury90"),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    frames = samples(ROOT)
    records, models = [], []
    for name, selection, features, treasury in specifications():
        frame = frames[selection]
        result = fit(frame, "award", features, "state_year")
        for row in result.coefficients(features):
            records.append({"model": name, **row})
        models.append(
            {
                "model": name,
                "sample": selection,
                "n": len(frame),
                "start": int(frame.year.min()),
                "end": int(frame.year.max()),
                "features": ";".join(features),
                "treasury_term": treasury,
                "states": result.states,
                "quarters": result.quarters,
                "effects": "state_year",
                "df": result.df,
            }
        )
    coefficients = pd.DataFrame(records)
    # The first and final rows reproduce the existing point estimates and SEs.
    for model, rel, reference_model, reference_term in [
        (
            "filing_full",
            "reports/filing-study/coefficients.csv",
            "known_prior_award",
            "filing_treasury90",
        ),
        ("original_full", "reports/factor-study/coefficients.csv", "state_year", "treasury90"),
    ]:
        reference = pd.read_csv(ROOT / rel)
        reference = reference[
            (reference.model == reference_model) & (reference.term == reference_term)
        ]
        if "covariance" in reference:
            reference = reference[reference.covariance == "two_way"]
        term = "filing_treasury90" if model == "filing_full" else "old_treasury90"
        actual = coefficients[(coefficients.model == model) & (coefficients.term == term)]
        if len(reference) != 1 or len(actual) != 1:
            raise ValueError("The comparison reference is ambiguous")
        if not np.allclose(
            actual[["estimate", "se"]], reference[["estimate", "se"]], rtol=0, atol=1e-8
        ):
            raise ValueError("An existing point estimate or standard error changed")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    coefficients.to_csv(output / "coefficients.csv", index=False)
    pd.DataFrame(models).to_csv(output / "models.csv", index=False)
    estimates = []
    for model in models:
        row = next(
            r
            for r in records
            if r["model"] == model["model"] and r["term"] == model["treasury_term"]
        )
        estimates.append(
            {
                "model": model["model"],
                "n": model["n"],
                **{
                    key + "_bp": 100 * row[key] if row[key] is not None else None
                    for key in ("estimate", "low", "high")
                },
            }
        )
    pd.DataFrame(estimates).to_csv(output / "treasury.csv", index=False)
    manifest = {
        "date": "2026-10-30",
        "status": "post hoc model comparison",
        "input_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS},
        "plan_sha256": hashlib.sha256(
            (ROOT / "docs/treasury_comparison_plan_2026-10-30.md").read_bytes()
        ).hexdigest(),
        "sample_counts": {key: len(frame) for key, frame in frames.items()},
        "inference": "State and decision-quarter two-way clustering; t intervals with min(cluster counts)-1 df",
        "interpretation": "Sequential conditional comparisons; not a unique or causal decomposition",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(pd.DataFrame(estimates).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
