"""A longer case panel, local conditions and changes between actual decisions."""

import argparse
import hashlib
import json
from bisect import bisect_left
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .economic_history import SOURCE, EconomicHistory
from .eei_benchmarks import SOURCE_ID, SOURCE_SHEET, read_workbook, validate_quarters
from .national_study import enrich
from .panel_diagnostics import REGIONAL_RESTRICTIONS, state_influence
from .panel_models import design, expanding_blocks, fit, ols

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("reports/expanded-study")
PLAN = Path("docs/expanded_analysis_plan_2026-10-28.md")
MARKET = ["treasury90", "curve90", "inflation", "stress"]
CASE = ["duration", "distribution"]
LOCAL = MARKET + CASE + ["prior", "unemployment"]
LONG = [x for x in LOCAL if x != "stress"]
CHANGES = ["delta_" + x for x in MARKET + ["unemployment"]] + ["gap_years", "distribution"]
PREDICTORS = MARKET + CASE + ["unemployment"]
SCHEMA = "anchored-returns-expanded-study/1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_panel(records, history):
    dates_by_entity = defaultdict(lambda: defaultdict(list))
    for row in records:
        if row["award_bp"] is not None:
            dates_by_entity[(row["state"], row["utility"])][row["authorized_date"]].append(row)
    output = []
    for row in records:
        if not 1985 <= row["year"] <= 2024:
            continue
        written = row["authorized_date"]
        earlier = dates_by_entity[(row["state"], row["utility"])]
        days = sorted(earlier)
        index = bisect_left(days, written) - 1
        prior_day = days[index] if index >= 0 else None
        gap = (
            (date.fromisoformat(written) - date.fromisoformat(prior_day)).days
            if prior_day
            else None
        )
        previous = earlier[prior_day] if prior_day and gap <= 3652 else []
        duration = (
            (date.fromisoformat(written) - date.fromisoformat(row["requested_date"])).days
            if row["requested_date"]
            else None
        )
        output.append(
            {
                **row,
                "source_id": SOURCE_ID,
                "source_sheet": SOURCE_SHEET,
                "entity": row["state"] + " / " + row["utility"],
                "quarter": written[:4] + "Q" + str((int(written[5:7]) - 1) // 3 + 1),
                "region": history.states[row["state"]]["region"],
                "roe": row["award_bp"] / 100 if row["award_bp"] is not None else None,
                "prior": np.mean([p["award_bp"] for p in previous]) / 100 if previous else None,
                "prior_date": prior_day if previous else None,
                "prior_ids": ";".join(p["id"] for p in previous),
                "prior_rows": len(previous),
                "prior_gap_days": gap if previous else None,
                "gap_years": gap / 365.25 if previous else None,
                "duration": duration / 365.25
                if duration is not None and 0 <= duration <= 3652
                else None,
                "distribution": int(row["case_type"] == "Distribution"),
            }
        )
    frame = pd.DataFrame(output).drop(columns=["treasury_bp", "treasury_date", "treasury_gap_days"])
    joined = history.join(frame.authorized_date, frame.state)
    frame = pd.concat([frame, joined], axis=1)
    prior_mask = frame.prior_date.notna()
    previous = history.join(frame.loc[prior_mask, "prior_date"], frame.loc[prior_mask, "state"])
    previous.index = frame.index[prior_mask]
    for key in previous:
        frame["previous_" + key] = previous[key]
    for key in MARKET + ["unemployment"]:
        frame["delta_" + key] = frame[key] - frame["previous_" + key]
    frame["delta_roe"] = frame.roe - frame.prior
    frame["rate_rise"] = frame.delta_treasury90.clip(lower=0)
    frame["rate_fall"] = frame.delta_treasury90.clip(upper=0)
    for region in ("Midwest", "South", "West"):
        frame["rate_" + region.lower()] = frame.delta_treasury90 * (frame.region == region)
    frame["main_eligible"] = (frame.year >= 1995) & frame[["roe", *LOCAL]].notna().all(axis=1)
    frame["change_eligible"] = (frame.year >= 1995) & frame[["delta_roe", *CHANGES]].notna().all(
        axis=1
    )
    frame["long_eligible"] = frame[["roe", *LONG]].notna().all(axis=1)
    return frame


def specifications():
    asymmetric = [x for x in CHANGES if x != "delta_treasury90"] + ["rate_rise", "rate_fall"]
    region = CHANGES + ["rate_midwest", "rate_south", "rate_west"]
    return [
        ("market_case", "main", "roe", MARKET + CASE, "none"),
        ("with_prior", "main", "roe", MARKET + CASE + ["prior"], "none"),
        ("local", "main", "roe", LOCAL, "none"),
        ("local_state_year", "main", "roe", LOCAL, "state_year"),
        ("local_entity_year", "main", "roe", LOCAL, "entity_year"),
        ("bridge_prior", "bridge", "roe", MARKET + CASE + ["prior"], "none"),
        ("bridge_state_year", "bridge", "roe", MARKET + CASE + ["prior"], "state_year"),
        ("main_no_stress", "main", "roe", LONG, "none"),
        ("main_no_stress_state_year", "main", "roe", LONG, "state_year"),
        ("long_no_stress", "long", "roe", LONG, "none"),
        ("long_state_year", "long", "roe", LONG, "state_year"),
        ("change", "change", "delta_roe", CHANGES, "none"),
        ("change_state_year", "change", "delta_roe", CHANGES, "state_year"),
        ("asymmetric", "change", "delta_roe", asymmetric, "state_year"),
        ("regional_slopes", "change", "delta_roe", region, "state_year"),
    ]


def estimate(frame):
    samples = {
        "main": frame[frame.main_eligible],
        "change": frame[frame.change_eligible],
        "long": frame[frame.long_eligible],
        "bridge": frame[frame.main_eligible & (frame.year >= 2010)],
    }
    coefficients, models, specs, fitted, sensitivity = [], [], [], {}, []
    for name, sample, target, features, effects in specifications():
        selected = samples[sample]
        result = fit(selected, target, features, effects)
        fitted[name] = result
        coefficients.extend({"model": name, **r} for r in result.coefficients(features))
        for covariance in ("state", "quarter"):
            sensitivity.extend(
                {"model": name, "covariance": covariance, **r}
                for r in result.coefficients(features, covariance)
            )
        models.append(
            {
                "model": name,
                "sample": sample,
                "target": target,
                "effects": effects,
                "n": result.n,
                "states": result.states,
                "quarters": result.quarters,
                "entities": selected.entity.nunique(),
                "parameters": result.parameters,
                "cluster_df": result.df,
                "r_squared": result.r_squared,
                "condition_number": result.condition_number,
                "covariance_min_eigenvalue": float(np.linalg.eigvalsh(result.covariance).min()),
            }
        )
        specs.append(
            {
                "model": name,
                "sample": sample,
                "target": target,
                "features": ";".join(features),
                "effects": effects,
            }
        )
    test_specs = [
        ("equal_rise_fall_slopes", "asymmetric", [{"rate_rise": 1, "rate_fall": -1}]),
        ("equal_regional_rate_slopes", "regional_slopes", REGIONAL_RESTRICTIONS),
    ]
    tests, joint_rows = {}, []
    for name, model, restrictions in test_specs:
        for covariance in ("two_way", "state", "quarter"):
            result = fitted[model].joint_test(restrictions, covariance)
            joint_rows.append({"test": name, "covariance": covariance, **result})
            if covariance == "two_way":
                tests[name] = result
    slopes = []
    change = samples["change"]
    for region in ("Northeast", "Midwest", "South", "West"):
        weights = {"delta_treasury90": 1}
        if region != "Northeast":
            weights["rate_" + region.lower()] = 1
        slopes.append(
            {
                "region": region,
                "region_n": int((change.region == region).sum()),
                **fitted["regional_slopes"].combination(weights),
            }
        )
    influence = state_influence(
        samples["main"],
        samples["change"],
        LOCAL,
        next(s[3] for s in specifications() if s[0] == "regional_slopes"),
    )
    return coefficients, models, specs, tests, sensitivity, joint_rows, slopes, influence


def loss_comparison(frame, reference):
    gain = frame["loss_" + reference] - frame.loss_with_prior
    result = ols(
        pd.DataFrame({"const": np.ones(len(frame))}), gain.to_numpy(), frame.state, frame.quarter
    )
    value = result.coefficients(["const"])[0]
    return {
        "reference": reference,
        "candidate": "with_prior",
        "n": len(frame),
        "improvement_bp": value["estimate"],
        "se_bp": value["se"],
        "low_bp": value["low"],
        "high_bp": value["high"],
        "states": result.states,
        "quarters": result.quarters,
        "cluster_df": result.df,
    }


def prediction_metrics(frame):
    return [
        {
            "model": model,
            "n": len(frame),
            "mae_bp": float(frame["loss_" + model].mean()),
            "rmse_bp": float(np.sqrt(np.mean(frame["error_" + model] ** 2))),
            "bias_bp": float(frame["error_" + model].mean()),
        }
        for model in ("training_mean", "previous_award", "market_case", "with_prior")
    ]


def rolling_evaluation(main):
    rows, blocks = [], []
    for start, train, test, status in expanding_blocks(main):
        block = {
            "start": start,
            "end": start + 4,
            "training_n": len(train),
            "test_n": len(test),
            "status": status,
        }
        blocks.append(block)
        if status != "available":
            continue
        predictions = {
            "training_mean": np.repeat(train.roe.mean(), len(test)),
            "previous_award": test.prior.to_numpy(),
        }
        for model, features in (
            ("market_case", PREDICTORS),
            ("with_prior", PREDICTORS + ["prior"]),
        ):
            x = design(train, features)
            beta = np.linalg.lstsq(x.to_numpy(), train.roe.to_numpy(), rcond=None)[0]
            predictions[model] = design(test, features)[x.columns].to_numpy() @ beta
        for i, row in enumerate(test.itertuples()):
            record = {
                "id": row.id,
                "date": row.authorized_date,
                "year": row.year,
                "state": row.state,
                "quarter": row.quarter,
                "region": row.region,
                "entity": row.entity,
                "block": f"{start}-{start + 4}",
                "actual": row.roe,
                "training_end": int(train.year.max()),
                "training_n": len(train),
            }
            for name, predicted in predictions.items():
                record[name] = float(predicted[i])
                record["error_" + name] = float((predicted[i] - row.roe) * 100)
                record["loss_" + name] = abs(record["error_" + name])
            rows.append(record)
    frame = pd.DataFrame(rows)
    if frame.empty or frame.id.duplicated().any():
        raise ValueError("Rolling evaluation must contain unique later-case observations")
    for block in blocks:
        if block["status"] == "available":
            part = frame[frame.block == f"{block['start']}-{block['end']}"]
            block["metrics"] = prediction_metrics(part)
            block["paired_improvement"] = loss_comparison(part, "previous_award")
    return frame, blocks


def summarize_groups(frame, group):
    rows = []
    for name, part in frame.groupby(group, sort=True):
        awards = part.roe.dropna()
        paired = part.dropna(subset=["roe", "prior"])
        rows.append(
            {
                "group": str(name),
                "cases": len(part),
                "observed_awards": len(awards),
                "utilities": part.entity.nunique(),
                "states": part.state.nunique(),
                "mean_roe": float(awards.mean()),
                "median_roe": float(awards.median()),
                "paired_awards": len(paired),
                "mean_adjustment_bp": float((paired.roe - paired.prior).mean() * 100),
                "unchanged_awards": int((paired.roe == paired.prior).sum()),
                "main_complete": int(part.main_eligible.sum()),
                "change_complete": int(part.change_eligible.sum()),
            }
        )
    return rows


def calculate(root=ROOT):
    root = Path(root)
    history = EconomicHistory(root)
    raw, controls = read_workbook(root / "data/external/eei/eei_rate_review_2025_q3.xlsx")
    validate_quarters(raw, controls)
    frame = make_panel(enrich(raw, []), history)
    main = frame[frame.main_eligible]
    coefficients, models, specs, tests, sensitivity, joint_rows, slopes, influence = estimate(frame)
    predictions, blocks = rolling_evaluation(main)
    original = pd.read_csv(root / "reports/factor-study/estimation.csv")
    bridge_ids = set(main.loc[main.year >= 2010, "id"])
    if set(original.id) != bridge_ids:
        raise ValueError("The 2010-2024 bridge does not preserve the original estimation IDs")
    missing = {
        name: int(frame.loc[frame.year >= 1995, name].isna().sum()) for name in ["roe", *LOCAL]
    }
    summary = {
        "schema": SCHEMA,
        "primary_years": [1995, 2024],
        "longer_years": [1985, 2024],
        "source_vintage": "EEI 2025 Q3; revised economic histories retrieved October 28, 2026",
        "coverage": {
            "primary_candidates": int((frame.year >= 1995).sum()),
            "main_complete": len(main),
            "main_states": main.state.nunique(),
            "main_entities": main.entity.nunique(),
            "main_quarters": main.quarter.nunique(),
            "changes": int(frame.change_eligible.sum()),
            "long_complete": int(frame.long_eligible.sum()),
            "original_complete": len(original),
            "bridge_ids_match": True,
            "economic_series": len(history.series),
            "economic_numeric_observations": sum(
                r["numeric_rows"] for r in history.manifest["series"]
            ),
        },
        "missing_fields_primary": missing,
        "models": models,
        "coefficients": coefficients,
        "joint_tests": tests,
        "covariance_sensitivity": sensitivity,
        "joint_test_sensitivity": joint_rows,
        "regional_slopes": slopes,
        "state_influence": influence,
        "prediction_blocks": blocks,
        "rolling_metrics": prediction_metrics(predictions),
        "rolling_comparisons": [
            loss_comparison(predictions, x) for x in ("previous_award", "market_case")
        ],
        "regional": summarize_groups(frame[frame.year >= 1995], "region"),
        "uncertainty": "Two-way state/authorization-quarter covariance; finite-sample corrections; t intervals with smaller cluster count minus one",
    }
    return frame, predictions, specs, summary


def figures(frame, summary, output):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    main = frame[frame.main_eligible]
    annual = main.groupby("year").agg(
        roe=("roe", "mean"), prior=("prior", "mean"), n=("id", "size")
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
    axes[0].plot(annual.index, annual.roe, color="#244d42", label="Current award")
    axes[0].plot(annual.index, annual.prior, color="#808782", ls="--", label="Prior award")
    axes[0].set(
        xlabel="Authorization year",
        ylabel="Allowed ROE (%)",
        title="Awards across the expanded period",
    )
    axes[0].legend(frameon=False)
    for region, part in main.groupby("region"):
        counts = part.groupby("year").size().reindex(range(1995, 2025), fill_value=0)
        colors = {
            "Midwest": "#244d42",
            "Northeast": "#78978a",
            "South": "#766d57",
            "West": "#526e80",
        }
        styles = {"Midwest": "-", "Northeast": "--", "South": "-.", "West": ":"}
        axes[1].plot(
            counts.index, counts, label=region, lw=1.5, color=colors[region], ls=styles[region]
        )
    axes[1].set(
        xlabel="Authorization year",
        ylabel="Complete observations",
        title="Regional coverage varies by year",
    )
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "historical-coverage.png", dpi=180)
    plt.close(fig)
    selected = [
        r
        for r in summary["coefficients"]
        if (r["model"], r["term"])
        in {
            ("change", "delta_treasury90"),
            ("change_state_year", "delta_treasury90"),
            ("asymmetric", "rate_rise"),
            ("asymmetric", "rate_fall"),
        }
    ]
    labels = {
        "change": "Award changes: pooled",
        "change_state_year": "Award changes: state + year",
        "rate_rise": "Treasury increases",
        "rate_fall": "Treasury decreases",
    }
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, row in enumerate(selected):
        if row["low"] is not None:
            ax.plot([100 * row["low"], 100 * row["high"]], [i, i], color="#244d42", lw=1.5)
        ax.plot(100 * row["estimate"], i, "o", color="#244d42")
    ax.axvline(0, color="#a8aaa8", ls="--", lw=0.8)
    ax.set(
        yticks=range(len(selected)),
        yticklabels=[labels.get(r["term"], labels.get(r["model"])) for r in selected],
        xlabel="Award adjustment (bp) per one-percentage-point Treasury change",
        title="Changes in financial conditions and allowed returns",
    )
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output / "rate-adjustment.png", dpi=180)
    plt.close(fig)
    metrics = []
    for block in summary["prediction_blocks"]:
        if block["status"] == "available":
            metrics.append(
                (
                    str(block["start"]) + "–" + str(block["end"]),
                    {r["model"]: r["mae_bp"] for r in block["metrics"]},
                )
            )
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(metrics))
    for offset, name, label, color in (
        (-0.18, "previous_award", "Previous award", "#a3aaa5"),
        (0.18, "with_prior", "Augmented model", "#244d42"),
    ):
        bars = ax.bar(x + offset, [m[name] for _, m in metrics], 0.36, color=color, label=label)
        ax.bar_label(bars, fmt="%.1f", fontsize=8, padding=3)
    ax.set(
        xticks=x,
        xticklabels=[name for name, _ in metrics],
        ylabel="Mean absolute error (bp)",
        title="Expanding-window evaluation",
    )
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output / "rolling-errors.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, row in enumerate(summary["regional_slopes"]):
        if row["low"] is not None:
            ax.plot([row["low"] * 100, row["high"] * 100], [i, i], color="#244d42", lw=1.5)
        ax.plot(row["estimate"] * 100, i, "o", color="#244d42")
    ax.axvline(0, color="#a8aaa8", ls="--", lw=0.8)
    ax.set(
        yticks=range(4),
        yticklabels=[
            r["region"] + " (n=" + str(r["region_n"]) + ")" for r in summary["regional_slopes"]
        ],
        xlabel="Award adjustment (bp) per one-percentage-point Treasury change",
        title="Regional associations in award changes",
    )
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output / "regional-slopes.png", dpi=180)
    plt.close(fig)


def save_manifest(root, output, r_status):
    paths = [
        PLAN,
        SOURCE / "manifest.json",
        Path("data/external/eei/eei_rate_review_2025_q3.xlsx"),
        Path("reports/factor-study/study.json"),
        Path("reports/factor-study/estimation.csv"),
        *[
            Path(p)
            for p in (
                "src/economic_history.py",
                "src/panel_models.py",
                "src/expanded_study.py",
                "src/panel_diagnostics.py",
                "scripts/fetch_expanded_sources.py",
                "scripts/benchmark_history_joins.py",
                "analysis/expanded.R",
                "analysis/expanded.do",
            )
        ],
    ]
    manifest = {
        "schema": SCHEMA,
        "r_validation": r_status,
        "inputs": {str(p): digest(root / p) for p in paths},
        "outputs": {
            p.name: digest(p)
            for p in sorted(output.iterdir())
            if p.is_file() and p.name != "manifest.json"
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def build(root=ROOT, output=None):
    root = Path(root)
    output = Path(output) if output is not None else root / OUTPUT
    if output.exists() and any(output.iterdir()):
        marker = output / "manifest.json"
        if not marker.exists() or json.loads(marker.read_text()).get("schema") != SCHEMA:
            raise ValueError("Use an empty output directory or an existing expanded-study export")
    frame, predictions, specs, summary = calculate(root)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "panel.csv", index=False)
    frame.to_stata(output / "panel.dta", write_index=False, version=118)
    for name, mask in (
        ("estimation", frame.main_eligible),
        ("changes", frame.change_eligible),
        ("long", frame.long_eligible),
    ):
        selected = frame[mask].copy()
        selected.to_csv(output / (name + ".csv"), index=False)
        # Stata 14+ Unicode format. Blanks remain missing; no source fields are imputed.
        selected.to_stata(output / (name + ".dta"), write_index=False, version=118)
        restored = pd.read_stata(output / (name + ".dta"), convert_categoricals=False)
        if restored.id.tolist() != selected.id.tolist() or not np.allclose(
            restored.roe, selected.roe
        ):
            raise ValueError("Stata export did not preserve row identities and observed returns")
    predictions.to_csv(output / "predictions.csv", index=False)
    pd.DataFrame(specs).to_csv(output / "model_specs.csv", index=False)
    pd.DataFrame(summary["coefficients"]).to_csv(output / "coefficients.csv", index=False)
    pd.DataFrame(summary["models"]).to_csv(output / "model_coverage.csv", index=False)
    pd.DataFrame(summary["regional"]).to_csv(output / "regions.csv", index=False)
    for key in (
        "covariance_sensitivity",
        "joint_test_sensitivity",
        "regional_slopes",
        "state_influence",
    ):
        pd.DataFrame(summary[key]).to_csv(output / (key + ".csv"), index=False)
    pd.DataFrame(summarize_groups(frame[frame.year >= 1995], "year")).to_csv(
        output / "annual.csv", index=False
    )
    (output / "study.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    for name in (
        "r-crosscheck.csv",
        "r-predictions.csv",
        "r-history.png",
        "r-covariance.csv",
        "r-joint-tests.csv",
        "r-regional-slopes.csv",
    ):
        (output / name).unlink(missing_ok=True)
    figures(frame, summary, output)
    save_manifest(root, output, "not_run")
    return summary


def check_fingerprints(root, output):
    root = Path(root)
    output = Path(output) if output is not None else root / OUTPUT
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["schema"] != SCHEMA:
        raise ValueError("Unrecognized expanded-study manifest")
    for name, expected in manifest["inputs"].items():
        if digest(root / name) != expected:
            raise ValueError("Expanded study input changed: " + name)
    for name, expected in manifest["outputs"].items():
        if digest(output / name) != expected:
            raise ValueError("Expanded study output changed: " + name)
    return manifest


def numeric_equal(expected, actual):
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and expected.keys() == actual.keys()
            and all(numeric_equal(value, actual[key]) for key, value in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(expected) == len(actual)
            and all(numeric_equal(a, b) for a, b in zip(expected, actual))
        )
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and np.isclose(expected, actual, rtol=0, atol=1e-8)
    return expected == actual


def verify(root=ROOT, output=None, verify_r=False):
    root = Path(root)
    output = Path(output) if output is not None else root / OUTPUT
    manifest = check_fingerprints(root, output)
    _frame, _, _, calculated = calculate(root)
    saved = json.loads((output / "study.json").read_text())
    if not numeric_equal(calculated, saved):
        raise ValueError("Expanded study calculations do not reproduce")
    expected = pd.DataFrame(calculated["coefficients"])
    actual = pd.read_csv(output / "coefficients.csv")
    if list(zip(expected.model, expected.term)) != list(
        zip(actual.model, actual.term)
    ) or not np.allclose(
        expected[["estimate", "se", "low", "high"]].astype(float),
        actual[["estimate", "se", "low", "high"]].astype(float),
        atol=1e-8,
        rtol=0,
        equal_nan=True,
    ):
        raise ValueError("Expanded model coefficients do not reproduce")
    if verify_r or manifest["r_validation"] != "not_run":
        r = pd.read_csv(output / "r-crosscheck.csv")
        if list(zip(r.model, r.term)) != list(zip(actual.model, actual.term)) or not np.allclose(
            r[["estimate", "se", "low", "high"]],
            actual[["estimate", "se", "low", "high"]],
            atol=1e-7,
            rtol=0,
            equal_nan=True,
        ):
            raise ValueError("Native R model calculations differ from Python")
        r_predictions = pd.read_csv(output / "r-predictions.csv")
        predictions = pd.read_csv(output / "predictions.csv")
        keys = ["training_mean", "previous_award", "market_case", "with_prior"]
        if r_predictions.id.tolist() != predictions.id.tolist() or not np.allclose(
            r_predictions[keys], predictions[keys], rtol=0, atol=1e-8
        ):
            raise ValueError("Native R rolling predictions differ from Python")
        for reference, checked, keys, values in (
            (
                "covariance_sensitivity.csv",
                "r-covariance.csv",
                ["model", "covariance", "term"],
                ["estimate", "se", "low", "high"],
            ),
            (
                "joint_test_sensitivity.csv",
                "r-joint-tests.csv",
                ["test", "covariance"],
                ["statistic", "p"],
            ),
            (
                "regional_slopes.csv",
                "r-regional-slopes.csv",
                ["region"],
                ["estimate", "se", "low", "high"],
            ),
        ):
            a, b = pd.read_csv(output / reference), pd.read_csv(output / checked)
            if not a[keys].equals(b[keys]) or not np.allclose(
                a[values], b[values], atol=1e-7, rtol=0, equal_nan=True
            ):
                raise ValueError("Native R diagnostic differs: " + checked)
        if verify_r:
            save_manifest(
                root,
                output,
                str(len(r))
                + " coefficient/SE/interval rows and "
                + str(len(predictions))
                + " predictions for four rules matched in native R",
            )
    return {
        "status": "passed",
        "coverage": calculated["coverage"],
        "r_validation": json.loads((output / "manifest.json").read_text())["r_validation"],
    }


def explore(root=ROOT, *, kind="levels", region="all", start=1995, end=2024, export=None):
    if not 1995 <= start <= end <= 2024 or kind not in ("levels", "changes"):
        raise ValueError("Select levels or changes within 1995-2024")
    if region not in ("all", "Northeast", "Midwest", "South", "West"):
        raise ValueError("Unknown Census region")
    root = Path(root)
    check_fingerprints(root, root / OUTPUT)
    frame = pd.read_csv(root / OUTPUT / "panel.csv")
    selected = frame[
        frame.year.between(start, end) & ((frame.region == region) if region != "all" else True)
    ]
    flag, target, features = (
        ("main_eligible", "roe", LOCAL)
        if kind == "levels"
        else ("change_eligible", "delta_roe", CHANGES)
    )
    sample = selected[selected[flag]]
    result = {
        "mode": "exploratory; published findings are unchanged",
        "kind": kind,
        "region": region,
        "years": [start, end],
        "candidates": len(selected),
        "complete": len(sample),
        "states": sample.state.nunique(),
        "mean_award_percent": float(sample.roe.mean()) if len(sample) else None,
    }
    try:
        model = fit(sample, target, features, "state_year")
        result["model"] = {
            "status": "estimated",
            "effects": "state and year",
            "cluster_df": model.df,
            "coefficients": model.coefficients(features),
        }
    except ValueError as error:
        result["model"] = {"status": "unavailable", "reason": str(error)}
    if export:
        destination = Path(export)
        if destination.exists() or destination.resolve().is_relative_to((root / OUTPUT).resolve()):
            raise ValueError("Export to a new file outside the published report directory")
        sample.to_csv(destination, index=False)
        result["exported_rows"] = len(sample)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--verify-r", action="store_true")
    modes.add_argument("--explore", choices=["levels", "changes"])
    parser.add_argument(
        "--region", default="all", choices=["all", "Northeast", "Midwest", "South", "West"]
    )
    parser.add_argument("--start", type=int, default=1995)
    parser.add_argument("--end", type=int, default=2024)
    parser.add_argument("--export", type=Path, help="New CSV for a selected exploratory sample")
    args = parser.parse_args()
    if args.explore:
        print(
            json.dumps(
                explore(
                    kind=args.explore,
                    region=args.region,
                    start=args.start,
                    end=args.end,
                    export=args.export,
                ),
                indent=2,
                allow_nan=False,
            )
        )
        return
    result = (
        verify(output=args.output, verify_r=args.verify_r)
        if args.check or args.verify_r
        else build(output=args.output)
    )
    print(
        json.dumps(
            result
            if args.check or args.verify_r
            else {
                k: result[k]
                for k in ("coverage", "joint_tests", "rolling_metrics", "rolling_comparisons")
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
