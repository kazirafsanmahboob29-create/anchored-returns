"""Check the NumPy implementation against a separate statistical library."""

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy.stats import t
from statsmodels.stats.sandwich_covariance import cov_cluster, cov_cluster_2groups

from src.panel_models import design, expanding_blocks, ols


@pytest.fixture
def observations():
    rng = np.random.default_rng(816)
    state = np.repeat(np.arange(30), 20)
    quarter = np.tile(np.arange(20), 30)
    x = pd.DataFrame({"const": 1.0, "a": rng.normal(size=600), "b": rng.normal(size=600)})
    y = (
        x.to_numpy() @ np.array([9.0, 0.2, -0.1])
        + rng.normal(size=30)[state]
        + rng.normal(size=20)[quarter]
        + rng.normal(size=600)
    )
    return x, y, state, quarter


def test_numpy_ols_and_covariance_match_statsmodels(observations):
    x, y, state, quarter = observations
    ours = ols(x, y, state, quarter)
    reference = sm.OLS(y, x).fit()
    covariance, _, _ = cov_cluster_2groups(reference, state, quarter, use_correction=True)
    assert ours.beta == pytest.approx(reference.params.to_numpy(), abs=1e-12)
    assert ours.covariance == pytest.approx(covariance, abs=1e-12)
    coefficient = ours.coefficients(["a"])[0]
    assert coefficient["low"] == pytest.approx(
        ours.beta[1] - t.ppf(0.975, 19) * np.sqrt(covariance[1, 1])
    )
    assert ours.df == 19
    assert ours.state_covariance == pytest.approx(cov_cluster(reference, state), abs=1e-12)
    assert ours.quarter_covariance == pytest.approx(cov_cluster(reference, quarter), abs=1e-12)


@pytest.mark.parametrize("problem", ["rank", "nonfinite", "clusters", "alignment"])
def test_invalid_regressions_fail_explicitly(observations, problem):
    x, y, state, quarter = observations
    if problem == "rank":
        x["duplicate"] = x.a
    elif problem == "nonfinite":
        y[0] = np.nan
    elif problem == "clusters":
        state[:] = 0
    else:
        y = y[:-1]
    with pytest.raises(ValueError):
        ols(x, y, state, quarter)


def test_joint_restriction_uses_covariance_of_the_difference(observations):
    result = ols(*observations)
    contrast = np.array([0, 1, -1])
    expected = (contrast @ result.beta) ** 2 / (contrast @ result.covariance @ contrast)
    test = result.joint_test([{"a": 1, "b": -1}])
    assert test["statistic"] == pytest.approx(expected)
    assert 0 <= test["p"] <= 1 and test["denominator_df"] == 19
    combination = result.combination({"a": 1, "b": -1})
    assert combination["estimate"] == pytest.approx(contrast @ result.beta)
    assert combination["se"] == pytest.approx(np.sqrt(contrast @ result.covariance @ contrast))


def test_fixed_effects_do_not_silently_remove_collinearity():
    d = pd.DataFrame({"x": [0, 0, 1, 1], "state": ["A", "A", "B", "B"], "year": [2000, 2001] * 2})
    x = design(d, ["x"], "state_year")
    with pytest.raises(ValueError, match="rank"):
        ols(x, np.arange(4.0), d.state, ["Q1", "Q2"] * 2)


def test_expanding_blocks_never_train_on_their_evaluation_years():
    d = pd.DataFrame({"year": np.repeat(np.arange(1995, 2025), 25)})
    d["authorized_date"] = d.year.astype(str) + "-06-30"
    for start, train, test, status in expanding_blocks(d):
        assert status == "available"
        assert train.year.max() == start - 1
        assert test.year.min() == start and test.year.max() == start + 4
        assert train.authorized_date.max() < test.authorized_date.min()
