"""Exercise the retained research helpers with invented cases."""

from pathlib import Path

from openpyxl import Workbook
import pandas as pd

from src.factor_study import SERIES, panel
from src.national_study import enrich
from src.panel_diagnostics import state_influence
from src.validate_sheet import CODES, SCHEMA, validate_sheet


def test_prior_awards_and_case_eligibility():
    def case(index, utility, state, day, award, status="Settled", kind="Distribution"):
        return dict(source_row=index, utility=utility, state=state, docket=f"TEST-{index}",
                    authorized_date=day, authorized_roe_percent=award, requested_date="",
                    requested_roe_percent=None, completion_status=status, case_type=kind)

    records = [
        case(1, "Alder Electric", "Maine", "2000-01-01", "8"),
        case(2, "Alder Electric", "Maine", "2011-01-02", "9"),
        case(3, "Alder Electric", "Maine", "2012-01-02", "10"),
        case(4, "Alder Electric", "Maine", "2012-01-02", "12"),
        case(5, "Alder Electric", "Vermont", "2012-02-01", "19"),
        case(6, "Birch Power", "Maine", "2012-03-01", "17"),
        case(7, "Alder Electric", "Maine", "2012-04-01", "16", status="Pending"),
        case(8, "Alder Electric", "Maine", "2012-05-01", "15", kind="Rider"),
        case(9, "Alder Electric", "Maine", "2013-01-02", None),
        case(10, "Alder Electric", "Maine", "2014-01-02", "13"),
    ]
    result = {row["id"]: row for row in panel(enrich(records, []), dict.fromkeys(SERIES, ()))}
    assert set(result) == {f"EEI-{i}" for i in (2, 3, 4, 5, 6, 9, 10)}
    assert result["EEI-2"]["prior"] is None  # The 8% award was more than ten years earlier.
    assert result["EEI-3"]["prior"] == result["EEI-4"]["prior"] == 9  # Both use the 2011 award.
    assert result["EEI-5"]["prior"] is None
    assert result["EEI-6"]["prior"] is None
    assert result["EEI-9"]["roe"] is None
    assert result["EEI-9"]["prior"] == result["EEI-10"]["prior"] == 11  # (10% + 12%) / 2.


def test_state_influence_omits_exactly_the_selected_state(monkeypatch):
    main = pd.DataFrame({"state": ["ME", "ME", "VT", "NH"]}, index=[1, 2, 3, 4])
    changes = main.iloc[[0, 2, 3]]
    selections = []

    def record_fit(frame, target, features, effects):
        selections.append((target, tuple(frame.index)))
        raise ValueError("Fixture only records the selected rows")

    monkeypatch.setattr("src.panel_diagnostics.fit", record_fit)
    result = state_influence(main, changes, ["prior"], [])
    # Omitting ME, NH and VT in order leaves these exact case IDs.
    assert selections == [
        ("roe", (3, 4)), ("roe", (1, 2, 3)), ("roe", (1, 2, 4)),
        ("delta_roe", (3, 4)), ("delta_roe", (1, 3)), ("delta_roe", (1, 4)),
    ]
    assert [(row["omitted_state"], row["n"]) for row in result] == [
        ("ME", 2), ("NH", 3), ("VT", 3), ("ME", 2), ("NH", 2), ("VT", 2),
    ]


def test_coding_sheet_accepts_valid_code_and_rejects_unknown_code(tmp_path: Path):
    book = Workbook()
    book.remove(book.active)
    for sheet, key in (("Cases", "case_headers"), ("Passages", "passage_headers"),
                       ("Reliability", "reliability_headers")):
        book.create_sheet(sheet).append(SCHEMA[key])
    lists = book.create_sheet("Lists")
    for column, (key, values) in enumerate(SCHEMA["lists"].items(), 1):
        lists.cell(1, column, key)
        for row, value in enumerate(values, 2):
            lists.cell(row, column, value)
    # MKT is the sole active flag and the valid primary code for this DCF passage.
    passage = dict(passage_id="TEST-1-001", case_id="TEST-1", page_para="PDF p. 2",
                   excerpt="Invented software fixture.", section="Commission analysis",
                   method="DCF", primary_code="MKT", stance="Relied on", coder="Fixture",
                   **{code: int(code == "MKT") for code in CODES})
    case = dict(case_id="TEST-1", utility="Cedar Light")
    book["Cases"].append([case.get(key) for key in SCHEMA["case_headers"]])
    book["Passages"].append([passage.get(key) for key in SCHEMA["passage_headers"]])
    path = tmp_path / "invented.xlsx"
    book.save(path)
    valid = validate_sheet(path, scope="practice")
    cell = SCHEMA["passage_headers"].index("primary_code") + 1
    book["Passages"].cell(2, cell, "INVALID")
    book.save(path)
    invalid = validate_sheet(path, scope="practice")
    assert not any(i["sheet"] == "Passages" and i["field"] == "primary_code" for i in valid["issues"])
    assert any(
        i["sheet"] == "Passages" and i["field"] == "primary_code" and i["severity"] == "error"
        for i in invalid["issues"]
    )
    assert invalid["status"] == "failed"
