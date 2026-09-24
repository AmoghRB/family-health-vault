"""Doctor-visit summary: one page. Python picks the facts, the LLM only writes sentences.

OWNER: Reasoning & Submission role — name: ________ (fill in when you pick this)
LANGUAGE / LIBS: Python 3.12, re, datetime. LLM only via src/llm.py.

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py + prompts/summary.txt into
your AI, then say: "Implement src/summary.py exactly as described. Only edit this file."

FUNCTION  build(tl: Timeline, medicines: list[str], use_llm=True) -> DoctorSummary
  (api.py passes medicines = [m["name"] for m in store.medicines(person_id)])
  1. facts (pure Python): medicines as given,
     top_trends = first 3 red/amber flags, questions = their ask_doctor
     strings (deduplicated), caveats = tl["caveats"].
  2. intro:
     - If use_llm and llm.available(): send the facts as JSON to
       llm.chat(system=prompts/summary.txt, user=json.dumps(facts)).
       Then run guard(text, facts) and use it only if it passes.
     - Otherwise (or if the guard rejects it) use template(facts): e.g.
       "Ramesh Kumar has 7 reports from Mar 2024 to Aug 2026. 2 things are
        worth discussing: ..."
  3. generated = today's date "YYYY-MM-DD".

guard(text, facts) -> str | None   (safety net for the LLM's sentences)
  Reject (return None) if the text:
  - contains any number that doesn't appear in the facts JSON,
  - contains diagnosis/dose words: "diagnos", "you have", "mg", "dose",
    "stop taking", "start taking", "increase", "decrease",
  - is longer than 3 sentences.

RULES
  - The LLM never sees raw reports and never computes anything.
  - The summary must work with Ollama switched off (template path).

DONE WHEN
  tests/test_reason.py::test_summary_template passes, and the summary for the
  fake Ramesh data reads well as one page in the UI.
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import re
from datetime import date

from src import PROMPTS, llm
from src.contracts import DoctorSummary, Timeline

SUMMARY_PROMPT = PROMPTS / "summary.txt"


def guard(text: str, facts: dict) -> str | None:
    raise NotImplementedError  # TODO(REASON)


def template(facts: dict) -> str:
    raise NotImplementedError  # TODO(REASON)


def build(tl: Timeline, medicines: list[str], use_llm: bool = True) -> DoctorSummary:
    raise NotImplementedError  # TODO(REASON)
