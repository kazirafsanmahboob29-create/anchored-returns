"""Check filing chronology, weighted inference and the recorded-stage identity."""

import json

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_cluster_2groups

from scripts.fetch_filing_sources import acquire
from src.filing_study import (
    FORECAST_FEATURES,
    ROOT,
    RULES,
    STAGE_FEATURES,
    fit_stage,
    make_panel,
)
from src.panel_models import design


class ExampleHistory:
    def __init__(self):
        self.states = {"A": {"region": "South"}}

    def join(self, days, states):
        # Timing fixture only. These rows are never saved as research data.
        return pd.DataFrame(
            {
                key: np.arange(len(days), dtype=float)
                for key in ("treasury90", "inflation", "unemployment")
            }
        )


def case(identifier, filing, decision, award):
    return {
        "id": identifier,
        "state": "A",
        "utility": "Example utility",
        "year": int(decision[:4]),
        "requested_date": filing,
        "authorized_date": decision,
        "award_bp": award,
        "request_bp": 1050,
        "docket": identifier,
        "case_type": "Distribution",
    }


def test_known_prior_excludes_decisions_during_the_proceeding_and_same_day():
    rows = [
        case("old-a", "1993-01-01", "1994-01-01", 950),
        case("old-b", "1993-02-01", "1994-01-01", 1050),
        case("same-day", "1994-01-01", "1995-01-01", 1100),
        case("pending-update", "1995-01-01", "1996-01-01", 1200),
        case("target", "1995-01-01", "1997-01-01", 1000),
    ]
    d = make_panel(rows, ExampleHistory()).set_index("id")
    assert d.loc["target", "known_prior_ids"] == "old-a;old-b"
    assert d.loc["target", "known_prior"] == 10
    assert d.loc["target", "decision_prior_ids"] == "pending-update"
    assert d.loc["target", "prior_changed_at_filing"]
    assert d.loc["target", "known_prior_date"] < d.loc["target", "requested_date"]


def test_stale_and_invalid_filing_dates_are_not_filled():
    rows = [
        case("old", "1981-01-01", "1982-01-01", 1000),
        case("stale", "1995-01-01", "1996-01-01", 1100),
        case("invalid", "1999-01-01", "1998-01-01", 1050),
    ]
    d = make_panel(rows, ExampleHistory()).set_index("id")
    assert pd.isna(d.loc["stale", "known_prior"])
    assert not d.loc["invalid", "filing_valid"]
    assert not d.loc["invalid", "paired"]


def numerical_fixture():
    rng = np.random.default_rng(41)
    n = 240
    d = pd.DataFrame(
        {
            "state": np.tile(list("ABCDEF"), 40),
            "quarter": np.repeat([f"Q{x}" for x in range(12)], 20),
            "year": np.repeat([2000, 2001, 2002, 2003], 60),
            "x": rng.normal(size=n),
            "z": rng.normal(size=n),
        }
    )
    d["entity"] = d.state
    d["decision_group"] = [f"g{x // 3}" for x in range(n)]
    d.loc[d.index % 7 == 0, "decision_group"] = [f"solo{x}" for x in d.index[d.index % 7 == 0]]
    d["request"] = 2 + 0.7 * d.x + rng.normal(size=n)
    d["gap"] = -0.4 + 0.2 * d.x - 0.3 * d.z + rng.normal(size=n)
    d["award"] = d.request + d.gap
    d["decision_day_group"] = d.decision_group
    return d


def test_decision_day_weighted_covariance_matches_statsmodels_wls():
    d = numerical_fixture()
    x = design(d, ["x", "z"], "state_year")
    w = 1 / d.groupby("decision_group").x.transform("size")
    expected = sm.WLS(d.award, x, weights=w).fit()
    actual = fit_stage(d, "award", ["x", "z"], "state_year", "decision_days")
    reference = cov_cluster_2groups(expected, pd.factorize(d.state)[0], pd.factorize(d.quarter)[0])[
        0
    ]
    assert np.allclose(actual.beta, expected.params, atol=1e-11, rtol=0)
    assert np.allclose(actual.covariance, reference, atol=1e-11, rtol=0)


@pytest.mark.parametrize("weight", ["rows", "decision_days"])
def test_stage_identity_holds_for_every_coefficient(weight):
    d = numerical_fixture()
    results = [
        fit_stage(d, target, ["x", "z"], "state_year", weight)
        for target in ("request", "gap", "award")
    ]
    assert np.allclose(results[2].beta, results[0].beta + results[1].beta, atol=1e-12, rtol=0)


def test_real_cases_and_prediction_dates_preserve_information_order():
    d = pd.read_csv(ROOT / "reports/filing-study/panel.csv")
    paired = d[d.paired]
    assert len(paired) == 1785 and not d.id.duplicated().any()
    assert np.allclose(paired.award_bp - paired.request_bp, paired.decision_gap * 100)
    p = pd.read_csv(ROOT / "reports/filing-study/predictions.csv")
    assert not p.id.duplicated().any()
    assert (p.last_training_decision < p.requested_date).all()
    assert (p.known_prior_date < p.requested_date).all()
    assert (p.last_training_decision < p.training_cutoff).all()
    assert "duration" not in FORECAST_FEATURES
    assert not any(k.startswith(("update_", "decision_")) for k in FORECAST_FEATURES)
    for key in RULES:
        assert np.allclose(p["loss_" + key], abs(p[key] - p.actual) * 100)


def test_saved_identity_and_portable_exports_are_numeric_checks():
    decomposition = pd.read_csv(ROOT / "reports/filing-study/decomposition.csv")
    assert np.allclose(
        decomposition.award, decomposition.request + decomposition.decision_gap, atol=1e-9, rtol=0
    )
    for name in ("paired", "stage", "known-prior"):
        source = pd.read_csv(ROOT / f"reports/filing-study/{name}.csv")
        restored = pd.read_stata(
            ROOT / f"reports/filing-study/{name}.dta", convert_categoricals=False
        )
        assert source.id.tolist() == restored.id.tolist()
        cols = source.select_dtypes(include="number").columns
        assert np.allclose(source[cols], restored[cols], equal_nan=True, atol=1e-12, rtol=0)
    summary = json.loads((ROOT / "reports/filing-study/study.json").read_text())
    assert summary["coverage"]["stage_complete"] > 759
    assert len(summary["prediction_blocks"]) == 5
    assert len(STAGE_FEATURES) == len(set(STAGE_FEATURES))


def test_supplemental_archive_checks_hashes_without_a_network_request(tmp_path, monkeypatch):
    folder = tmp_path / "data/external/filing_2026-10-30"
    folder.mkdir(parents=True)
    for name in ("manifest.json", "ALUR.csv"):
        (folder / name).write_bytes((ROOT / "data/external/filing_2026-10-30" / name).read_bytes())

    def unexpected_request(*args, **kwargs):
        raise AssertionError("A complete cached archive should not fetch another vintage")

    monkeypatch.setattr("scripts.fetch_filing_sources.requests.get", unexpected_request)
    assert acquire(tmp_path)["series_id"] == "ALUR"
    (folder / "ALUR.csv").write_text("changed source bytes")
    with pytest.raises(ValueError, match="fingerprint"):
        acquire(tmp_path)


def test_prediction_sensitivity_uses_the_saved_errors_without_refitting():
    p = pd.read_csv(ROOT / "reports/filing-study/predictions.csv")
    checks = pd.read_csv(ROOT / "reports/filing-study/prediction_sensitivity.csv")
    selected = p[~np.isclose(p.request, p.actual, rtol=0, atol=1e-10)]
    row = checks[checks.selection == "nonzero_request_award_gap"].iloc[0]
    assert row.n == len(selected)
    assert row.estimate == pytest.approx((selected.loss_prior - selected.loss_with_request).mean())
    omission = pd.read_csv(ROOT / "reports/filing-study/prediction_state_omission.csv")
    assert set(omission.omitted_state) == set(p.state)
    for row in omission.itertuples():
        sample = p[p.state != row.omitted_state]
        assert row.n == len(sample)
        assert row.estimate == pytest.approx((sample.loss_prior - sample.loss_with_request).mean())
