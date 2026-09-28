"""OWNER: Pankaj Kumar B S"""

from src.standard import standardize


def test_unit_conversion_mmol_to_mgdl():
    result = standardize({"test": "FBS", "value": "6.6", "unit": "mmol/L", "range": None, "page": 1})
    assert result is not None
    assert result["test_id"] == "glucose_fasting"
    assert result["value"] == 118.8
    assert result["unit"] == "mg/dL"
    assert result["guessed"] is False


def test_missing_unit_is_guessed():
    result = standardize({"test": "Blood Sugar F", "value": "131", "unit": None, "range": None, "page": 1})
    assert result is not None
    assert result["test_id"] == "glucose_fasting"
    assert result["value"] == 131.0
    assert result["guessed"] is True


def test_unknown_test_returns_none():
    result = standardize({"test": "Unknown Test XYZ", "value": "5", "unit": None, "range": None, "page": 1})
    assert result is None


def test_status_flagging_low_normal_high():
    high = standardize({"test": "FBS", "value": "150", "unit": "mg/dL", "range": None, "page": 1})
    assert high["status"] == "high"

    normal = standardize({"test": "FBS", "value": "90", "unit": "mg/dL", "range": None, "page": 1})
    assert normal["status"] == "normal"

    low = standardize({"test": "FBS", "value": "50", "unit": "mg/dL", "range": None, "page": 1})
    assert low["status"] == "low"


def test_unparseable_value_returns_none():
    result = standardize({"test": "FBS", "value": "not-a-number", "unit": "mg/dL", "range": None, "page": 1})
    assert result is None


def test_unconvertible_unit_returns_none():
    result = standardize({"test": "FBS", "value": "6.6", "unit": "weird_unit", "range": None, "page": 1})
    assert result is None


def test_alias_case_and_whitespace_insensitive():
    result = standardize({"test": "  fbs  ", "value": "90", "unit": "mg/dL", "range": None, "page": 1})
    assert result is not None
    assert result["test_id"] == "glucose_fasting"


def test_open_ended_normal_range():
    result = standardize({"test": "HDL", "value": "35", "unit": "mg/dL", "range": None, "page": 1})
    assert result["status"] == "low"  # below 40, normal is [40, None]
