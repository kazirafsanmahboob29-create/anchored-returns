"""Dated economic joins, panel associations and a fixed temporal holdout."""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, timedelta
from hashlib import sha256
import csv
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import pearsonr, spearmanr
from statsmodels.stats.sandwich_covariance import cov_cluster_2groups

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "data/external/factor_research_2026-10-26"
OUTPUT = "reports/factor-study"
SERIES = ("DGS10", "T10Y3M", "CPIAUCNS", "STLFSI4")
MARKET = ["treasury90", "curve90", "inflation", "stress"]
CASE = ["duration", "distribution"]
MAIN = MARKET + CASE + ["prior"]
LABELS = dict(
    treasury90="10-year Treasury, prior 90 days (pp)",
    treasury30="10-year Treasury, prior 30 days (pp)",
    curve90="10-year minus 3-month yield, prior 90 days (pp)",
    curve30="10-year minus 3-month yield, prior 30 days (pp)",
    inflation="CPI inflation, two-month lag (pp)",
    stress="Financial stress, 14-day lag (index)",
    duration="Filing duration (years)",
    distribution="Distribution case (0/1)",
    prior="Previous recorded award (pp)",
    request="Requested ROE (pp)",
    roe="Authorized ROE (pp)",
)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def load_series(root=ROOT):
    result = {}
    for name in SERIES:
        path = Path(root) / SOURCE / (name + "_2008_present.csv")
        meta = json.loads(path.with_suffix(".metadata.json").read_text())
        if digest(path) != meta["sha256"]:
            raise ValueError("Economic source fingerprint changed: " + name)
        records = list(csv.DictReader(path.open()))
        if not records or list(records[0]) not in (["observation_date", name], ["DATE", name]):
            raise ValueError("Unexpected series identity: " + name)
        values = []
        for row in records:
            day = row.get("observation_date", row.get("DATE"))
            date.fromisoformat(day)
            value = None if row[name] in ("", ".") else float(row[name])
            if value is not None and not np.isfinite(value):
                raise ValueError("Non-finite source value")
            values.append(dict(date=day, value=value))
        days = [r["date"] for r in values]
        if days != sorted(set(days)):
            raise ValueError("Series dates must be unique and sorted")
        result[name] = values
    return result


def average_before(records, written, window):
    """Exclude the authorization day, and reject sparse or stale windows."""
    start = (date.fromisoformat(written) - timedelta(days=window)).isoformat()
    rows = [r for r in records if start <= r["date"] < written and r["value"] is not None]
    minimum = 40 if window == 90 else 10
    if (
        len(rows) < minimum
        or (date.fromisoformat(written) - date.fromisoformat(rows[-1]["date"])).days > 7
    ):
        return None, len(rows)
    return float(np.mean([r["value"] for r in rows])), len(rows)


def month_before(written, months):
    current = date.fromisoformat(written)
    index = current.year * 12 + current.month - 1 - months
    return f"{index // 12:04d}-{index % 12 + 1:02d}-01"


def economic_join(written, series):
    result = {}
    for name, key in [("DGS10", "treasury"), ("T10Y3M", "curve")]:
        for window in (30, 90):
            result[key + str(window)], result[key + str(window) + "_n"] = average_before(
                series[name], written, window
            )
    target, prior = month_before(written, 2), month_before(written, 14)
    cpi = {r["date"]: r["value"] for r in series["CPIAUCNS"]}
    result["inflation_month"] = target
    result["inflation"] = (
        100 * (cpi[target] / cpi[prior] - 1) if cpi.get(target) and cpi.get(prior) else None
    )
    cutoff = (date.fromisoformat(written) - timedelta(days=14)).isoformat()
    candidates = [r for r in series["STLFSI4"] if r["date"] <= cutoff and r["value"] is not None]
    chosen = candidates[-1] if candidates else None
    valid = chosen and (date.fromisoformat(cutoff) - date.fromisoformat(chosen["date"])).days <= 14
    result["stress"] = chosen["value"] if valid else None
    result["stress_date"] = chosen["date"] if valid else None
    return result


def panel(records, series):
    """Keep every 2010–2024 base row; lag lookup uses the earlier table too."""
    history = defaultdict(lambda: defaultdict(list))
    for row in records:
        if row["award_bp"] is not None:
            history[(row["state"], row["utility"])][row["authorized_date"]].append(row)
    output = []
    for row in records:
        if not 2010 <= row["year"] <= 2024:
            continue
        written = row["authorized_date"]
        entity = row["state"] + " / " + row["utility"]
        dates = sorted(history[(row["state"], row["utility"])])
        # Same-day decisions share information; they cannot be each other's lag.
        index = bisect_left(dates, written) - 1
        prior_date = dates[index] if index >= 0 else None
        gap = (
            (date.fromisoformat(written) - date.fromisoformat(prior_date)).days
            if prior_date
            else None
        )
        previous = (
            history[(row["state"], row["utility"])][prior_date]
            if prior_date and gap <= 3652
            else []
        )
        requested = row["requested_date"]
        duration = (
            (date.fromisoformat(written) - date.fromisoformat(requested)).days
            if requested
            else None
        )
        valid_duration = duration is not None and 0 <= duration <= 3652
        output.append(
            dict(
                **row,
                entity=entity,
                quarter=written[:4] + "Q" + str((int(written[5:7]) - 1) // 3 + 1),
                roe=row["award_bp"] / 100 if row["award_bp"] is not None else None,
                request=row["request_bp"] / 100 if row["request_bp"] is not None else None,
                distribution=int(row["case_type"] == "Distribution"),
                duration=duration / 365.25 if valid_duration else None,
                duration_days=duration,
                prior=float(np.mean([p["award_bp"] for p in previous])) / 100 if previous else None,
                prior_date=prior_date if previous else None,
                prior_gap_days=gap if previous else None,
                prior_ids=";".join(p["id"] for p in previous),
                prior_rows=len(previous),
                **economic_join(written, series),
            )
        )
    return output


def complete(frame, features=MAIN):
    return frame.dropna(subset=["roe"] + features).copy()


def design(frame, features, effects="none"):
    x = frame[features].astype(float).copy()
    x = x.loc[:, x.nunique() > 1]
    if effects != "none":
        names = (
            ["state", "year"]
            if effects == "state_year"
            else ["entity", "year"]
            if effects == "entity_year"
            else ["year"]
        )
        x = pd.concat(
            [x, pd.get_dummies(frame[names].astype(str), drop_first=True, dtype=float)], axis=1
        )
    x = sm.add_constant(x, has_constant="add")
    if np.linalg.matrix_rank(x.to_numpy()) != x.shape[1]:
        raise ValueError("Regression design is rank deficient")
    if len(x) <= x.shape[1] + 2:
        raise ValueError("Insufficient residual degrees of freedom")
    return x


def fit(frame, features, effects="none", identifier="", title=""):
    data = complete(frame, features)
    x = design(data, features, effects)
    result = sm.OLS(data.roe, x, missing="raise").fit()
    state = pd.factorize(data.state)[0]
    quarter = pd.factorize(data.quarter)[0]
    if len(set(state)) < 2 or len(set(quarter)) < 2:
        raise ValueError("Two-way covariance requires two groups in each dimension")
    # Decisions can share both a commission and a national financial environment.
    covariance, _, _ = cov_cluster_2groups(result, state, quarter, use_correction=True)
    leverage = result.get_influence().hat_matrix_diag
    # Singleton fixed-effect cells have unit leverage: HC3 is undefined.
    hc3 = (
        result.get_robustcov_results(cov_type="HC3").bse
        if np.all(leverage < 1 - 1e-10)
        else np.full(x.shape[1], np.nan)
    )
    coefficients = []
    for i, name in enumerate(x.columns):
        if name not in features:
            continue
        variance = float(covariance[i, i])
        se = float(np.sqrt(variance)) if variance > 0 else None
        value = float(result.params.iloc[i])
        coefficients.append(
            dict(
                term=name,
                label=LABELS.get(name, name),
                estimate=value,
                se=se,
                low=value - 1.959963984540054 * se if se else None,
                high=value + 1.959963984540054 * se if se else None,
                hc3_se=float(hc3[i]) if np.isfinite(hc3[i]) else None,
                variance_status="positive" if se else "nonpositive_unavailable",
            )
        )
    return dict(
        id=identifier,
        title=title,
        effects=effects,
        features=features,
        n=len(data),
        parameters=x.shape[1],
        states=data.state.nunique(),
        entities=data.entity.nunique(),
        quarters=data.quarter.nunique(),
        r2=float(result.rsquared),
        adjusted_r2=float(result.rsquared_adj),
        condition_number=float(result.condition_number),
        coefficients=coefficients,
        unit_leverage_rows=int(np.sum(leverage >= 1 - 1e-10)),
        rows=data.id.tolist(),
        covariance="Two-way state and authorization-quarter clusters; finite-sample correction; 95% normal Wald intervals",
    )


def correlations(frame):
    output = []
    names = ["roe"] + MAIN + ["request"]
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            pair = frame[[a, b]].dropna()
            valid = len(pair) >= 3 and pair[a].nunique() > 1 and pair[b].nunique() > 1
            output.append(
                dict(
                    x=a,
                    y=b,
                    n=len(pair),
                    pearson=float(pearsonr(pair[a], pair[b]).statistic) if valid else None,
                    spearman=float(spearmanr(pair[a], pair[b]).statistic) if valid else None,
                )
            )
    return output


def holdout(frame):
    # Fit once on the earlier period. Test-period outcomes never update coefficients.
    train = frame[frame.year <= 2019]
    test = frame[frame.year >= 2020]
    predictions = dict(
        training_mean=np.full(len(test), train.roe.mean()), previous_award=test.prior.to_numpy()
    )
    for name, features in [("market_case", MARKET + CASE), ("with_prior", MAIN)]:
        x = design(train, features)
        result = sm.OLS(train.roe, x).fit()
        predictions[name] = result.predict(
            sm.add_constant(test[features].astype(float), has_constant="add")[x.columns]
        ).to_numpy()
    output = []
    for name, predicted in predictions.items():
        # ROE is stored in percentage points; report prediction error in basis points.
        errors = (test.roe.to_numpy() - predicted) * 100
        output.append(
            dict(
                model=name,
                train_n=len(train),
                test_n=len(test),
                mae_bp=float(np.mean(abs(errors))),
                rmse_bp=float(np.sqrt(np.mean(errors**2))),
            )
        )
    rows = [
        dict(
            id=row.id,
            date=row.authorized_date,
            actual=row.roe,
            **{name: float(values[i]) for name, values in predictions.items()},
        )
        for i, row in enumerate(test.itertuples())
    ]
    return dict(train_years=[2010, 2019], test_years=[2020, 2024], metrics=output, predictions=rows)


def differences(frame):
    by_id = {r["id"]: r for r in frame.to_dict("records")}
    output = []
    for row in frame.to_dict("records"):
        ids = row["prior_ids"].split(";")
        previous = [by_id[i] for i in ids if i in by_id]
        if len(previous) != len(ids) or not previous:
            continue
        changed = {}
        for name in ["roe"] + MARKET + ["duration"]:
            values = [r[name] for r in previous]
            changed[name] = (
                row[name] - float(np.mean(values))
                if pd.notna(row[name]) and all(pd.notna(v) for v in values)
                else None
            )
        output.append(
            dict(
                id=row["id"],
                state=row["state"],
                entity=row["entity"],
                year=row["year"],
                quarter=row["quarter"],
                **changed,
            )
        )
    return pd.DataFrame(output)


def write_csv(path, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(root=ROOT):
    root = Path(root)
    national = json.loads((root / "reports/national-study/study.json").read_text())
    if any(digest(root / name) != value for name, value in national["input_sha256"].items()):
        raise ValueError("National inputs changed; rebuild the national study first")
    series = load_series(root)
    records = panel(national["records"], series)
    frame = pd.DataFrame(records)
    common = complete(frame)
    models = [
        fit(common, MARKET + CASE, identifier="market_case", title="Market and case variables"),
        fit(common, MAIN, identifier="with_prior", title="Add prior award"),
        fit(common, MAIN, "state_year", "state_year", "State and year controls"),
        fit(common, MAIN, "entity_year", "entity_year", "Utility-state and year controls"),
    ]
    sensitivity = []
    short = common.copy()
    short["treasury90"] = short["treasury30"]
    short["curve90"] = short["curve30"]
    sensitivity.append(fit(short, MAIN, "state_year", "window30", "30-day market window"))
    ne = {"Connecticut", "Maine", "Massachusetts", "New Hampshire", "Rhode Island", "Vermont"}
    sensitivity.append(
        fit(common[~common.state.isin(ne)], MAIN, "state_year", "outside_NE", "Omit New England")
    )
    sensitivity.append(
        fit(
            common[common.distribution == 1],
            MAIN,
            "state_year",
            "distribution",
            "Distribution cases",
        )
    )
    paired = common.dropna(subset=["request"])
    sensitivity.append(
        fit(paired, MAIN, "state_year", "request_sample", "Request-pair sample, without request")
    )
    sensitivity.append(
        fit(paired, MAIN + ["request"], "state_year", "with_request", "Add requested ROE")
    )
    diff = differences(frame)
    sensitivity.append(
        fit(diff, MARKET + ["duration"], "none", "changes", "Changes within utility-state")
    )
    sensitivity.append(
        fit(diff, MARKET + ["duration"], "year", "changes_year", "Changes with year controls")
    )
    output = root / OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    credits = json.loads((root / SOURCE / "publication_allowlist.json").read_text())
    source_records = [
        json.loads((root / SOURCE / (name + "_2008_present.metadata.json")).read_text())
        for name in SERIES
    ]
    snapshot = dict(
        schema="anchored-returns-factor-snapshot/1",
        id="archived-2026-10-26",
        retrieved_at_utc=max(r["retrieved_at_utc"] for r in source_records),
        vintage="October 26, 2026 current historical vintage; not as-known at authorization",
        series=series,
        sources=source_records,
        source_credits=credits["source_credits"],
        bls_check=credits["bls_cpi_validation"],
    )
    (output / "macro.json").write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")
    write_csv(output / "panel.csv", records)
    common.to_csv(output / "estimation.csv", index=False)
    diff.to_csv(output / "changes.csv", index=False)
    stata = frame.copy()
    for column in stata.select_dtypes(include=["object", "str"]).columns:
        stata[column] = stata[column].fillna("").astype(str)
    stata.to_stata(output / "panel.dta", write_index=False, version=118)
    inputs = [
        "reports/national-study/study.json",
        "src/factor_study.py",
        "docs/factor_analysis_plan_v0.1.0.md",
        "analysis/factors.R",
        "analysis/factors.do",
        "presentation/factors/compute.mjs",
    ]
    inputs += [
        SOURCE + "/" + name + "_2008_present" + suffix
        for name in SERIES
        for suffix in (".csv", ".metadata.json")
    ]
    result = dict(
        schema="anchored-returns-factors/1",
        title="Market conditions and persistence in authorized utility returns",
        date="2026-10-26",
        case_vintage="EEI 2025 Q3",
        macro_vintage="2026-10-26",
        years=[2010, 2024],
        input_sha256={name: digest(root / name) for name in inputs},
        labels=LABELS,
        coverage=dict(
            entries=len(frame),
            awards=int(frame.roe.notna().sum()),
            complete=len(common),
            excluded=len(frame) - len(common),
            states=common.state.nunique(),
            entities=common.entity.nunique(),
            quarters=common.quarter.nunique(),
            missing={name: int(frame[name].isna().sum()) for name in ["roe"] + MAIN},
            multiple_prior_rows=int((common.prior_rows > 1).sum()),
        ),
        models=models,
        sensitivity=sensitivity,
        correlations=correlations(frame),
        common_correlations=correlations(common),
        holdout=holdout(common),
        records=records,
        definitions=dict(
            plan="docs/factor_analysis_plan_v0.1.0.md",
            prior="Exact utility label and state; strictly earlier date within ten years; prior same-date entries averaged",
            macro="Current historical vintage with observation-date lags, not an as-known vintage",
            inference="Associations conditional on selected variables; no causal identification design",
        ),
    )
    (output / "study.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    coef = [
        dict(model=model["id"], n=model["n"], **coefficient)
        for model in models + sensitivity
        for coefficient in model["coefficients"]
    ]
    write_csv(output / "coefficients.csv", coef)
    write_csv(output / "correlations.csv", result["correlations"])
    write_csv(output / "holdout.csv", result["holdout"]["predictions"])
    return result


def package(root=ROOT):
    root = Path(root)
    directory = root / OUTPUT
    expected = pd.read_csv(directory / "coefficients.csv")
    independent = pd.read_csv(directory / "r-crosscheck.csv")
    if len(independent) != 27:
        raise ValueError("Native R crosscheck is incomplete")
    for row in independent.itertuples():
        reference = expected[(expected.model == row.model) & (expected.term == row.term)].iloc[0]
        if abs(row.estimate - reference.estimate) > 1e-7 or abs(row.se - reference.se) > 1e-7:
            raise ValueError("Native R crosscheck does not match Python")
    manifest = dict(
        schema="anchored-returns-factor-artifacts/1",
        r_validation="27 coefficients and two-way clustered standard errors match within 1e-7",
        stata="Native syntax supplied, execution unverified",
        files={
            p.name: digest(p)
            for p in directory.glob("*")
            if p.is_file() and p.name not in ("artifact-manifest.json", "factor-study.zip")
        },
    )
    (directory / "artifact-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with ZipFile(root / OUTPUT / "factor-study.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted((root / OUTPUT).glob("*")):
            if path.is_file() and path.suffix != ".zip":
                archive.write(path, str(path.relative_to(root)))
        for name in [
            "src/factor_study.py",
            "src/__init__.py",
            "docs/factor_analysis_plan_v0.1.0.md",
            "docs/factor_study.md",
            "docs/dartmouth_portfolio.md",
            "analysis/factors.R",
            "analysis/factors.do",
            "pyproject.toml",
            "requirements-lock.txt",
        ]:
            archive.write(root / name, name)
        for name in SERIES:
            for suffix in (".csv", ".metadata.json"):
                path = SOURCE + "/" + name + "_2008_present" + suffix
                archive.write(root / path, path)
        for name in [
            "data/external/eei/source.json",
            "data/external/eei/eei_rate_review_2025_q3.xlsx",
            "reports/national-study/study.json",
            "data/external/eei/electric_observations.csv",
        ]:
            archive.write(root / name, name)
        national = json.loads((root / "reports/national-study/study.json").read_text())
        for name in [*national["input_sha256"], SOURCE + "/publication_allowlist.json"]:
            if name not in archive.namelist():
                archive.write(root / name, name)
        archive.write(root / "presentation/factors/compute.mjs", "presentation/factors/compute.mjs")
        for path in (root / "data/external/bls_cpi/2026-10-26").glob("*.json"):
            archive.write(path, str(path.relative_to(root)))
        archive.writestr(
            "README.md",
            "# Reproduction\n\nInstall Python 3.11+ and the dependencies with `python -m pip install -e .`. Run `python -m src.factor_study`, then `Rscript analysis/factors.R reports/factor-study`. Inputs include the original EEI workbook, the national normalized records, all hashed national inputs, and four attributed economic histories. The R script checks coefficients and clustered standard errors against Python before drawing the figures. Native Stata syntax is provided but has not been executed. No original-order PDFs or API keys are required.\n",
        )


def render_article(root, template):
    root = Path(root)
    data = json.loads((root / OUTPUT / "study.json").read_text())
    if any(digest(root / name) != value for name, value in data["input_sha256"].items()):
        raise ValueError("Factor inputs changed; run research factors")
    artifact = json.loads((root / OUTPUT / "artifact-manifest.json").read_text())
    if any(digest(root / OUTPUT / name) != value for name, value in artifact["files"].items()):
        raise ValueError("Factor outputs changed; rerun checks and package")
    models = data["models"]
    by_id = {m["id"]: m for m in models}
    coefficient = lambda model, term: next(
        c for c in by_id[model]["coefficients"] if c["term"] == term
    )
    correlations = next(
        r for r in data["common_correlations"] if r["x"] == "roe" and r["y"] == "prior"
    )
    values = dict(
        FACTOR_N=str(data["coverage"]["complete"]),
        FACTOR_ENTRIES=str(data["coverage"]["entries"]),
        FACTOR_AWARDS=str(data["coverage"]["awards"]),
        FACTOR_EXCLUDED=str(data["coverage"]["excluded"]),
        FACTOR_STATES=str(data["coverage"]["states"]),
        FACTOR_ENTITIES=str(data["coverage"]["entities"]),
        PRIOR_R=f"{correlations['pearson']:.2f}",
        TREASURY_POOLED=f"{coefficient('market_case', 'treasury90')['estimate'] * 100:.1f}",
        TREASURY_ADJUSTED=f"{coefficient('state_year', 'treasury90')['estimate'] * 100:.1f}",
        PRIOR_ADJUSTED=f"{coefficient('state_year', 'prior')['estimate'] * 100:.1f}",
    )
    values["FACTOR_TABLE"] = "".join(
        "<tr><td>"
        + m["title"]
        + "</td>"
        + "".join(
            "<td>"
            + f"{coefficient(m['id'], term)['estimate']:.3f}"
            + "<small>"
            + f"[{coefficient(m['id'], term)['low']:.3f}, {coefficient(m['id'], term)['high']:.3f}]"
            + "</small></td>"
            for term in ("treasury90", "prior")
            if any(c["term"] == term for c in m["coefficients"])
        )
        + (" <td>Not included</td>" if m["id"] == "market_case" else "")
        + "<td>"
        + f"{m['r2']:.3f}"
        + "</td></tr>"
        for m in models
    )
    labels = dict(
        training_mean="Training-period mean",
        previous_award="Previous recorded award",
        market_case="Market and case model",
        with_prior="Model with previous award",
    )
    values["HOLDOUT_TABLE"] = "".join(
        "<tr><td>"
        + labels[m["model"]]
        + "</td><td>"
        + f"{m['mae_bp']:.1f}"
        + "</td><td>"
        + f"{m['rmse_bp']:.1f}"
        + "</td></tr>"
        for m in data["holdout"]["metrics"]
    )
    for key, value in values.items():
        template = template.replace("__" + key + "__", value)
    return template


if __name__ == "__main__":
    result = build()
    print(json.dumps({key: result[key] for key in ["coverage", "models", "holdout"]}, indent=2))
