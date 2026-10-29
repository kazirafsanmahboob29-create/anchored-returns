"""The prediction comparison must preserve rows, units and source identity."""

import json

import numpy as np
import pandas as pd
import pytest

from src.prediction_audit import build, comparison, joined_predictions, load_inputs, verify


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


def test_real_saved_prediction_comparison():
    frame = load_inputs()
    result = comparison(frame)
    assert (result["n"], result["states"], result["quarters"]) == (188, 42, 20)
    assert result["improvement_bp"] == pytest.approx(0.908849383674961, abs=1e-10)
    assert result["se_bp"] == pytest.approx(1.4286351725369446, abs=1e-10)
    assert result["low_bp"] < 0 < result["high_bp"]
    assert (result["candidate_wins"], result["reference_wins"], result["ties"]) == (86, 102, 0)
    frame["state"] = "One group"
    with pytest.raises(ValueError, match="two states"):
        comparison(frame)


def test_export_fingerprints_detect_changed_results(tmp_path):
    build(output=tmp_path)
    assert verify(output=tmp_path)["status"] == "passed"
    p = tmp_path / "summary.json"
    summary = json.loads(p.read_text())
    summary["observations"] = 999
    p.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="output changed"):
        verify(output=tmp_path)


def test_nonfinite_predictions_and_nonempty_destinations_are_refused(tmp_path):
    p, e = example()
    p.loc[0, "with_prior"] = np.nan
    with pytest.raises(ValueError, match="finite"):
        joined_predictions(p, e)
    (tmp_path / "original.txt").write_text("Keep this file")
    with pytest.raises(ValueError, match="empty output"):
        build(output=tmp_path)
