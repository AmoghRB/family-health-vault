"""Reasoning: trends, flags and data-quality caveats. Plain Python, NO LLM.

OWNER: Reasoning & Submission role — name: ________ (fill in when you pick this)
LANGUAGE / LIBS: Python 3.12, PyYAML, statistics, datetime. No LLM, no numpy needed.

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py + data/rules.yaml +
data/medicines.yaml into your AI, then say:
"Implement src/reason.py exactly as described. Only edit this file."

GOAL
  Turn a person's stored values + medicines into a Timeline (src/contracts.py):
  one series per test for the chart, a list of flags for the cards, and
  data-quality caveats. This is where the demo's "wow" moment comes from.

FUNCTIONS
  drug_class(name) -> str | None
      Look the medicine name up in data/medicines.yaml (case-insensitive,
      also match if an alias is a word inside the name). Used by src/ingest.py.

  trend(points) -> dict
      points = [{"date", "value"}...] oldest first, needs ≥ 3.
      Least-squares slope per year (write it by hand, ~8 lines), plus
      {"direction": "rising"|"falling"|"flat", "change": last − first,
       "years": span}. "flat" if |total change| < 5% of the first value.

  timeline(store, person_id) -> Timeline | None
      1. None if store.person(person_id) is None.
      2. series: group store.results(person_id) by test_id; each point gets
         source = f"{filename}#p{page}"; display name/unit/normal range from
         data/tests.yaml (reuse src.standard.catalogue()).
      3. Flags (each is a Flag dict; ask_doctor is ALWAYS a question):
         a. Cross-document (MOST IMPORTANT, the demo depends on it): for each
            rule in data/rules.yaml, if the person has a medicine of that
            drug_class AND any listed test meets its condition using readings
            from the last one before the medicine's start_date onwards → one
            flag citing BOTH the prescription file and the lab files.
            e.g. metformin + creatinine rising →
            "Kidney values rising since metformin started" /
            "Should my kidney function be checked while on metformin?"
         b. Trend: 3+ readings, direction == the test's `bad` direction, and
            the latest is outside the range or within 10% of the limit → amber
            (red if outside the range and still getting worse).
         c. Out of range: latest reading outside the range and not already
            flagged → amber.
         d. Good news: was out of range, now back inside → green.
         Sort flags red → amber → green.
      4. Caveats (plain strings):
         - a "fasting" test (test_id starting "glucose_fasting") whose report
           collected_time is after 10:00 → "The fasting sample on <date> was
           collected at <time>, so it may not be a true fasting value."
         - two reports with the same date and lab → possible duplicate
         - a test value marked guessed → "Unit for <test> on <date> was not
           printed and was inferred."

RULES
  - No LLM. No diagnoses ("you have diabetes" ✗). Describe numbers, ask questions.
  - Every number in `detail` comes from the data, formatted like "6.1 → 7.2%".

DONE WHEN
  pytest -q tests/test_reason.py passes, and on the fake data Ramesh gets ≥ 3
  flags including the metformin one.
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from datetime import date

import yaml

from src import DATA
from src.contracts import Flag, Timeline

RULES_FILE = DATA / "rules.yaml"
MEDICINES_FILE = DATA / "medicines.yaml"


def drug_class(name: str) -> str | None:
    raise NotImplementedError  # TODO(REASON)


def trend(points: list[dict]) -> dict:
    raise NotImplementedError  # TODO(REASON)


def timeline(store, person_id: int) -> Timeline | None:
    raise NotImplementedError  # TODO(REASON)
