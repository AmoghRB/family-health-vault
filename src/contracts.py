"""The shapes passed between modules. SHARED FILE: change only after the group agrees.

This is the contract that lets four people build separately and still plug
together. Every module takes and returns plain dicts shaped like the TypedDicts
below (TypedDicts are just type hints; at runtime they are ordinary dicts).

Flow:
    extract.py  ──ExtractedReport──►  standard.py  ──StandardValue──►  store.py
    store.py    ──rows──►  reason.py  ──Timeline──►  api.py / web/app.js
    reason.py   ──Timeline──►  summary.py  ──DoctorSummary──►  api.py / web/app.js

Human-readable version with examples: docs/interfaces.md
"""

from __future__ import annotations

from typing import Literal, TypedDict

Level = Literal["red", "amber", "green"]
Status = Literal["low", "normal", "high", "unknown"]


# ── 1. extract.py → standard.py (Extraction & API → Data & Standards) ────────────────
class RawValue(TypedDict):
    test: str              # exactly as printed, e.g. "Blood Sugar F"
    value: str             # exactly as printed, e.g. "131" or "6.6" (string: no parsing yet)
    unit: str | None       # as printed, e.g. "mmol/L"; None if not printed
    range: str | None      # reference range as printed, e.g. "70 - 100", "< 200"
    page: int              # 1-based page number


class Medicine(TypedDict):
    name: str              # name only, never dose/strength/frequency


class ExtractedReport(TypedDict):
    kind: Literal["lab", "prescription"]
    person: str | None           # patient name as printed
    date: str | None             # "YYYY-MM-DD" (sample collection date if printed)
    collected_time: str | None   # "HH:MM" 24h, used by the fasting-time check
    lab: str | None              # lab / clinic name
    values: list[RawValue]       # empty for prescriptions
    medicines: list[Medicine]    # empty for lab reports


# ── 2. standard.py output (Data & Standards → store.py / reason.py) ──────────────────
class StandardValue(TypedDict):
    test_id: str               # key in data/tests.yaml, e.g. "glucose_fasting"
    name: str                  # display name, e.g. "Fasting glucose"
    value: float               # converted to the canonical unit
    unit: str                  # canonical unit, e.g. "mg/dL"
    normal: list[float | None] # [low, high] in the canonical unit; None = open-ended
    status: Status
    raw: RawValue              # what was printed, kept for traceability
    guessed: bool              # True if alias or unit had to be guessed


# ── 3. reason.py → api.py → web/app.js (Reasoning & Submission → Frontend & Demo) ────
class Point(TypedDict):
    date: str                  # "YYYY-MM-DD"
    value: float
    source: str                # "<filename>#p<page>", e.g. "apollo_2024-03-11.pdf#p1"


class Series(TypedDict):
    test: str                  # display name, e.g. "HbA1c"
    test_id: str
    unit: str
    normal: list[float | None]
    points: list[Point]        # oldest first


class Flag(TypedDict):
    level: Level
    title: str                 # short, e.g. "Blood sugar rising steadily"
    detail: str                # the numbers, e.g. "HbA1c 6.1 → 7.2% over 29 months."
    ask_doctor: str            # always a question, never advice
    sources: list[str]         # filenames the flag is based on


class Timeline(TypedDict):
    person: str
    person_id: int
    series: list[Series]
    flags: list[Flag]          # most severe first
    caveats: list[str]         # data-quality warnings (late "fasting" sample, duplicates…)


# ── 4. summary.py → api.py → web/app.js (Reasoning & Submission → Frontend & Demo) ───
class DoctorSummary(TypedDict):
    person: str
    generated: str             # "YYYY-MM-DD"
    medicines: list[str]
    top_trends: list[Flag]     # at most 3
    questions: list[str]
    caveats: list[str]
    intro: str                 # 2–3 sentences written by the LLM (or a template if Ollama is off)


# ── 5. api.py responses (Extraction & API → Frontend & Demo) ─────────────────────────
class Person(TypedDict):
    id: int
    name: str
    reports: int               # number of uploaded reports


class UploadResult(TypedDict):
    filename: str
    ok: bool
    report_id: int | None
    person_id: int | None
    kind: str | None
    values_saved: int
    message: str               # human-readable, shown in the UI
