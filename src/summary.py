"""Doctor-visit summary: one page. Python picks the facts, the LLM only writes sentences.

OWNER: Reasoning & Submission role
LANGUAGE / LIBS: Python 3.12, re, datetime. LLM only via src/llm.py.

FUNCTION  build(tl: Timeline, medicines: list[str], use_llm=True) -> DoctorSummary
guard(text, facts) -> str | None
template(facts) -> str

DONE WHEN
  tests/test_reason.py::test_summary_template passes, and the summary for the
  fake Ramesh data reads well as one page in the UI.
"""

from __future__ import annotations

import json
import re
from datetime import date

from src import PROMPTS, llm
from src.contracts import DoctorSummary, Timeline

SUMMARY_PROMPT = PROMPTS / "summary.txt"

_BANNED = [
    "diagnos", "you have", "mg", "dose",
    "stop taking", "start taking", "increase", "decrease",
]


def _extract_numbers(text: str) -> set[str]:
    """Pull all numbers (int or decimal) from a string."""
    return set(re.findall(r"\d+\.?\d*", text))


def guard(text: str, facts: dict) -> str | None:
    """Safety net for the LLM's sentences. Return text if OK, None if rejected."""
    # 1. Check for invented numbers
    text_nums = _extract_numbers(text)
    facts_nums = _extract_numbers(json.dumps(facts))
    if text_nums - facts_nums:
        return None

    # 2. Check for banned words
    lower = text.lower()
    for word in _BANNED:
        if word in lower:
            return None

    # 3. Check sentence count (≤ 3)
    sentences = re.split(r"[.!?]+", text.strip())
    # filter out empty strings from trailing punctuation
    sentences = [s for s in sentences if s.strip()]
    if len(sentences) > 3:
        return None

    return text


def template(facts: dict) -> str:
    """Fixed fallback intro when the LLM is off or its output is rejected."""
    person = facts.get("person", "This person")
    meds = facts.get("medicines", [])
    top = facts.get("top_trends", [])

    parts = []
    if meds:
        parts.append(f"{person} is currently taking {', '.join(meds)}.")
    else:
        parts.append(f"{person} has recent lab reports on file.")

    if top:
        titles = [f["title"] for f in top]
        n = len(titles)
        things = "thing" if n == 1 else "things"
        parts.append(
            f"{n} {things} worth discussing with the doctor: {'; '.join(titles)}."
        )
    else:
        parts.append("No urgent findings to discuss.")

    return " ".join(parts)


def build(tl: Timeline, medicines: list[str],
          use_llm: bool = True) -> DoctorSummary:
    """Assemble the doctor-visit summary from a Timeline."""
    # 1. Facts (pure Python)
    red_amber = [f for f in tl["flags"] if f["level"] in ("red", "amber")]
    top_trends = red_amber[:3]
    # deduplicated questions preserving order
    seen_q: set[str] = set()
    questions: list[str] = []
    for f in top_trends:
        q = f["ask_doctor"]
        if q not in seen_q:
            questions.append(q)
            seen_q.add(q)

    caveats = tl["caveats"]

    facts = {
        "person": tl["person"],
        "medicines": medicines,
        "top_trends": top_trends,
        "questions": questions,
        "caveats": caveats,
    }

    # 2. Intro
    intro = None
    if use_llm:
        try:
            if llm.available():
                system = SUMMARY_PROMPT.read_text(encoding="utf-8")
                raw = llm.chat(system=system, user=json.dumps(facts))
                intro = guard(raw, facts)
        except Exception:
            intro = None

    if intro is None:
        intro = template(facts)

    # 3. Assemble DoctorSummary
    return {
        "person": tl["person"],
        "generated": date.today().isoformat(),
        "medicines": medicines,
        "top_trends": top_trends,
        "questions": questions,
        "caveats": caveats,
        "intro": intro,
    }
