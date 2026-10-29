"""OLS and two-way cluster covariance with explicit rank and timing checks."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import f, t


@dataclass(frozen=True)
class LinearResult:
    names: tuple
    beta: np.ndarray
    covariance: np.ndarray
    residuals: np.ndarray
    n: int
    parameters: int
    states: int
    quarters: int
    df: int
    r_squared: float
    condition_number: float
    state_covariance: np.ndarray
    quarter_covariance: np.ndarray

    def coefficients(self, terms, covariance="two_way"):
        critical = t.ppf(0.975, self.df)
        matrix = self.covariance_matrix(covariance)
        output = []
        for term in terms:
            i = self.names.index(term)
            variance = float(matrix[i, i])
            se = float(np.sqrt(variance)) if variance >= 0 else None
            estimate = float(self.beta[i])
            output.append(
                {
                    "term": term,
                    "estimate": estimate,
                    "se": se,
                    "low": estimate - critical * se if se is not None else None,
                    "high": estimate + critical * se if se is not None else None,
                    "variance_status": "available" if se is not None else "negative_unavailable",
                }
            )
        return output

    def covariance_matrix(self, name):
        choices = {
            "two_way": self.covariance,
            "state": self.state_covariance,
            "quarter": self.quarter_covariance,
        }
        if name not in choices:
            raise ValueError("Unknown covariance choice")
        return choices[name]

    def combination(self, weights):
        vector = np.zeros(len(self.names))
        for name, value in weights.items():
            vector[self.names.index(name)] = value
        estimate = float(vector @ self.beta)
        variance = float(vector @ self.covariance @ vector)
        se = float(np.sqrt(variance)) if variance >= 0 else None
        critical = t.ppf(0.975, self.df)
        return {
            "estimate": estimate,
            "se": se,
            "low": estimate - critical * se if se is not None else None,
            "high": estimate + critical * se if se is not None else None,
        }

    def joint_test(self, restrictions, covariance="two_way"):
        matrix = np.zeros((len(restrictions), len(self.names)))
        for row, restriction in enumerate(restrictions):
            for name, value in restriction.items():
                matrix[row, self.names.index(name)] = value
        covariance = matrix @ self.covariance_matrix(covariance) @ matrix.T
        if np.linalg.eigvalsh(covariance).min() <= 0:
            return {
                "statistic": None,
                "df": len(restrictions),
                "p": None,
                "status": "nonpositive_restriction_covariance",
            }
        value = matrix @ self.beta
        statistic = float(value @ np.linalg.solve(covariance, value)) / len(restrictions)
        return {
            "statistic": statistic,
            "df": len(restrictions),
            "denominator_df": self.df,
            "p": float(f.sf(statistic, len(restrictions), self.df)),
            "status": "approximate_cluster_F",
        }


def design(frame, features, effects="none"):
    if len(features) != len(set(features)):
        raise ValueError("Predictors must be unique")
    x = frame[list(features)].astype(float).copy()
    if not np.isfinite(x.to_numpy()).all() or (x.nunique() <= 1).any():
        raise ValueError("Predictors must be finite and vary in the selected sample")
    groups = {"none": [], "state_year": ["state", "year"], "entity_year": ["entity", "year"]}
    if effects not in groups:
        raise ValueError("Unknown fixed effects")
    if groups[effects]:
        x = pd.concat(
            [x, pd.get_dummies(frame[groups[effects]].astype(str), drop_first=True, dtype=float)],
            axis=1,
        )
    x.insert(0, "const", 1.0)
    return x


def fit(frame, target, features, effects="none"):
    x = design(frame, features, effects)
    return ols(x, frame[target].to_numpy(dtype=float), frame.state, frame.quarter)


def ols(x, y, state, quarter):
    matrix = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = matrix.shape
    if y.shape != (n,) or len(state) != n or len(quarter) != n:
        raise ValueError("Regression observations and clusters must align")
    if not np.isfinite(matrix).all() or not np.isfinite(y).all():
        raise ValueError("Regression inputs must be finite")
    if n <= k + 2 or np.linalg.matrix_rank(matrix) != k:
        raise ValueError("Regression lacks rank or residual degrees of freedom")
    states, state_labels = pd.factorize(state)
    quarters, quarter_labels = pd.factorize(quarter)
    if (
        min(len(state_labels), len(quarter_labels)) < 2
        or (states < 0).any()
        or (quarters < 0).any()
    ):
        raise ValueError("At least two nonmissing clusters are required in each dimension")
    beta = np.linalg.lstsq(matrix, y, rcond=None)[0]
    residuals = y - matrix @ beta
    _, triangular = np.linalg.qr(matrix, mode="reduced")
    inverse = np.linalg.solve(triangular, np.eye(k))
    bread = inverse @ inverse.T
    scores = matrix * residuals[:, None]

    def clustered(codes):
        count = int(codes.max()) + 1
        sums = np.zeros((count, k))
        np.add.at(sums, codes, scores)
        correction = count / (count - 1) * (n - 1) / (n - k)
        return correction * bread @ (sums.T @ sums) @ bread

    intersections = pd.factorize(pd.MultiIndex.from_arrays([states, quarters]))[0]
    state_covariance, quarter_covariance = clustered(states), clustered(quarters)
    covariance = state_covariance + quarter_covariance - clustered(intersections)
    total = float(np.sum((y - y.mean()) ** 2))
    if total <= 0:
        raise ValueError("The outcome must vary")
    return LinearResult(
        tuple(x.columns),
        beta,
        (covariance + covariance.T) / 2,
        residuals,
        n,
        k,
        len(state_labels),
        len(quarter_labels),
        min(len(state_labels), len(quarter_labels)) - 1,
        1 - float(residuals @ residuals) / total,
        float(np.linalg.cond(matrix)),
        state_covariance,
        quarter_covariance,
    )


def expanding_blocks(frame):
    for start in (2000, 2005, 2010, 2015, 2020):
        train = frame[(frame.year >= 1995) & (frame.year < start)]
        test = frame[frame.year.between(start, start + 4)]
        if len(train) < 100 or not len(test):
            yield start, train, test, "insufficient_history"
            continue
        if train.authorized_date.max() >= test.authorized_date.min():
            raise ValueError("Training observations must precede evaluation observations")
        yield start, train, test, "available"
