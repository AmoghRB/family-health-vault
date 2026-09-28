"""Ask the vault: answers questions about one person's records with the LOCAL model.

OWNER: Amogh R B
LANGUAGE / LIBS: Python 3.12, re, json. LLM only via src/llm.py (Ollama on 127.0.0.1).

Same rule as the rest of the app: numbers come from Python, sentences from the LLM.
  1. facts(store, person_id): Python collects readings, medicines, flags and caveats.
  2. Dosing / medication-change questions are refused before the model sees them.
  3. The model phrases an answer from the facts only (prompts/chat.txt).
  4. guard(): any number in the reply that isn't in the facts or the question means the
     model calculated or invented something, so the reply is replaced by plain facts.
  5. Ollama off → a keyword answer straight from the facts, still useful offline.

answer(...) returns {"answer": str, "sources": [str], "mode": "llm" | "facts" | "refused"}.
"""

from __future__ import annotations

import json
import re

from src import PROMPTS, llm, reason

CHAT_PROMPT = PROMPTS / "chat.txt"
MAX_QUESTION = 400
DOSING_RE = re.compile(
    r"\b(dose|dosage|how (much|many) (mg|tablets?|pills?)|\d+\s?(mg|mcg|iu)\b(?!\s*/)|"
    r"(stop|start|quit|skip|increase|decrease|double|reduce) (taking|my|the)|should i (take|stop))", re.I)
REFUSAL = ("I can't advise on doses or changing medicines. That's a question for your doctor. "
           "I can tell you what your reports show, for example how a test has changed over time.")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _nums(text: str) -> set[float]:
    return {float(n) for n in NUM_RE.findall(text)}


def facts(store, person_id: int) -> dict | None:
    """Everything the model may use, gathered by Python. None if the person doesn't exist."""
    tl = reason.timeline(store, person_id)
    if tl is None:
        return None
    tests = []
    for s in tl["series"]:
        lo, hi = s["normal"]
        tests.append({
            "test": s["test"],
            "unit": s["unit"],
            "normal_range": f'{reason._range_text(s["normal"])} {s["unit"]}',
            "readings": [
                {"date": p["date"], "value": p["value"], "source": p["source"].split("#")[0],
                 "status": "below range" if lo is not None and p["value"] < lo
                 else "above range" if hi is not None and p["value"] > hi else "in range"}
                for p in s["points"]
            ],
        })
    return {
        "person": tl["person"],
        "medicines": [{"name": m["name"], "since": m.get("start_date")} for m in store.medicines(person_id)],
        "tests": tests,
        "flags": [{"title": f["title"], "detail": f["detail"], "ask_doctor": f["ask_doctor"]} for f in tl["flags"]],
        "data_quality_notes": tl["caveats"],
    }


def guard(reply: str, facts_: dict, question: str) -> bool:
    """True if every number in the reply appears in the facts or the question."""
    allowed = _nums(json.dumps(facts_)) | _nums(question) | set(range(0, 11))  # small counts ("2 readings")
    return _nums(reply) <= allowed


def _mentioned(facts_: dict, text: str) -> list[dict]:
    """Tests whose name (or a word of it) appears in the text."""
    low = text.lower()
    hits = [t for t in facts_["tests"] if t["test"].lower() in low]
    if not hits:
        hits = [t for t in facts_["tests"]
                if any(len(w) > 2 and w in low for w in re.findall(r"[a-z0-9]+", t["test"].lower()))]
    return hits


def _sources(facts_: dict, text: str) -> list[str]:
    files = []
    for t in _mentioned(facts_, text):
        for r in t["readings"]:
            if r["source"] not in files:
                files.append(r["source"])
    return files[:6]


def facts_answer(facts_: dict, question: str) -> str:
    """No-LLM answer: latest reading of each test the question mentions."""
    hits = _mentioned(facts_, question)
    if not hits:
        if re.search(r"medicine|medication|drug|tablet|prescri", question, re.I) and facts_["medicines"]:
            return "Medicines on record: " + ", ".join(m["name"] for m in facts_["medicines"]) + "."
        if facts_["flags"]:
            return "Flagged for the doctor: " + "; ".join(f["title"] for f in facts_["flags"]) + "."
        return "I don't see that in the uploaded reports."
    parts = []
    for t in hits[:3]:
        first, last = t["readings"][0], t["readings"][-1]
        s = f"{t['test']}: latest {last['value']} {t['unit']} on {last['date']} ({last['status']}; normal {t['normal_range']})"
        if len(t["readings"]) > 1:
            s += f", first recorded {first['value']} {t['unit']} on {first['date']}"
        parts.append(s + ".")
    return " ".join(parts)


def answer(store, person_id: int, question: str, history: list[dict] | None = None) -> dict | None:
    """One chat turn. None if the person doesn't exist. Never raises for model failures."""
    question = " ".join(str(question).split())[:MAX_QUESTION]
    f = facts(store, person_id)
    if f is None:
        return None
    if DOSING_RE.search(question):
        return {"answer": REFUSAL, "sources": [], "mode": "refused"}
    if not f["tests"] and not f["medicines"]:
        return {"answer": f"There are no reports for {f['person']} yet. Upload one and ask again.",
                "sources": [], "mode": "facts"}

    if llm.available():
        turns = [{"role": h.get("role"), "text": str(h.get("text", ""))[:500]}
                 for h in (history or [])[-4:] if h.get("role") in ("user", "assistant")]
        user = json.dumps({"FACTS": f, "EARLIER_TURNS": turns, "QUESTION": question}, ensure_ascii=False)
        system = "\n".join(ln for ln in CHAT_PROMPT.read_text().splitlines() if not ln.startswith("#")).strip()
        try:
            reply = llm.chat(system, user, timeout=120).strip()
            if reply and guard(reply, f, question) and not DOSING_RE.search(reply):
                return {"answer": reply, "sources": _sources(f, question + " " + reply), "mode": "llm"}
        except RuntimeError:
            pass  # fall through to the facts answer
    return {"answer": facts_answer(f, question), "sources": _sources(f, question), "mode": "facts"}
