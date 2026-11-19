"""Source-backed checks of decade selection, unchanged fits and yield dispersion."""

import numpy as np
import pandas as pd
import pytest

from scripts.filing_decades import (
    PERIODS, ROOT, TREASURY, WORKBOOK, analyze, load_panel, specification, verify_full_sample,
)
from src.filing_study import fit_stage


def test_decades_match_direct_source_backed_fits():
    if not (ROOT / WORKBOOK).is_file():
        pytest.skip("Local EEI workbook required for source-backed decade regression")
    frame = load_panel()
    verify_full_sample(frame)
    original = frame.copy(deep=True)
    result = analyze(frame)
    _, flag, features, effects, weight = specification()
    assert len(result) == len(PERIODS)
    selected_ids = []
    for row, (start, end) in zip(result.itertuples(), PERIODS):
        selected = frame.loc[frame[flag] & (frame.year >= start) & (frame.year <= end)]
        selected_ids.extend(selected.id.tolist())
        assert row.period == f"{start}-{end}"
        assert row.n == len(selected)
        deviations = np.concatenate([
            (part[TREASURY] - part[TREASURY].mean()).to_numpy()
            for _, part in selected.groupby("year")
        ]) if len(selected) else np.array([])
        if len(deviations) > 1:
            assert row.within_year_sd_pp == pytest.approx(np.std(deviations, ddof=1))
        try:
            direct = fit_stage(selected, "award", features, effects, weight)
        except ValueError as error:
            assert row.status == "unavailable"
            assert row.reason == str(error)
            continue
        expected = direct.coefficients([TREASURY], "two_way")[0]
        assert row.treasury_estimate_pp == pytest.approx(expected["estimate"])
        if expected["low"] is None:
            assert row.status == "inference_unavailable"
            assert pd.isna(row.treasury_low_pp)
            assert pd.isna(row.treasury_high_pp)
        else:
            assert row.status == "estimated"
            assert row.treasury_low_pp == pytest.approx(expected["low"])
            assert row.treasury_high_pp == pytest.approx(expected["high"])
    eligible = frame[frame[flag] & frame.year.between(1985, 2024)]
    assert len(selected_ids) == len(set(selected_ids))
    assert set(selected_ids) == set(eligible.id)
    assert frame.equals(original)
