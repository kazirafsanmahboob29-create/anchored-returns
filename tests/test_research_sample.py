"""Selection rules checked against independent exhaustive enumeration."""

from collections import Counter
from itertools import combinations

import pytest

from src.research_sample import choose_sample, REQUIRED


def candidates():
    dates = {
        "CT": ["2025-11-05", "2025-10-28", "2024-11-01", "2024-11-01"],
        "MA": ["2024-09-30", "2024-06-24", "2021-09-30", "2020-10-30"],
        "ME": ["2025-03-13", "2021-10-18", "2020-03-26"],
        "VT": ["2026-08-28", "2023-10-23"],
        "NH": ["2025-07-25"],
        "RI": ["2020-05-05"],
    }
    return [
        dict(
            candidate_id=REQUIRED if state == "NH" else f"TEST-{state}-{i}",
            state=state,
            order_date=day,
            docket=f"SYNTHETIC-{i}",
            utility=f"Synthetic {state} {i}",
            status="conditional_settled_substitute" if state == "RI" else "eligible_contested_roe",
        )
        for state, days in dates.items()
        for i, day in enumerate(days)
    ]


def test_conditional_substitute_never_enters_strict_selection():
    pool = candidates()
    assert choose_sample(pool) is None
    assert len(choose_sample(pool, conditional=True)) == 15


def test_solution_matches_exhaustive_quota_and_date_priority_oracle():
    pool = candidates() + [
        dict(
            candidate_id="EXTRA-" + state,
            state=state,
            order_date=day,
            docket="EXTRA",
            utility="Synthetic extra",
            status="eligible_contested_roe",
        )
        for state, day in [
            ("CT", "2026-06-01"),
            ("MA", "2019-06-01"),
            ("VT", "2025-06-01"),
            ("RI", "2025-06-01"),
        ]
    ]
    ordered = sorted(
        pool,
        key=lambda c: (
            -int(c["order_date"].replace("-", "")),
            c["state"],
            c["docket"],
            c["utility"],
        ),
    )
    expected = None
    for group in combinations(ordered, 15):
        count = Counter(c["state"] for c in group)
        if (
            len(count) == 6
            and max(count.values()) <= 4
            and count["VT"] >= 2
            and sum(c["order_date"] < "2022-01-01" for c in group) >= 5
            and sum(c["order_date"] >= "2023-01-01" for c in group) >= 5
            and REQUIRED in {c["candidate_id"] for c in group}
        ):
            expected = [c["candidate_id"] for c in group]
            break
    assert expected is not None
    assert [
        c["candidate_id"] for c in choose_sample(list(reversed(pool)), conditional=True)
    ] == expected


@pytest.mark.parametrize("change", ["future", "required", "early", "state", "vermont"])
def test_quota_failures_cannot_be_silently_relaxed(change):
    pool = candidates()
    if change == "future":
        pool[0]["order_date"] = "2026-10-02"
    if change == "required":
        next(c for c in pool if c["state"] == "NH")["candidate_id"] = "OTHER"
    if change == "early":
        next(c for c in pool if c["state"] == "RI")["order_date"] = "2022-01-01"
    if change == "state":
        next(c for c in pool if c["state"] == "RI")["state"] = "CT"
    if change == "vermont":
        next(c for c in pool if c["state"] == "VT")["state"] = "ME"
    assert choose_sample(pool, conditional=True) is None


def test_unknown_classification_and_duplicate_identity_fail():
    pool = candidates()
    pool[0]["status"] = "eligible_unverified_guess"
    with pytest.raises(ValueError, match="Unknown eligibility"):
        choose_sample(pool)
    pool = candidates()
    pool.append(dict(pool[0]))
    with pytest.raises(ValueError, match="Duplicate"):
        choose_sample(pool)
