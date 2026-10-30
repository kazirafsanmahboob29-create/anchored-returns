"""Check real sample identity, prior-decision timing and portable exports."""

import json

import numpy as np
import pandas as pd
import pytest

from src.expanded_study import ROOT, explore, make_panel, numeric_equal


class ExampleHistory:
    def __init__(self):
        self.states = {"A": {"region": "Northeast"}}

    def join(self, days, states):
        # Software fixture only. It never enters a research source directory.
        return pd.DataFrame(
            {
                name: np.ones(len(days))
                for name in ("treasury90", "curve90", "inflation", "stress", "unemployment")
            }
        )


def test_prior_uses_actual_earlier_date_and_all_same_day_awards():
    rows = []
    for identifier, day, award in (
        ("old", "1994-01-01", 1000),
        ("a", "1995-01-01", 900),
        ("b", "1995-01-01", 1100),
        ("next", "1996-01-01", 950),
    ):
        rows.append(
            {
                "id": identifier,
                "state": "A",
                "utility": "Utility",
                "year": int(day[:4]),
                "authorized_date": day,
                "award_bp": award,
                "requested_date": None,
                "case_type": "Distribution",
                "treasury_bp": None,
                "treasury_date": None,
                "treasury_gap_days": None,
            }
        )
    frame = make_panel(rows, ExampleHistory()).set_index("id")
    assert frame.loc["a", "prior_ids"] == frame.loc["b", "prior_ids"] == "old"
    assert frame.loc["a", "prior"] == 10
    assert frame.loc["next", "prior_ids"] == "a;b"
    assert frame.loc["next", "prior"] == 10
    assert frame.loc["next", "delta_roe"] == -0.5


def test_saved_extended_sample_contains_the_original_ids():
    extended = pd.read_csv(ROOT / "reports/expanded-study/estimation.csv")
    original = pd.read_csv(ROOT / "reports/factor-study/estimation.csv")
    assert len(extended) > len(original)
    assert set(extended.loc[extended.year >= 2010, "id"]) == set(original.id)
    assert not extended.id.duplicated().any()
    assert (extended.prior_date < extended.authorized_date).all()
    assert extended.year.between(1995, 2024).all()


def test_stata_datasets_preserve_numeric_model_inputs():
    for name in ("estimation", "changes", "long"):
        csv = pd.read_csv(ROOT / f"reports/expanded-study/{name}.csv")
        dta = pd.read_stata(ROOT / f"reports/expanded-study/{name}.dta", convert_categoricals=False)
        assert csv.id.tolist() == dta.id.tolist()
        for column in csv.select_dtypes(include="number").columns:
            assert np.allclose(csv[column], dta[column], equal_nan=True, atol=1e-12, rtol=0), column


def test_saved_predictions_keep_block_timing_and_one_row_per_case():
    frame = pd.read_csv(ROOT / "reports/expanded-study/predictions.csv")
    assert not frame.id.duplicated().any()
    assert (frame.training_end < frame.year).all()
    assert (frame.training_n >= 100).all()
    assert np.allclose(frame.loss_previous_award, abs(frame.previous_award - frame.actual) * 100)
    summary = json.loads((ROOT / "reports/expanded-study/study.json").read_text())
    assert summary["coverage"]["main_complete"] > 533
    assert len(summary["prediction_blocks"]) == 5
    assert summary["prediction_blocks"][0]["status"] == "insufficient_history"


def test_explorer_filters_real_rows_and_preserves_the_published_panel(tmp_path):
    original = (ROOT / "reports/expanded-study/panel.csv").read_bytes()
    export = tmp_path / "midwest.csv"
    result = explore(region="Midwest", start=2010, end=2024, export=export)
    data = pd.read_csv(export)
    assert result["complete"] == len(data) > 0
    assert (data.region == "Midwest").all() and data.year.between(2010, 2024).all()
    assert original == (ROOT / "reports/expanded-study/panel.csv").read_bytes()
    with pytest.raises(ValueError, match="new file"):
        explore(region="Midwest", export=export)


@pytest.mark.parametrize(
    "setting",
    [{"region": "Invented"}, {"start": 1980}, {"end": 2026}, {"start": 2024, "end": 2010}],
)
def test_explorer_rejects_unsupported_regions_and_periods(setting):
    with pytest.raises(ValueError):
        explore(**setting)


def test_report_comparison_checks_values_not_just_schema():
    original = {"metrics": [{"mae": 31.2, "n": 634}], "status": "available"}
    assert numeric_equal(
        original, {"metrics": [{"mae": 31.2 + 1e-10, "n": 634}], "status": "available"}
    )
    assert not numeric_equal(
        original, {"metrics": [{"mae": 30.0, "n": 634}], "status": "available"}
    )
