"""Independent source controls, period boundaries and explicit EEI scope."""

from decimal import Decimal

import pytest

from src.eei_benchmarks import _number, read_workbook


def test_binary_serialization_is_normalized_without_discarding_real_precision():
    assert _number(Decimal("9.6999999999999993"), "Q4") == "9.70"
    with pytest.raises(ValueError, match="precision"):
        _number(Decimal("9.701"), "Q4")


def test_changed_original_workbook_is_rejected(tmp_path):
    path = tmp_path / "changed.xlsx"
    path.write_bytes(b"not the original source")
    with pytest.raises(ValueError, match="fingerprint"):
        read_workbook(path)


