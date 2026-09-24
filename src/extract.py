"""Extraction: PDF → ExtractedReport (values copied exactly as printed).

OWNER: Extraction & API role — name: ________ (fill in when you pick this)
LANGUAGE / LIBS: Python 3.12, pdfplumber, json, re. LLM calls only via src/llm.py.

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py + prompts/extract.txt into
your AI, then say: "Implement src/extract.py exactly as described. Only edit this file."

GOAL
  Read one lab report or prescription PDF and return an ExtractedReport
  (src/contracts.py). Values stay as printed STRINGS: no unit conversion,
  no maths. Conversion is src/standard.py's job.

PIPELINE
  1. read_pdf(path) -> list[str]: one string per page via pdfplumber.
     Use page.extract_text(layout=True) so table columns stay aligned. Also
     try page.extract_tables(); if a table has a header row containing
     "test"/"investigation" and "result"/"value", turn each row into a line
     "<test>  <value>  <unit>  <range>" and append it to that page's text.
  2. read_llm(pages) -> ExtractedReport | None:
     - join pages as "=== PAGE n ===\n<text>" blocks,
     - system prompt = contents of prompts/extract.txt,
     - call llm.chat_json(system, user_text),
     - validate the result has the ExtractedReport keys and correct types;
       if not, retry ONCE with the error message appended; else return None.
  3. read_rules(pages) -> ExtractedReport: a regex fallback that works with
     no LLM, so the demo never dies:
     - date: first dd/mm/yyyy, dd-mm-yy, "14 Aug 2026" etc. → "YYYY-MM-DD"
       (day first; two-digit years are 20xx)
     - time: "hh:mm" or "hh:mm AM/PM" near "collected"/"collection" → 24h
     - person: text after "Patient Name"/"Name"/"Pt. Name"
     - lab: first line of page 1
     - values: lines matching  <name> <number> [unit] [range]
     - kind: "prescription" if it contains "Rx" or "Tab."/"Cap." lines
     - medicines: the word(s) after "Tab."/"Cap."/"Syp." with the strength removed
  4. extract(path, mode="auto") -> ExtractedReport:
     mode "llm" → read_llm only; "rules" → read_rules only;
     "auto" → LLM if llm.available() else rules. If the LLM result has fewer
     than half the values rules found, use rules (the LLM probably skipped some).

RULES
  - Never convert units or compute anything here.
  - Never keep doses: strip "500mg", "1-0-1", "BD", "OD" from medicine names.
  - Values not found = not included. Never invent.

DONE WHEN
  pytest -q tests/test_extract.py passes, and python tools/accuracy.py prints
  ≥ 95% on samples/ (needs the Data & Standards owner's fake reports + standard.py).
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src import PROMPTS, llm
from src.contracts import ExtractedReport

EXTRACT_PROMPT = PROMPTS / "extract.txt"


def read_pdf(path: str | Path) -> list[str]:
    raise NotImplementedError  # TODO(EXTRACT)


def read_llm(pages: list[str]) -> ExtractedReport | None:
    raise NotImplementedError  # TODO(EXTRACT)


def read_rules(pages: list[str]) -> ExtractedReport:
    raise NotImplementedError  # TODO(EXTRACT)


def extract(path: str | Path, mode: str = "auto") -> ExtractedReport:
    raise NotImplementedError  # TODO(EXTRACT)
