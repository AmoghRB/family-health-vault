"""OWNER: Pankaj Kumar B S

Converts a RawValue (as extracted, still strings) into a StandardValue
(canonical unit, known reference range, traceable to its source).

Numbers are computed here in plain Python — never by the LLM.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

TESTS_PATH = Path(__file__).parent.parent / "data" / "tests.yaml"

_tests_cache: dict | None = None


def _load_tests() -> dict:
    global _tests_cache
    if _tests_cache is None:
        with open(TESTS_PATH, encoding="utf-8") as f:
            _tests_cache = yaml.safe_load(f)
    return _tests_cache


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation-adjacent spacing."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _find_test_id(raw_test_name: str) -> Optional[str]:
    """Exact (normalized) match against aliases in tests.yaml. No fuzzy matching."""
    tests = _load_tests()
    target = _normalize(raw_test_name)
    for test_id, spec in tests.items():
        for alias in spec["aliases"]:
            if _normalize(alias) == target:
                return test_id
    return None


def _parse_value(raw_value: str) -> Optional[float]:
    """Raw value is a string as printed, e.g. '131', '6.6', or occasionally messy."""
    cleaned = raw_value.strip().replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _convert_unit(value: float, from_unit: str, to_unit: str, conversions: dict) -> Optional[float]:
    """Convert value from from_unit to to_unit using the factor in conversions.
    conversions maps {other_unit: factor_to_canonical}. Returns None if unsupported.
    """
    from_unit_norm = from_unit.strip()
    if from_unit_norm == to_unit:
        return value
    factor = conversions.get(from_unit_norm)
    if factor is None:
        return None
    return value * factor


def _status(value: float, normal: list) -> str:
    low, high = normal
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


def standardize(raw_value: dict) -> Optional[dict]:
    """Takes a RawValue dict, returns a StandardValue dict, or None if the
    test is unrecognized or the value can't be trusted.
    """
    test_id = _find_test_id(raw_value["test"])
    if test_id is None:
        return None  # unknown test — don't guess the identity of the test itself

    spec = _load_tests()[test_id]

    numeric_value = _parse_value(raw_value["value"])
    if numeric_value is None:
        return None  # implausible/unparseable value

    printed_unit = raw_value.get("unit")
    guessed = False

    if printed_unit is None:
        # No unit printed — assume canonical unit, but flag it as guessed.
        converted_value = numeric_value
        guessed = True
    elif printed_unit.strip() == spec["canonical_unit"]:
        converted_value = numeric_value
    else:
        converted_value = _convert_unit(
            numeric_value, printed_unit, spec["canonical_unit"], spec["conversions"]
        )
        if converted_value is None:
            return None  # unit we don't know how to convert — don't fabricate a number

    return {
        "test_id": test_id,
        "name": spec["name"],
        "value": round(converted_value, 2),
        "unit": spec["canonical_unit"],
        "normal": spec["normal"],
        "status": _status(converted_value, spec["normal"]),
        "raw": raw_value,
        "guessed": guessed,
    }
