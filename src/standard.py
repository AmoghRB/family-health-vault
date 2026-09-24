"""Standardizer: turns a value as printed on a report into one canonical value.

OWNER: Data & Standards role — name: ________ (fill in when you pick this)
LANGUAGE / LIBS: Python 3.12, PyYAML, `re`. No other dependencies. No LLM here.

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py into your AI, then say:
"Implement src/standard.py exactly as described. Only edit this file."

GOAL
  Labs print the same test under different names and units ("FBS 6.6 mmol/L",
  "Blood Sugar F 131", "Glucose (Fasting) 118 mg/dL"). This module maps each
  to one test id from data/tests.yaml, converts it to the canonical unit,
  attaches the normal range, and says whether it is low/normal/high.

INPUT   a RawValue dict (see src/contracts.py), e.g.
        {"test": "FBS", "value": "6.6", "unit": "mmol/L", "range": None, "page": 1}
OUTPUT  a StandardValue dict, or None if the test is unknown or the value is
        implausible, e.g.
        {"test_id": "glucose_fasting", "name": "Fasting glucose", "value": 118.8,
         "unit": "mg/dL", "normal": [70, 100], "status": "high",
         "raw": <the input>, "guessed": False}

STEPS
  1. catalogue(): load data/tests.yaml once (cache with functools.lru_cache).
  2. norm_name(s): lowercase, strip punctuation like "." ":" "*", collapse spaces.
  3. match_test(raw_name) -> (test_id | None, guessed): exact alias match first;
     if none, fuzzy match with difflib.get_close_matches(cutoff=0.85) and set
     guessed=True.
  4. norm_unit(u): lowercase, "umol/l" and "µmol/l" treated the same, "mg/dl"
     etc. Return None for empty.
  5. parse_number(v): "6.6" → 6.6, "1,20,000" → 120000, "<0.5" → 0.5, "H 131" →
     131. None if no number.
  6. Conversion: if unit is the canonical unit → factor 1. If unit is in
     `convert` → use that factor. If unit is None (not printed) → pick the
     factor whose converted value lands inside `plausible` and is closest to
     the normal range (compare with the printed range if there is one), and
     set guessed=True.
  7. Reject (return None) if the converted value is outside `plausible`.
  8. status(value, normal): "low" / "normal" / "high"; None bounds are open.
  9. Round the value to 2 decimals.

RULES
  - Pure functions, no database, no network, no LLM.
  - Never raise on bad input: return None.

DONE WHEN
  pytest -q tests/test_standard.py passes, including
  standardize({"test": "FBS", "value": "6.6", "unit": "mmol/L", ...})["value"] == 118.8
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from src import DATA
from src.contracts import RawValue, StandardValue, Status

TESTS_FILE = DATA / "tests.yaml"


def catalogue() -> dict:
    """All tests from data/tests.yaml, keyed by test_id. Cached."""
    raise NotImplementedError  # TODO(DATA)


def norm_name(s: str) -> str:
    raise NotImplementedError  # TODO(DATA)


def match_test(raw_name: str) -> tuple[str | None, bool]:
    """(test_id, guessed). test_id is None if nothing matches."""
    raise NotImplementedError  # TODO(DATA)


def norm_unit(u: str | None) -> str | None:
    raise NotImplementedError  # TODO(DATA)


def parse_number(v: str | float | int | None) -> float | None:
    raise NotImplementedError  # TODO(DATA)


def status(value: float, normal: list[float | None]) -> Status:
    raise NotImplementedError  # TODO(DATA)


def standardize(raw: RawValue) -> StandardValue | None:
    """Main entry point. See the module docstring."""
    raise NotImplementedError  # TODO(DATA)
