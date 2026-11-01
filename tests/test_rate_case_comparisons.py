"""Check units and coverage in the original-order financial comparison."""

from pathlib import Path

import pytest

from src.rate_case_comparisons import equity_return_allowance, load_schedules, roe_sensitivity

ROOT = Path(__file__).resolve().parents[1]


def test_basis_point_units_and_signed_sensitivity():
    assert roe_sensitivity(4_000_000_000, 0.5, 25) == pytest.approx(5_000_000)
    assert roe_sensitivity(4_000_000_000, 0.5, -25) == pytest.approx(-5_000_000)
    assert equity_return_allowance(100, 0.5, 0.09) == pytest.approx(4.5)
    with pytest.raises(ValueError):
        equity_return_allowance(100, 50, 9)


def test_settlement_missingness_and_joint_decision_units():
    rows = load_schedules(ROOT / "data/research/comparability-v1/phase2")
    assert len(rows) == 16
    assert len({r["proceeding_id"] for r in rows}) == 15
    pa = [r for r in rows if r["state"] == "PA"]
    assert len(pa) == 3
    assert all(r["equity_allowance_per_100"] is None for r in pa)
    assert all(r["annual_equity_allowance_usd"] is None for r in pa)
    nstar, west = [r for r in rows if r["proceeding_id"] == "MA-17-05"]
    assert nstar["applied_roe"] == west["applied_roe"]
    assert nstar["equity_allowance_per_100"] != west["equity_allowance_per_100"]


def test_performance_bridge_and_approved_rate_base_scope():
    rows = load_schedules(ROOT / "data/research/comparability-v1/phase2")
    for row in rows:
        if row["base_roe"] is not None and row["adjustment_roe"] is not None:
            assert row["base_roe"] + row["adjustment_roe"] == pytest.approx(row["applied_roe"])
    coned = next(r for r in rows if r["proceeding_id"] == "NY-22-E-0064")
    assert coned["approved_rate_base_usd"] == 26_094_576_000
    assert coned["evidence"]["approved_rate_base_usd"]["location"]["pdf_page"] == 339
