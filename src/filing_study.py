"""Separate recorded requests from decisions and evaluate filing-date predictions."""

import argparse
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

from .economic_history import SOURCE, EconomicHistory, SeriesIndex
from .eei_benchmarks import read_workbook, validate_quarters
from .expanded_study import digest, numeric_equal
from .national_study import enrich
from .panel_models import design, ols

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("reports/filing-study")
PLAN = Path("docs/filing_analysis_plan_2026-10-30.md")
SCHEMA = "anchored-returns-filing-study/1"
EXTRA_SOURCE = Path("data/external/filing_2026-10-30")
FINANCIAL = ["treasury90", "inflation", "unemployment"]
STAGE_FEATURES = (
    ["filing_" + k for k in FINANCIAL]
    + ["update_" + k for k in FINANCIAL]
    + ["duration", "distribution"]
)
FORECAST_FEATURES = ["filing_" + k for k in FINANCIAL] + [
    "distribution",
    "prior_age",
    "known_prior",
]
RULES = ("prior", "request", "request_adjusted", "prior_adjusted", "market_prior", "with_request")
TARGETS = ("request", "award", "decision_gap")


class FilingHistory(EconomicHistory):
    def __init__(self, root):
        super().__init__(root)
        folder = Path(root) / EXTRA_SOURCE
        record = json.loads((folder / "manifest.json").read_text())
        if (
            record.get("schema") != "anchored-returns-filing-sources/1"
            or record.get("series_id") != "ALUR"
        ):
            raise ValueError("Wrong supplemental source identity")
        if digest(folder / "ALUR.csv") != record["sha256"]:
            raise ValueError("Supplemental source fingerprint changed")
        self.series["ALUR"] = SeriesIndex.from_csv(folder / "ALUR.csv", "ALUR")
        self.states["Alabama"] = {"region": "South", "series_id": "ALUR"}


def make_panel(records, history):
    by_entity = defaultdict(lambda: defaultdict(list))
    for row in records:
        if row["award_bp"] is not None:
            by_entity[(row["state"], row["utility"])][row["authorized_date"]].append(row)
    output = []
    for row in records:
        if not 1980 <= row["year"] <= 2024:
            continue
        filing, decision = row["requested_date"], row["authorized_date"]
        duration = (
            (date.fromisoformat(decision) - date.fromisoformat(filing)).days if filing else None
        )
        valid = duration is not None and 0 <= duration <= 3652
        dated = by_entity[(row["state"], row["utility"])]
        days = sorted(dated)

        def prior_at(cutoff, days=days, dated=dated):
            index = bisect_left(days, cutoff) - 1 if cutoff else -1
            previous = days[index] if index >= 0 else None
            gap = (
                (date.fromisoformat(cutoff) - date.fromisoformat(previous)).days
                if previous
                else None
            )
            rows = dated[previous] if previous and gap <= 3652 else []
            return rows, previous if rows else None, gap if rows else None

        earlier, prior_date, age = prior_at(filing if valid else None)
        decision_prior, decision_prior_date, _ = prior_at(decision)
        output.append(
            {
                **{k: v for k, v in row.items() if not k.startswith("treasury_")},
                "entity": row["state"] + " / " + row["utility"],
                "quarter": decision[:4] + "Q" + str((int(decision[5:7]) - 1) // 3 + 1),
                "region": history.states[row["state"]]["region"],
                "decision_group": row["state"]
                + "|"
                + decision
                + "|"
                + " ".join(row["docket"].split()),
                "decision_day_group": row["state"] + "|" + decision,
                "filing_valid": valid,
                "filing_year": int(filing[:4]) if valid else None,
                "duration": duration / 365.25 if valid else None,
                "distribution": int(row["case_type"] == "Distribution"),
                "request": row["request_bp"] / 100 if row["request_bp"] is not None else None,
                "request_vintage_verified": False,
                "award": row["award_bp"] / 100 if row["award_bp"] is not None else None,
                "known_prior": float(np.mean([p["award_bp"] for p in earlier])) / 100
                if earlier
                else None,
                "known_prior_date": prior_date,
                "known_prior_ids": ";".join(p["id"] for p in earlier),
                "known_prior_rows": len(earlier),
                "prior_age": age / 365.25 if earlier else None,
                "decision_prior_date": decision_prior_date,
                "decision_prior_ids": ";".join(p["id"] for p in decision_prior),
            }
        )
    frame = pd.DataFrame(output)
    frame["decision_gap"] = frame.award - frame.request
    frame["request_change"] = frame.request - frame.known_prior
    frame["award_change"] = frame.award - frame.known_prior
    frame["prior_changed_at_filing"] = frame.known_prior_ids != frame.decision_prior_ids
    for prefix, column in (("filing_", "requested_date"), ("decision_", "authorized_date")):
        mask = frame.filing_valid if prefix == "filing_" else pd.Series(True, index=frame.index)
        joined = history.join(frame.loc[mask, column], frame.loc[mask, "state"])
        joined.index = frame.index[mask]
        # Keep reference dates and counts as well as the numeric model inputs.
        for key in joined:
            if key not in ("curve90", "stress"):
                frame[prefix + key] = joined[key]
    for key in FINANCIAL:
        frame["update_" + key] = frame["decision_" + key] - frame["filing_" + key]
    frame["paired"] = frame[["request", "award"]].notna().all(axis=1) & frame.filing_valid
    frame["stage_eligible"] = (
        frame.paired & (frame.year >= 1985) & frame[STAGE_FEATURES].notna().all(axis=1)
    )
    frame["prior_eligible"] = frame.stage_eligible & frame.known_prior.notna()
    frame["forecast_eligible"] = (
        frame.paired & (frame.filing_year >= 1985) & frame[FORECAST_FEATURES].notna().all(axis=1)
    )
    return frame


def fit_stage(frame, target, features, effects, weight="rows"):
    x = design(frame, features, effects)
    if weight == "decision_days":
        # Same-day decisions may share a proceeding even when docket labels differ.
        group = "decision_day_group"
        scale = np.sqrt(1 / frame.groupby(group)[group].transform("size").to_numpy())
    elif weight == "rows":
        scale = np.ones(len(frame))
    else:
        raise ValueError("Unknown observation weight")
    return ols(x.mul(scale, axis=0), frame[target].to_numpy() * scale, frame.state, frame.quarter)


def specifications():
    return [
        ("paired", "stage_eligible", STAGE_FEATURES, "state_year", "rows"),
        ("known_prior", "prior_eligible", STAGE_FEATURES + ["known_prior"], "state_year", "rows"),
        (
            "utility_controls",
            "prior_eligible",
            STAGE_FEATURES + ["known_prior"],
            "entity_year",
            "rows",
        ),
        (
            "decision_day_weight",
            "prior_eligible",
            STAGE_FEATURES + ["known_prior"],
            "state_year",
            "decision_days",
        ),
    ]


def estimate(frame):
    rows, specs, coverage, decompositions = [], [], [], []
    for name, flag, features, effects, weight in specifications():
        selected = frame[frame[flag]]
        results = {}
        for target in TARGETS:
            model_name = name + "_" + target
            model = fit_stage(selected, target, features, effects, weight)
            results[target] = model
            for covariance in ("two_way", "state", "quarter"):
                rows.extend(
                    {"model": model_name, "covariance": covariance, **r}
                    for r in model.coefficients(features, covariance)
                )
            specs.append(
                {
                    "model": model_name,
                    "flag": flag,
                    "target": target,
                    "features": ";".join(features),
                    "effects": effects,
                    "weight": weight,
                }
            )
            coverage.append(
                {
                    "model": model_name,
                    "n": len(selected),
                    "groups": selected.decision_group.nunique(),
                    "states": model.states,
                    "quarters": model.quarters,
                    "entities": selected.entity.nunique(),
                    "parameters": model.parameters,
                    "df": model.df,
                }
            )
        difference = results["award"].beta - results["request"].beta - results["decision_gap"].beta
        if not np.allclose(difference, 0, rtol=0, atol=1e-9):
            raise ValueError("Request/decision coefficient identity failed")
        for feature in features:
            idx = results["award"].names.index(feature)
            decompositions.append(
                {
                    "specification": name,
                    "term": feature,
                    "request": float(results["request"].beta[idx]),
                    "decision_gap": float(results["decision_gap"].beta[idx]),
                    "award": float(results["award"].beta[idx]),
                    "identity_error": float(difference[idx]),
                }
            )
    return rows, specs, coverage, decompositions


def loss_comparison(predictions, candidate, baseline):
    gain = predictions["loss_" + baseline] - predictions["loss_" + candidate]
    fitted = ols(
        pd.DataFrame({"const": np.ones(len(gain))}),
        gain.to_numpy(),
        predictions.state,
        predictions.quarter,
    )
    return {
        "candidate": candidate,
        "baseline": baseline,
        "n": len(gain),
        **fitted.coefficients(["const"])[0],
    }


def metrics(predictions):
    return [
        {
            "rule": key,
            "n": len(predictions),
            "mae_bp": float(predictions["loss_" + key].mean()),
            "rmse_bp": float(np.sqrt(np.mean(predictions["error_" + key] ** 2))),
        }
        for key in RULES
    ]


def rolling_evaluation(frame):
    frame = frame[frame.forecast_eligible]
    records, blocks = [], []
    for start, end in ((2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2022)):
        cutoff = f"{start}-01-01"
        train = frame[frame.authorized_date < cutoff]
        test = frame[frame.filing_year.between(start, end)]
        block = {
            "block": f"{start}-{end}",
            "start": start,
            "end": end,
            "training_n": len(train),
            "test_n": len(test),
            "cutoff": cutoff,
            "status": "available" if len(train) >= 100 and len(test) else "insufficient_history",
        }
        blocks.append(block)
        if block["status"] != "available":
            continue
        if (
            train.authorized_date.max() >= test.requested_date.min()
            or not (test.known_prior_date < test.requested_date).all()
        ):
            raise ValueError("Filing-date prediction uses unavailable outcomes")
        predicted = {
            "prior": test.known_prior.to_numpy(),
            "request": test.request.to_numpy(),
            "request_adjusted": test.request.to_numpy() + train.decision_gap.mean(),
            "prior_adjusted": test.known_prior.to_numpy() + train.award_change.mean(),
        }
        for name, features in (
            ("market_prior", FORECAST_FEATURES),
            ("with_request", FORECAST_FEATURES + ["request"]),
        ):
            try:
                x = design(train, features)
                if np.linalg.matrix_rank(x) != x.shape[1]:
                    raise ValueError("Prediction training matrix lacks rank")
            except ValueError as error:
                block["status"] = "unavailable_training_design"
                block["reason"] = str(error)
                break
            xp = test[features].astype(float).copy()
            xp.insert(0, "const", 1.0)
            beta = np.linalg.lstsq(x.to_numpy(), train.award.to_numpy(), rcond=None)[0]
            predicted[name] = xp.to_numpy() @ beta
        if block["status"] != "available":
            continue
        for i, row in enumerate(test.itertuples()):
            record = {
                "id": row.id,
                "state": row.state,
                "quarter": row.quarter,
                "region": row.region,
                "requested_date": row.requested_date,
                "authorized_date": row.authorized_date,
                "known_prior_date": row.known_prior_date,
                "known_prior_ids": row.known_prior_ids,
                "block": block["block"],
                "training_cutoff": cutoff,
                "last_training_decision": train.authorized_date.max(),
                "training_n": len(train),
                "actual": row.award,
            }
            for key in RULES:
                record[key] = float(predicted[key][i])
                record["error_" + key] = float(100 * (predicted[key][i] - row.award))
                record["loss_" + key] = abs(record["error_" + key])
            records.append(record)
    predictions = pd.DataFrame(records)
    if predictions.empty or predictions.id.duplicated().any():
        raise ValueError("Prediction cases must be nonempty and unique")
    for block in blocks:
        if block["status"] == "available":
            block["metrics"] = metrics(predictions[predictions.block == block["block"]])
    comparisons = [
        loss_comparison(predictions, "with_request", baseline)
        for baseline in ("prior", "request_adjusted", "market_prior")
    ]
    return predictions, blocks, comparisons


def describe(frame):
    paired = frame[frame.paired]
    return {
        "candidates": len(frame),
        "pairs": len(paired),
        "states": paired.state.nunique(),
        "groups": paired.decision_group.nunique(),
        "decision_days": paired.decision_day_group.nunique(),
        "mean_request": float(paired.request.mean()),
        "mean_award": float(paired.award.mean()),
        "mean_gap_bp": float(100 * paired.decision_gap.mean()),
        "median_gap_bp": float(100 * paired.decision_gap.median()),
        "below_request": int((paired.award_bp < paired.request_bp).sum()),
        "equal_request": int((paired.award_bp == paired.request_bp).sum()),
        "above_request": int((paired.award_bp > paired.request_bp).sum()),
    }


def calculate(root=ROOT):
    root = Path(root)
    raw, controls = read_workbook(root / "data/external/eei/eei_rate_review_2025_q3.xlsx")
    validate_quarters(raw, controls)
    frame = make_panel(enrich(raw, []), FilingHistory(root))
    coefficients, specs, models, decomposition = estimate(frame)
    predictions, blocks, comparisons = rolling_evaluation(frame)
    omission = []
    sample = frame[frame.prior_eligible]
    for state in sorted(sample.state.unique()):
        part = sample[sample.state != state]
        try:
            model = fit_stage(part, "award", STAGE_FEATURES + ["known_prior"], "state_year")
            omission.append(
                {
                    "omitted_state": state,
                    "status": "available",
                    **model.coefficients(["known_prior"])[0],
                }
            )
        except ValueError as error:
            omission.append({"omitted_state": state, "status": str(error)})
    earlier = pd.read_csv(root / "reports/expanded-study/estimation.csv")
    annual = [{"year": int(year), **describe(part)} for year, part in frame.groupby("year")]
    regional = [{"region": region, **describe(part)} for region, part in frame.groupby("region")]
    summary = {
        "schema": SCHEMA,
        "date": "2026-10-30",
        "coverage": {
            **describe(frame),
            "stage_complete": int(frame.stage_eligible.sum()),
            "known_prior_complete": int(frame.prior_eligible.sum()),
            "forecast_complete": int(frame.forecast_eligible.sum()),
            "predictions": len(predictions),
            "original_model_rows": len(earlier),
            "original_overlap_in_stage": len(
                set(earlier.id) & set(frame.loc[frame.stage_eligible, "id"])
            ),
            "prior_dates_differ": int((frame.prior_changed_at_filing & frame.paired).sum()),
        },
        "exclusions": {
            "missing_award": int(frame.award.isna().sum()),
            "missing_request": int(frame.request.isna().sum()),
            "invalid_filing": int((~frame.filing_valid).sum()),
            "stage_missing": {
                key: int(frame.loc[frame.paired & (frame.year >= 1985), key].isna().sum())
                for key in STAGE_FEATURES
            },
        },
        "models": models,
        "coefficients": coefficients,
        "decomposition": decomposition,
        "annual": annual,
        "regional": regional,
        "state_omission": omission,
        "prediction_blocks": blocks,
        "prediction_metrics": metrics(predictions),
        "prediction_comparisons": comparisons,
        "interpretation": "Recorded requests and decisions; association and accounting decomposition, not causal mediation. Revised predictors; completed-case retrospective evaluation.",
        "request_vintage": "EEI records a request and filing date but no amendment history. The recorded request is not verified as the value available on that exact filing date.",
    }
    return frame, predictions, specs, summary


def figures(frame, summary, output):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    annual = pd.DataFrame(summary["annual"])
    fig, axes = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    axes[0].plot(annual.year, annual.mean_request, color="#222222", label="Requested")
    axes[0].plot(annual.year, annual.mean_award, color="#5e7a6a", label="Authorized")
    axes[0].set(
        ylabel="Return on equity (%)", title="Requested and authorized returns in the same cases"
    )
    axes[0].legend(frameon=False)
    axes[1].bar(annual.year, annual.pairs, color="#9ba69d", width=0.8)
    axes[1].set(ylabel="Paired observations", xlabel="Authorization year")
    fig.tight_layout()
    fig.savefig(output / "requests-awards.png", dpi=180)
    plt.close(fig)
    part = pd.DataFrame(summary["coefficients"])
    part = part[
        (part.covariance == "two_way")
        & (part.term == "known_prior")
        & part.model.str.startswith("known_prior_")
    ]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for i, row in enumerate(part.itertuples()):
        if np.isfinite(row.low):
            ax.plot([100 * row.low, 100 * row.high], [i, i], color="#5e7a6a")
        ax.plot(100 * row.estimate, i, "o", color="#222222")
    ax.axvline(0, color="#aaaaaa", ls="--", lw=0.8)
    ax.set(
        yticks=range(len(part)),
        yticklabels=[
            r.removeprefix("known_prior_").replace("_", " ").capitalize() for r in part.model
        ],
        xlabel="Basis points per one-percentage-point higher known prior award",
        title="Where the prior-award association appears",
    )
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output / "stage-decomposition.png", dpi=180)
    plt.close(fig)
    blocks = [b for b in summary["prediction_blocks"] if b["status"] == "available"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    styles = (
        ("prior", "Known prior", "#aaaaaa"),
        ("request_adjusted", "Request + historical gap", "#5e7a6a"),
        ("with_request", "Model with request", "#222222"),
    )
    positions = np.arange(len(blocks))
    width = 0.24
    for j, (key, label, color) in enumerate(styles):
        values = [next(m["mae_bp"] for m in b["metrics"] if m["rule"] == key) for b in blocks]
        bars = ax.bar(positions + (j - 1) * width, values, width, label=label, color=color)
        ax.bar_label(bars, fmt="%.1f", fontsize=8, padding=3)
    ax.set(
        xticks=positions,
        xticklabels=[b["block"] for b in blocks],
        ylabel="Mean absolute error (bp)",
        xlabel="Filing-year evaluation block",
        title="Retrospective comparison by filing-year block",
    )
    ax.margins(y=0.22)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "filing-predictions.png", dpi=180)
    plt.close(fig)


def write_manifest(root, output, r_status="not_run"):
    inputs = [
        PLAN,
        SOURCE / "manifest.json",
        EXTRA_SOURCE / "manifest.json",
        EXTRA_SOURCE / "ALUR.csv",
        EXTRA_SOURCE / "source_review.json",
        Path("scripts/fetch_filing_sources.py"),
        Path("data/external/eei/eei_rate_review_2025_q3.xlsx"),
        Path("reports/expanded-study/estimation.csv"),
        *[
            Path("src") / name
            for name in (
                "filing_study.py",
                "economic_history.py",
                "panel_models.py",
                "eei_benchmarks.py",
                "national_study.py",
            )
        ],
        Path("analysis/filing.R"),
        Path("analysis/filing.do"),
    ]
    manifest = {
        "schema": SCHEMA,
        "inputs": {str(p): digest(root / p) for p in inputs},
        "outputs": {
            p.name: digest(p)
            for p in sorted(output.iterdir())
            if p.is_file() and p.name != "manifest.json"
        },
        "r_validation": r_status,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def build(root=ROOT, output=None):
    root = Path(root)
    output = Path(output) if output else root / OUTPUT
    if output.exists() and any(output.iterdir()) and not (output / "manifest.json").exists():
        raise ValueError("Use a new output folder or an existing filing-study export")
    if (output / "manifest.json").exists() and json.loads(
        (output / "manifest.json").read_text()
    ).get("schema") != SCHEMA:
        raise ValueError("Unrecognized output folder")
    frame, predictions, specs, summary = calculate(root)
    output.mkdir(parents=True, exist_ok=True)
    tables = {
        "panel": frame,
        "predictions": predictions,
        "model_specs": pd.DataFrame(specs),
        **{
            key: pd.DataFrame(summary[key])
            for key in (
                "coefficients",
                "models",
                "decomposition",
                "annual",
                "regional",
                "state_omission",
            )
        },
    }
    for name, table in tables.items():
        table.to_csv(output / (name + ".csv"), index=False)
    for name, data in (
        ("paired", frame[frame.paired]),
        ("stage", frame[frame.stage_eligible]),
        ("known-prior", frame[frame.prior_eligible]),
    ):
        data.to_csv(output / (name + ".csv"), index=False)
        data.to_stata(output / (name + ".dta"), write_index=False, version=118)
        restored = pd.read_stata(output / (name + ".dta"), convert_categoricals=False)
        numeric = data.select_dtypes(include="number").columns
        if restored.id.tolist() != data.id.tolist() or not np.allclose(
            restored[numeric], data[numeric], equal_nan=True, atol=1e-12, rtol=0
        ):
            raise ValueError("Stata round trip changed source values")
    (output / "study.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    # The browser export keeps source identities while avoiding a large predictor payload.
    columns = [
        "id",
        "state",
        "utility",
        "docket",
        "case_type",
        "region",
        "year",
        "requested_date",
        "authorized_date",
        "request_bp",
        "award_bp",
        "known_prior_date",
        "known_prior",
        "source_row",
    ]
    records = json.loads(frame.loc[frame.paired, columns].to_json(orient="records"))
    (output / "cases.json").write_text(
        json.dumps(
            {"schema": SCHEMA, "source": "EEI 2025 Q3", "cases": records},
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )
    for name in ("r-coefficients.csv", "r-predictions.csv", "r-decomposition.csv"):
        (output / name).unlink(missing_ok=True)
    figures(frame, summary, output)
    write_manifest(root, output)
    return summary


def verify(root=ROOT, output=None, verify_r=False):
    root = Path(root)
    output = Path(output) if output else root / OUTPUT
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Unrecognized filing-study manifest")
    for name, expected in manifest["inputs"].items():
        if digest(root / name) != expected:
            raise ValueError("Filing input changed: " + name)
    for name, expected in manifest["outputs"].items():
        if digest(output / name) != expected:
            raise ValueError("Filing output changed: " + name)
    frame, predictions, _, summary = calculate(root)
    if not numeric_equal(summary, json.loads((output / "study.json").read_text())):
        raise ValueError("Filing-study calculations do not reproduce")
    for name, expected in (("panel", frame), ("predictions", predictions)):
        actual = pd.read_csv(output / (name + ".csv"))
        if actual.id.tolist() != expected.id.tolist():
            raise ValueError("Saved case identities differ")
        columns = expected.select_dtypes(include="number").columns
        if not np.allclose(actual[columns], expected[columns], equal_nan=True, rtol=0, atol=1e-8):
            raise ValueError("Saved numeric cases differ")
    if verify_r or manifest["r_validation"] != "not_run":
        for expected_name, actual_name, keys, columns in (
            (
                "coefficients",
                "r-coefficients",
                ["model", "covariance", "term"],
                ["estimate", "se", "low", "high"],
            ),
            ("predictions", "r-predictions", ["id"], list(RULES)),
            (
                "decomposition",
                "r-decomposition",
                ["specification", "term"],
                ["request", "decision_gap", "award"],
            ),
        ):
            a, b = (
                pd.read_csv(output / (expected_name + ".csv")),
                pd.read_csv(output / (actual_name + ".csv")),
            )
            if not a[keys].equals(b[keys]) or not np.allclose(
                a[columns], b[columns], equal_nan=True, rtol=0, atol=1e-7
            ):
                raise ValueError("Native R replication differs: " + actual_name)
        if verify_r:
            write_manifest(
                root,
                output,
                "all stage models, covariance choices, coefficient identities and six prediction rules matched in native R",
            )
    return {"status": "passed", "coverage": summary["coverage"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--verify-r", action="store_true")
    args = parser.parse_args()
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
                key: result[key]
                for key in ("coverage", "prediction_metrics", "prediction_comparisons")
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
