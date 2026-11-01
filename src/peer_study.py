"""Dated, other-state peer comparisons and review of saved prediction errors."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_cluster_2groups

from .filing_study import FORECAST_FEATURES, ROOT, loss_comparison
from .panel_models import design, ols

OUTPUT = Path("reports/peer-study")
PLAN = Path("docs/research_review_2026-10-30.md")
BASE = [
    "known_prior",
    "filing_treasury90",
    "filing_inflation",
    "filing_unemployment",
    "distribution",
]


def peer_windows(frame, months=12, min_awards=10, min_states=5):
    """Use calendar months, strict filing cutoffs and no own-state awards."""
    if months not in (6, 12):
        raise ValueError("Only the specified six- and twelve-month windows are supported")
    awards = frame[frame.award.notna()].copy()
    awards["day"] = pd.to_datetime(awards.authorized_date)
    records = []
    for row in frame.itertuples():
        filing = pd.to_datetime(row.requested_date, errors="coerce")
        selected = awards.iloc[:0]
        if not pd.isna(filing):
            selected = awards[
                (awards.state != row.state)
                & (awards.day >= filing - pd.DateOffset(months=months))
                & (awards.day < filing)
            ]
        enough = len(selected) >= min_awards and selected.state.nunique() >= min_states
        # One state/date receives one unit of weight even with several utility rows.
        day_means = selected.groupby(["state", "authorized_date"]).award.mean()
        records.append(
            {
                "id": row.id,
                f"peer{months}": float(day_means.mean()) if enough else np.nan,
                f"peer{months}_row": float(selected.award.mean()) if enough else np.nan,
                f"peer{months}_n": len(selected),
                f"peer{months}_states": selected.state.nunique(),
                f"peer{months}_dates": len(day_means),
                f"peer{months}_last": selected.authorized_date.max() if len(selected) else "",
                f"peer{months}_ids": ";".join(sorted(selected.id)) if len(selected) else "",
            }
        )
    return pd.DataFrame(records).set_index("id")


def model_design(frame, features, effects):
    if effects == "state_year":
        return design(frame, features, effects)
    if effects not in ("state", "state_trend"):
        raise ValueError("Unknown peer specification")
    x = design(frame, features)
    state = pd.get_dummies(frame.state, prefix="state", drop_first=True, dtype=float)
    x = pd.concat([x, state], axis=1)
    if effects == "state_trend":
        x["trend"] = frame.year - 1985
    return x


def estimate(frame):
    common = frame[frame.prior_eligible & frame.peer12.notna()].copy()
    specs = []
    for effects in ("state", "state_trend", "state_year"):
        specs.extend(
            (
                ("baseline_" + effects, common, None, effects),
                ("peer12_" + effects, common, "peer12", effects),
            )
        )
    specs.append(("peer12_row_state", common, "peer12_row", "state"))
    six = common[common.peer6.notna()]
    specs.extend(
        (("peer12_six_common", six, "peer12", "state"), ("peer6_six_common", six, "peer6", "state"))
    )
    coefficients, coverage = [], []
    for name, selected, peer, effects in specs:
        features = BASE + ([peer] if peer else [])
        x = model_design(selected, features, effects)
        model = ols(x, selected.award.to_numpy(), selected.state, selected.quarter)
        # A separate library checks the fitted slopes and cluster implementation.
        reference = sm.OLS(selected.award, x).fit()
        covariance = cov_cluster_2groups(
            reference, pd.factorize(selected.state)[0], pd.factorize(selected.quarter)[0]
        )[0]
        if not (
            np.allclose(model.beta, reference.params, atol=1e-9, rtol=0)
            and np.allclose(model.covariance, covariance, atol=1e-8, rtol=0)
        ):
            raise ValueError("Peer regression differs from statsmodels")
        coefficients.extend({"model": name, **r} for r in model.coefficients(features))
        coverage.append(
            {
                "model": name,
                "n": len(selected),
                "states": model.states,
                "parameters": model.parameters,
                "r_squared": model.r_squared,
                "condition_number": model.condition_number,
                "features": ";".join(features),
                "effects": effects,
            }
        )
    return common, pd.DataFrame(coefficients), pd.DataFrame(coverage)


def predictions(frame):
    eligible = frame[frame.forecast_eligible & frame.peer12.notna()]
    records, blocks = [], []
    for start, end in ((2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2022)):
        cutoff = f"{start}-01-01"
        train = eligible[eligible.authorized_date < cutoff]
        test = eligible[eligible.filing_year.between(start, end)]
        block = {
            "block": f"{start}-{end}",
            "training_n": len(train),
            "n": len(test),
            "status": "available",
        }
        blocks.append(block)
        if len(train) < 100 or not len(test):
            block["status"] = "insufficient_history"
            continue
        if not (
            (train.authorized_date < cutoff).all()
            and (test.known_prior_date < test.requested_date).all()
            and (test.peer12_last < test.requested_date).all()
        ):
            raise ValueError("Prediction dates overlap unavailable information")
        values = {"prior": test.known_prior.to_numpy()}
        for name, features in (
            ("market_prior", FORECAST_FEATURES),
            ("with_request", FORECAST_FEATURES + ["request"]),
            ("market_peer", FORECAST_FEATURES + ["peer12"]),
        ):
            try:
                x = design(train, features)
                if np.linalg.matrix_rank(x) != x.shape[1]:
                    raise ValueError("Training design lacks rank")
                xp = test[features].astype(float).copy()
                xp.insert(0, "const", 1.0)
                beta = np.linalg.lstsq(x, train.award, rcond=None)[0]
                values[name] = xp.to_numpy() @ beta
            except ValueError as error:
                block["status"] = "unavailable_training_design"
                block["reason"] = str(error)
                break
        if block["status"] != "available":
            continue
        row = test[["id", "state", "quarter", "requested_date", "authorized_date"]].copy()
        row["block"] = block["block"]
        row["actual"] = test.award
        for name, value in values.items():
            row[name] = value
            row["loss_" + name] = 100 * np.abs(value - row.actual)
        records.append(row)
        block["mae"] = {k: float(row["loss_" + k].mean()) for k in values}
    result = pd.concat(records, ignore_index=True)
    comparisons = [loss_comparison(result, "market_peer", b) for b in ("prior", "market_prior")]
    return result, blocks, comparisons


def recent_block(saved, panel):
    """Post hoc timing descriptions, not an identified monetary-policy shock."""
    recent = saved[saved.block == "2020-2022"].merge(
        panel[["id", "update_treasury90", "award_change"]], on="id", validate="one_to_one"
    )
    records = []
    selections = [
        ("all_2020_2022_filings", recent),
        ("decided_before_2022_03_16", recent[recent.authorized_date < "2022-03-16"]),
        ("decided_on_or_after_2022_03_16", recent[recent.authorized_date >= "2022-03-16"]),
    ]
    for label, part in selections:
        records.append(
            {
                "selection": label,
                "n": len(part),
                "decision_start": part.authorized_date.min(),
                "decision_end": part.authorized_date.max(),
                "mean_treasury_update_pp": float(part.update_treasury90.mean()),
                "mean_award_change_bp": float(100 * part.award_change.mean()),
                **{
                    k + "_mae_bp": float(part["loss_" + k].mean())
                    for k in ("prior", "market_prior", "with_request")
                },
            }
        )
    return records


def build(root=ROOT):
    root = Path(root)
    frame = pd.read_csv(root / "reports/filing-study/panel.csv")
    if frame.id.duplicated().any():
        raise ValueError("Duplicate case identities")
    for months in (6, 12):
        frame = frame.join(peer_windows(frame, months), on="id", validate="one_to_one")
    common, coefficients, models = estimate(frame)
    forecast, blocks, comparisons = predictions(frame)
    saved = pd.read_csv(root / "reports/filing-study/predictions.csv")
    worst = saved.sort_values(["loss_with_request", "id"], ascending=[False, True]).head(5)
    worst = worst.merge(
        frame[["id", "utility", "docket", "source_row"]], on="id", validate="one_to_one", sort=False
    )
    output = root / OUTPUT
    output.mkdir(exist_ok=True, parents=True)
    frame.to_csv(output / "panel.csv", index=False)
    coefficients.to_csv(output / "coefficients.csv", index=False)
    models.to_csv(output / "models.csv", index=False)
    forecast.to_csv(output / "predictions.csv", index=False)
    pd.DataFrame(comparisons).to_csv(output / "prediction_comparisons.csv", index=False)
    worst.to_csv(output / "five-misses.csv", index=False)
    summary = {
        "schema": "anchored-returns-peer-study/1",
        "date": "2026-10-30",
        "status": "post-review extension",
        "coverage": {
            "eligible_prior": int(frame.prior_eligible.sum()),
            "peer12_common": len(common),
            "peer6_common": int(common.peer6.notna().sum()),
            "predictions": len(forecast),
        },
        "prior_peer_correlation": float(common.known_prior.corr(common.peer12)),
        "prediction_mae_bp": {
            key: float(forecast["loss_" + key].mean())
            for key in ("prior", "market_prior", "with_request", "market_peer")
        },
        "coefficients": coefficients.to_dict(orient="records"),
        "models": models.to_dict(orient="records"),
        "prediction_blocks": blocks,
        "prediction_comparisons": comparisons,
        "recent_filing_block": recent_block(saved, frame),
        "recent_decision_years": saved[saved.block == "2020-2022"]
        .authorized_date.str[:4]
        .value_counts()
        .sort_index()
        .to_dict(),
        "inputs": {
            str(p): hashlib.sha256((root / p).read_bytes()).hexdigest()
            for p in (
                PLAN,
                Path("src/peer_study.py"),
                Path("analysis/peer.R"),
                Path("src/panel_models.py"),
                Path("src/filing_study.py"),
                Path("reports/filing-study/panel.csv"),
                Path("reports/filing-study/predictions.csv"),
            )
        },
    }
    (output / "study.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return summary


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = build()
    print(
        json.dumps(
            {k: result[k] for k in ("coverage", "prediction_comparisons", "recent_filing_block")},
            indent=2,
        )
    )
