"""The prediction comparison must preserve rows, units and source identity."""


import numpy as np
import pandas as pd
import pytest

from src.prediction_audit import build, joined_predictions


def example():
    # Small synthetic software inputs; these are never part of the research outputs.
    predictions = pd.DataFrame(
        {
            "id": ["a", "b"],
            "date": ["2020-01-01", "2020-04-01"],
            "actual": [9.0, 10.0],
            "training_mean": [9.5, 9.5],
            "previous_award": [9.2, 9.8],
            "market_case": [9.4, 9.6],
            "with_prior": [9.1, 9.9],
        }
    )
    estimation = pd.DataFrame(
        {
            "id": ["a", "b"],
            "state": ["A", "B"],
            "entity": ["A / a", "B / b"],
            "quarter": ["2020Q1", "2020Q2"],
            "case_type": ["Distribution"] * 2,
            "authorized_date": predictions.date,
            "roe": [9.0, 10.0],
            "prior": [9.2, 9.8],
        }
    )
    return predictions, estimation


def test_basis_point_conversion_and_paired_sign():
    frame = joined_predictions(*example())
    assert frame.loss_previous_award.tolist() == pytest.approx([20, 20])
    assert frame.gain_bp.tolist() == pytest.approx([10, 10])


@pytest.mark.parametrize("change", ["duplicate", "unknown", "outcome", "prior", "date"])
def test_prediction_source_mismatches_are_rejected(change):
    p, e = example()
    if change == "duplicate":
        p.loc[1, "id"] = "a"
    elif change == "unknown":
        p.loc[1, "id"] = "missing"
    elif change == "outcome":
        p.loc[1, "actual"] += 0.01
    elif change == "prior":
        p.loc[1, "previous_award"] += 0.01
    else:
        p.loc[1, "date"] = "2021-04-01"
    with pytest.raises(ValueError):
        joined_predictions(p, e)


def test_nonfinite_predictions_and_nonempty_destinations_are_refused(tmp_path):
    p, e = example()
    p.loc[0, "with_prior"] = np.nan
    with pytest.raises(ValueError, match="finite"):
        joined_predictions(p, e)
    (tmp_path / "original.txt").write_text("Keep this file")
    with pytest.raises(ValueError, match="empty output"):
        build(output=tmp_path)
