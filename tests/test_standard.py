"""Tests for src/standard.py.  OWNER: Data & Standards role — name: ________ (fill in when you pick this).

These are the DONE WHEN checks. Add more cases as you add tests to tests.yaml.
Run: pytest -q tests/test_standard.py
"""

from src.standard import match_test, parse_number, standardize


def raw(test, value, unit=None, rng=None):
    return {"test": test, "value": value, "unit": unit, "range": rng, "page": 1}


def test_mmol_glucose_converts_to_mg_dl():
    v = standardize(raw("FBS", "6.6", "mmol/L"))
    assert v["test_id"] == "glucose_fasting"
    assert v["value"] == 118.8
    assert v["unit"] == "mg/dL"
    assert v["status"] == "high"


def test_alias_without_unit_is_guessed():
    v = standardize(raw("Blood Sugar F", "131", None, "70-100"))
    assert v["test_id"] == "glucose_fasting"
    assert v["value"] == 131
    assert v["guessed"] is True


def test_creatinine_umol():
    v = standardize(raw("S. Creatinine", "106", "µmol/L"))
    assert v["test_id"] == "creatinine"
    assert abs(v["value"] - 1.2) < 0.01


def test_unknown_test_returns_none():
    assert standardize(raw("Unobtainium level", "5", "mg/dL")) is None


def test_implausible_value_returns_none():
    assert standardize(raw("FBS", "9000", "mg/dL")) is None


def test_parse_number_indian_grouping():
    assert parse_number("1,50,000") == 150000
    assert parse_number("<0.5") == 0.5


def test_match_test_exact():
    assert match_test("Fasting Blood Sugar") == ("glucose_fasting", False)
