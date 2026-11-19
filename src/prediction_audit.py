"""Evaluate the preserved later-case predictions without fitting new models."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_cluster_2groups

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("reports/factor-study")
OUTPUT = Path("reports/prediction-audit")
MODELS = ("training_mean", "previous_award", "market_case", "with_prior")
SCHEMA = "anchored-returns-prediction-audit/1"
CRITICAL = 1.959963984540054


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def joined_predictions(predictions, estimation):
    """Require a one-to-one match so dropped or duplicated cases cannot improve MAE."""
    if predictions.id.duplicated().any() or estimation.id.duplicated().any():
        raise ValueError("Prediction and estimation IDs must be unique")
    metadata = ["id", "state", "entity", "quarter", "case_type", "authorized_date", "roe", "prior"]
    frame = predictions.merge(estimation[metadata], on="id", how="left", validate="one_to_one")
    if frame[metadata].isna().any().any():
        raise ValueError("Every prediction needs complete matching source metadata")
    values = frame[["actual", *MODELS, "roe", "prior"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Predictions and observed returns must be finite")
    if not np.allclose(frame.actual, frame.roe, rtol=0, atol=1e-10):
        raise ValueError("Prediction outcomes differ from the estimation table")
    if not np.allclose(frame.previous_award, frame.prior, rtol=0, atol=1e-10):
        raise ValueError("Previous-award predictions differ from the source lags")
    if not frame.date.equals(frame.authorized_date):
        raise ValueError("Prediction dates differ from authorization dates")
    dates = pd.to_datetime(frame.date, format="%Y-%m-%d", errors="raise")
    if not (dates.dt.year.between(2020, 2024)).all():
        raise ValueError("This audit is restricted to the saved 2020-2024 evaluation")
    if not dates.dt.to_period("Q").astype(str).equals(frame.quarter):
        raise ValueError("Authorization quarters differ from the source dates")
    frame["year"] = dates.dt.year
    for model in MODELS:
        # Inputs are percentage points. Errors and loss differences are basis points.
        frame[f"error_{model}"] = (frame[model] - frame.actual) * 100
        frame[f"loss_{model}"] = frame[f"error_{model}"].abs()
    frame["gain_bp"] = frame.loss_previous_award - frame.loss_with_prior
    return frame


def load_inputs(root=ROOT):
    root = Path(root)
    folder = root / SOURCE
    manifest = json.loads((folder / "artifact-manifest.json").read_text())
    for name in ("study.json", "holdout.csv", "estimation.csv"):
        if digest(folder / name) != manifest["files"][name]:
            raise ValueError(f"Preserved factor-study input changed: {name}")
    study = json.loads((folder / "study.json").read_text())
    for name, fingerprint in study["input_sha256"].items():
        if digest(root / name) != fingerprint:
            raise ValueError(f"Factor-study source changed: {name}")
    frame = joined_predictions(
        pd.read_csv(folder / "holdout.csv"), pd.read_csv(folder / "estimation.csv")
    )
    expected = study["holdout"]["predictions"]
    if frame.id.tolist() != [row["id"] for row in expected]:
        raise ValueError("Saved predictions and study IDs differ")
    for name in ("actual", *MODELS):
        if not np.allclose(frame[name], [row[name] for row in expected], rtol=0, atol=1e-10):
            raise ValueError(f"Saved predictions and study values differ: {name}")
    return frame


def metrics(frame):
    return [
        {
            "model": model,
            "n": len(frame),
            "mae_bp": float(frame[f"loss_{model}"].mean()),
            "rmse_bp": float(np.sqrt(np.mean(frame[f"error_{model}"] ** 2))),
            "bias_bp": float(frame[f"error_{model}"].mean()),
            "median_absolute_error_bp": float(frame[f"loss_{model}"].median()),
        }
        for model in MODELS
    ]


def comparison(frame, reference="previous_award", candidate="with_prior"):
    """A positive paired loss difference means the candidate has smaller error."""
    gain = frame[f"loss_{reference}"] - frame[f"loss_{candidate}"]
    states, quarters = pd.factorize(frame.state)[0], pd.factorize(frame.quarter)[0]
    if len(set(states)) < 2 or len(set(quarters)) < 2:
        raise ValueError("At least two states and quarters are required")
    fit = sm.OLS(gain.to_numpy(), np.ones((len(frame), 1))).fit()
    # Keep state dependence and common quarterly conditions in the uncertainty estimate.
    covariance, _, _ = cov_cluster_2groups(fit, states, quarters, use_correction=True)
    variance = float(covariance[0, 0])
    se = float(np.sqrt(variance)) if variance > 0 else None
    estimate = float(gain.mean())
    return {
        "reference": reference,
        "candidate": candidate,
        "n": len(frame),
        "states": len(set(states)),
        "quarters": len(set(quarters)),
        "improvement_bp": estimate,
        "se_bp": se,
        "low_bp": estimate - CRITICAL * se if se is not None else None,
        "high_bp": estimate + CRITICAL * se if se is not None else None,
        "variance_status": "positive" if se is not None else "nonpositive_unavailable",
        "candidate_wins": int((gain > 1e-10).sum()),
        "reference_wins": int((gain < -1e-10).sum()),
        "ties": int((gain.abs() <= 1e-10).sum()),
    }


def tables(frame):
    annual, case_types = [], []
    for key, output in (("year", annual), ("case_type", case_types)):
        for group, part in frame.groupby(key, sort=True):
            output.extend({"group": str(group), **record} for record in metrics(part))
    omitted = [
        {
            "omitted_state": state,
            "n": len(frame) - int((frame.state == state).sum()),
            "improvement_bp": float(frame.loc[frame.state != state, "gain_bp"].mean()),
        }
        for state in sorted(frame.state.unique())
    ]
    equal_entity = float(frame.groupby("entity").gain_bp.mean().mean())
    return annual, case_types, omitted, equal_entity


def numerical_checks(summary):
    rows = []
    for record in summary["metrics"]:
        for field in ("mae_bp", "rmse_bp"):
            rows.append({"check": f"{record['model']}.{field}", "value": record[field]})
    for record in summary["comparisons"]:
        for field in ("improvement_bp", "se_bp"):
            rows.append({"check": f"{record['reference']}.{field}", "value": record[field]})
    return rows


def figure(summary, annual, output):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})
    years = sorted({row["group"] for row in annual})
    for model, offset, color, label in (
        ("previous_award", -0.18, "#a6aaa8", "Previous award"),
        ("with_prior", 0.18, "#263d35", "Model with prior award"),
    ):
        values = [
            next(row["mae_bp"] for row in annual if row["group"] == year and row["model"] == model)
            for year in years
        ]
        axes[0].bar(np.arange(len(years)) + offset, values, width=0.34, color=color, label=label)
    axes[0].set(
        xticks=np.arange(len(years)),
        xticklabels=years,
        ylabel="Mean absolute error (bp)",
        title="Prediction errors vary across years",
    )
    axes[0].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.18))
    row = summary["comparisons"][0]
    if row["se_bp"] is not None:
        axes[1].errorbar(
            row["improvement_bp"],
            0,
            xerr=CRITICAL * row["se_bp"],
            fmt="o",
            color="#263d35",
            capsize=5,
        )
    axes[1].axvline(0, color="#a6aaa8", linestyle="--", linewidth=1)
    axes[1].set(
        yticks=[],
        xlabel="MAE improvement over previous award (bp)",
        title="The average gain remains uncertain",
        ylim=(-1, 1),
    )
    axes[1].text(
        0.03,
        0.12,
        "Positive values favor the model.\n95% interval, clustered by state and quarter.",
        transform=axes[1].transAxes,
        fontsize=8,
    )
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Later-case evaluation, 2020-2024", fontweight="bold", y=1.01)
    fig.text(
        0.02,
        -0.04,
        "188 preserved predictions. Models fitted on 2010-2019; revised historical inputs. Conditional, retrospective evaluation.",
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(output / "prediction-evaluation.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_manifest(root, output, r_validation):
    paths = [
        SOURCE / "artifact-manifest.json",
        SOURCE / "study.json",
        SOURCE / "holdout.csv",
        SOURCE / "estimation.csv",
        Path("src/prediction_audit.py"),
        Path("analysis/prediction_audit.R"),
        Path("docs/prediction_evaluation.md"),
    ]
    manifest = {
        "schema": SCHEMA,
        "r_validation": r_validation,
        "inputs": {str(path): digest(root / path) for path in paths},
        "outputs": {
            path.name: digest(path)
            for path in sorted(output.iterdir())
            if path.is_file() and path.name != "manifest.json"
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")


def build(root=ROOT, output=None):
    root = Path(root)
    output = Path(output) if output is not None else root / OUTPUT
    if output.exists() and any(output.iterdir()):
        marker = output / "manifest.json"
        if not marker.exists() or json.loads(marker.read_text()).get("schema") != SCHEMA:
            raise ValueError("Use an empty output folder or an existing prediction-audit folder")
    frame = load_inputs(root)
    annual, case_types, omitted, equal_entity = tables(frame)
    summary = {
        "schema": SCHEMA,
        "analysis_date": "2026-10-28",
        "evaluation": "Post hoc audit of fixed predictions; no refitting",
        "train_years": [2010, 2019],
        "test_years": [2020, 2024],
        "observations": len(frame),
        "entities": int(frame.entity.nunique()),
        "metrics": metrics(frame),
        "comparisons": [comparison(frame), comparison(frame, "market_case")],
        "equal_entity_improvement_bp": equal_entity,
        "leave_one_state_out_range_bp": [
            min(row["improvement_bp"] for row in omitted),
            max(row["improvement_bp"] for row in omitted),
        ],
        "uncertainty": "Finite-sample-corrected state plus quarter minus intersection covariance; 95% normal Wald interval; fitted models held fixed",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    frame.to_csv(output / "paired_predictions.csv", index=False)
    for name, rows in (
        ("metrics", summary["metrics"]),
        ("comparisons", summary["comparisons"]),
        ("annual", annual),
        ("case_types", case_types),
        ("leave_one_state_out", omitted),
        ("python_checks", numerical_checks(summary)),
    ):
        pd.DataFrame(rows).to_csv(output / f"{name}.csv", index=False)
    # A rebuild invalidates a prior R check, even when its old files remain present.
    for name in ("r-crosscheck.csv", "r-prediction-errors.png"):
        (output / name).unlink(missing_ok=True)
    figure(summary, annual, output)
    write_manifest(root, output, "not_run")
    return summary


def verify(root=ROOT, output=None, *, verify_r=False):
    root = Path(root)
    output = Path(output) if output is not None else root / OUTPUT
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Unrecognized prediction audit")
    for name, expected in manifest["inputs"].items():
        if digest(root / name) != expected:
            raise ValueError(f"Prediction audit input changed: {name}")
    for name, expected in manifest["outputs"].items():
        if digest(output / name) != expected:
            raise ValueError(f"Prediction audit output changed: {name}")
    frame = load_inputs(root)
    saved = json.loads((output / "summary.json").read_text())
    checks = pd.DataFrame(
        numerical_checks(
            {
                "metrics": metrics(frame),
                "comparisons": [comparison(frame), comparison(frame, "market_case")],
            }
        )
    )
    expected = pd.DataFrame(numerical_checks(saved))
    if checks.check.tolist() != expected.check.tolist() or not np.allclose(
        checks.value, expected.value, rtol=0, atol=1e-8
    ):
        raise ValueError("Saved evaluation does not match recomputed predictions")
    if verify_r or manifest["r_validation"] != "not_run":
        r = pd.read_csv(output / "r-crosscheck.csv")
        if r.check.tolist() != checks.check.tolist() or not np.allclose(
            r.value, checks.value, rtol=0, atol=1e-8
        ):
            raise ValueError("R calculations differ from Python")
        if verify_r:
            write_manifest(root, output, "12 checks matched within 1e-8")
    return {
        "status": "passed",
        "observations": len(frame),
        "numerical_checks": len(checks),
        "r_validation": json.loads((output / "manifest.json").read_text())["r_validation"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--verify-r", action="store_true")
    args = parser.parse_args()
    result = (
        verify(output=args.output, verify_r=args.verify_r)
        if args.check or args.verify_r
        else build(output=args.output)
    )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
