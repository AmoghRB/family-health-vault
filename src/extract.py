"""Extraction: PDF → ExtractedReport (values copied exactly as printed).

OWNER: Extraction (Person 2): Amogh R B
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

import pdfplumber

from src import PROMPTS, llm
from src.contracts import ExtractedReport

EXTRACT_PROMPT = PROMPTS / "extract.txt"
TABLE_MARK = "=== TABLE ==="

# ── reading the PDF ───────────────────────────────────────────────────────────


def _results_table(table: list[list]) -> bool:
    """True if a pdfplumber table looks like a lab results table."""
    if not table or not table[0]:
        return False
    head = " ".join(str(c or "").lower() for c in table[0])
    return any(w in head for w in ("test", "investigation", "parameter")) and any(
        w in head for w in ("result", "value", "observed")
    )


def read_pdf(path: str | Path) -> list[str]:
    """One string per page. Results tables are appended as 'a | b | c | d' rows."""
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            rows = []
            for table in page.extract_tables():
                if _results_table(table):
                    rows += [" | ".join((c or "").strip() for c in r) for r in table[1:] if r]
            if rows:
                text += f"\n{TABLE_MARK}\n" + "\n".join(rows)
            pages.append(text)
    return pages


# ── small parsers (rules path) ────────────────────────────────────────────────

MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), start=1)}
DATE_RE = re.compile(
    r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"                        # 2024-03-11 (ISO)
    r"|\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b"          # 11/03/2024, 14-08-26
    r"|\b(\d{1,2})[\s\-]([A-Za-z]{3})[a-z]*[\s\-,]+(\d{2,4})\b"  # 20 Sep 2024, 14-Aug-26
)
TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})(?::\d{2})?\s*([AaPp]\.?[Mm]\.?)?")
COLLECT_RE = re.compile(r"collect|sample|drawn", re.I)


def _iso(day: int, month: int, year: int) -> str | None:
    if year < 100:
        year += 2000
    if 1 <= month <= 12 and 1 <= day <= 31 and 1990 <= year <= 2100:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def parse_date(s: str) -> str | None:
    """First date in s (ISO, else day-first) as YYYY-MM-DD."""
    for m in DATE_RE.finditer(s):
        if m.group(1):
            d = _iso(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        elif m.group(4):
            d = _iso(int(m.group(4)), int(m.group(5)), int(m.group(6)))
        else:
            mon = MONTHS.get(m.group(8).lower()[:3])
            d = _iso(int(m.group(7)), mon, int(m.group(9))) if mon else None
        if d:
            return d
    return None


def parse_time(s: str) -> str | None:
    """First clock time in s as 24-hour HH:MM."""
    m = TIME_RE.search(s)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    ampm = (m.group(3) or "").lower().replace(".", "")
    if ampm == "pm" and h < 12:
        h += 12
    if ampm == "am" and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else None


def _tidy(name: str) -> str:
    """Strip and title-case names printed in ALL CAPS."""
    name = re.sub(r"\s+", " ", name).strip(" ,:-")
    return name.title() if name.isupper() else name


NULLISH = {"", "none", "null", "n/a", "na", "-", "nil"}


def clean_person(name: str | None) -> str | None:
    """'Mr. RAMESH KUMAR (58Y/M)' → 'Ramesh Kumar'."""
    if not name or str(name).strip().lower() in NULLISH:
        return None
    name = re.sub(r"[(\[].*?[)\]]", " ", str(name))
    name = re.sub(r"^\s*(?:mr|mrs|ms|miss|smt|shri|master|baby)\.?\s+", "", name, flags=re.I)
    return _tidy(name) or None


def clean_lab(lab: str | None) -> str | None:
    """'SUNRISE DIAGNOSTICS · NABL accredited …' → 'Sunrise Diagnostics'."""
    if not lab or str(lab).strip().lower() in NULLISH:
        return None
    return _tidy(re.split(r"\s[·|]\s|\s[-–]\s|,\s", str(lab))[0]) or None


def clean_unit_range(unit, rng) -> tuple[str | None, str | None]:
    """Fix a unit that is really a range (or 'None'), as models sometimes return."""
    unit = None if unit is None or str(unit).strip().lower() in NULLISH else str(unit).strip()
    rng = None if rng is None or str(rng).strip().lower() in NULLISH else str(rng).strip()
    if unit:
        m = re.match(r"^(\S*?)\s*[(\[]([^)\]]*)[)\]]$", unit)
        if m:                                   # "mg/dL (0.6 - 1.3)" or "(70-100)"
            unit, rng = m.group(1) or None, rng or m.group(2).strip()
        elif RANGE_RE.match(unit):              # "70-100" in the unit slot
            unit, rng = None, rng or unit
    if rng:
        rng = rng.strip("()[] ") or None
    return unit, rng


PERSON_RE = re.compile(
    r"(?:patient\s*name|pt\.?\s*name|patient|name)\s*[:\-]\s*"
    r"(?:(?:mr|mrs|ms|miss|smt|shri|master|baby)\.?\s+)?"
    r"([A-Za-z][A-Za-z.' ]*?)(?=\s{2,}|\s+(?:age|sex|gender|date|uhid|ref)\b|\s*[(\[,|]|$)",
    re.I | re.M,
)


def parse_person(text: str) -> str | None:
    m = PERSON_RE.search(text)
    return clean_person(m.group(1)) if m else None


# A value line: "<name> [: or ....] <value> [unit] [range]"
LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9 .()/%,'&+\-]*?)\s*:?\s+"
    r"(?P<value>[<>]?\s?\d[\d,]*(?:\.\d+)?)(?![\d/:\-])\s*(?P<rest>.*)$"
)
UNIT_RE = re.compile(r"^(?:[a-zA-Zµμ%][\w/%µμ.^*]*|/[\w.]+)$")
RANGE_RE = re.compile(
    r"^(?:[<>≤≥]=?\s*\d[\d,]*(?:\.\d+)?"
    r"|\d[\d,]*(?:\.\d+)?\s*(?:-|–|to)\s*\d[\d,]*(?:\.\d+)?)$", re.I)
BULLET_RE = re.compile(r"^(?:\(cid:\d+\)|[•●▪◦·*\-–])\s*")      # "(cid:127) FBS : 6.1 …"
REF_RE = re.compile(r"^(?:ref(?:erence)?\.?(?:\s*range)?|normal(?:\s*range)?)\s*[:\-]?\s*", re.I)
FLAG_WORDS = {"h", "l", "high", "low", "*", "**", "abnormal"}
NOT_A_TEST = re.compile(
    r"\b(name|age|sex|gender|date|sample|collected|collection|reported|report|page|ref|"
    r"patient|time|phone|mobile|barcode|review|visit|uhid|dr|tab|cap|syp)\b", re.I)


def parse_line(line: str) -> dict | None:
    """One text line → {test, value, unit, range} as printed, or None."""
    line = re.sub(r"\.{2,}", " : ", line).strip()
    line = BULLET_RE.sub("", line)
    m = LINE_RE.match(line)
    if not m:
        return None
    name = m.group("name").strip(" :.-")
    if len(name) < 2 or NOT_A_TEST.search(name):
        return None
    rest = m.group("rest").strip()
    tokens = rest.split()
    unit = None
    if tokens and UNIT_RE.match(tokens[0]) and tokens[0].lower() not in FLAG_WORDS:
        unit, rest = tokens[0], " ".join(tokens[1:])
    rest = " ".join(t for t in rest.split() if t.lower() not in FLAG_WORDS)
    rng = REF_RE.sub("", rest.strip().strip("()[]")).strip() or None
    if rng and not RANGE_RE.match(rng):
        return None          # leftover words → not a result line (e.g. "Review after 1 month …")
    return {"test": name, "value": m.group("value").replace(" ", ""), "unit": unit, "range": rng}


def parse_table_row(row: str) -> dict | None:
    """'Test | 112 | mg/dL | 70 - 100' → value dict (columns: test, result, unit, range)."""
    cells = [c.strip() for c in row.split("|")]
    if len(cells) < 2 or not re.match(r"^[<>]?\s?\d[\d,]*(?:\.\d+)?$", cells[1]):
        return None
    return {"test": cells[0], "value": cells[1].replace(" ", ""),
            "unit": (cells[2] if len(cells) > 2 else "") or None,
            "range": (cells[3] if len(cells) > 3 else "") or None}


MED_RE = re.compile(
    r"\b(?:tab|tablet|cap|capsule|syp|syrup|inj)\.?\s+([A-Za-z][A-Za-z\-]*(?:\s+[A-Za-z][A-Za-z\-]*)*)", re.I)
# "1. Metformin 500 mg — 1 tab …", "2) Uprise D3 60,000 IU …" (numbered Rx list)
NUMBERED_MED_RE = re.compile(
    r"^\s*\d{1,2}[.)]\s+([A-Za-z][A-Za-z\-]*(?:\s+[A-Za-z][A-Za-z0-9\-]*)*)", re.M)
DOSE_WORDS = {"od", "bd", "tds", "qid", "hs", "sos", "mg", "mcg", "ml", "x", "days", "before",
              "after", "food", "daily", "once", "twice"}


def parse_medicines(text: str) -> list[dict]:
    meds = []
    rx = re.search(r"^\s*(rx|℞)\b", text, re.I | re.M)
    numbered = list(NUMBERED_MED_RE.finditer(text, rx.end())) if rx else []
    for m in [*MED_RE.finditer(text), *numbered]:
        words = []
        for w in m.group(1).split():
            if w.lower() in DOSE_WORDS:
                break
            words.append(w)
        name = " ".join(words)
        if name and name.lower() not in {x["name"].lower() for x in meds}:
            meds.append({"name": name})
    return meds


def parse_lab(pages: list[str], kind: str) -> str | None:
    lines = [ln.strip() for ln in pages[0].splitlines() if ln.strip()] if pages else []
    if kind == "prescription":
        for ln in lines:
            if re.search(r"clinic|hospital|nursing|centre|center|polyclinic", ln, re.I):
                return _tidy(re.split(r"[·,|]", ln)[0])
    return _tidy(re.split(r"[·|]", lines[0])[0]) if lines else None


# ── the two readers ───────────────────────────────────────────────────────────


def read_rules(pages: list[str]) -> ExtractedReport:
    """Regex reader: works with no LLM so the demo never dies."""
    text = "\n".join(pages)
    meds = parse_medicines(text)
    rx = bool(re.search(r"^\s*(rx|℞)\b", text, re.I | re.M))
    values = []
    for n, page in enumerate(pages, start=1):
        body, _, table = page.partition(f"\n{TABLE_MARK}\n")
        rows = [parse_table_row(r) for r in table.splitlines()] if table else []
        rows += [] if table else [parse_line(ln) for ln in body.splitlines()]
        values += [{**v, "page": n} for v in rows if v]
    kind = "prescription" if (rx or meds) and len(values) < 3 else "lab"
    if kind == "prescription":
        values = []
    collect_line = next((ln for ln in text.splitlines() if COLLECT_RE.search(ln)), None)
    date = None
    time = None
    if collect_line:
        tail = collect_line[COLLECT_RE.search(collect_line).start():]
        date, time = parse_date(tail), parse_time(tail)
    if not date:
        date = parse_date(text)
    if not time and kind == "lab":
        time_line = next((ln for ln in text.splitlines() if re.search(r"time", ln, re.I)), "")
        time = parse_time(time_line[re.search(r"time", time_line, re.I).start():]) if time_line else None
    return {
        "kind": kind,
        "person": parse_person(text),
        "date": date,
        "collected_time": time if kind == "lab" else None,
        "lab": parse_lab(pages, kind),
        "values": values,
        "medicines": meds if kind == "prescription" else [],
    }


def _system_prompt() -> str:
    lines = EXTRACT_PROMPT.read_text().splitlines()
    return "\n".join(ln for ln in lines if not ln.startswith("#")).strip()


def _check(out: dict) -> tuple[ExtractedReport | None, str | None]:
    """Normalise an LLM reply to ExtractedReport. Returns (report, error)."""
    if not isinstance(out, dict):
        return None, "reply was not a JSON object"
    if out.get("kind") not in ("lab", "prescription"):
        return None, 'kind must be "lab" or "prescription"'
    if not isinstance(out.get("values", []), list) or not isinstance(out.get("medicines", []), list):
        return None, "values and medicines must be lists"
    values = []
    for v in out.get("values") or []:
        if not isinstance(v, dict) or not v.get("test") or v.get("value") in (None, ""):
            continue
        try:
            page = int(v.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        value = str(v["value"]).strip()
        unit, rng = clean_unit_range(v.get("unit"), v.get("range"))
        m = re.match(r"^([<>]?\s?\d[\d,]*(?:\.\d+)?)\s+(\S+)$", value)
        if m:                                   # "7.2 %" → value "7.2", unit "%"
            value, unit = m.group(1), unit or m.group(2)
        if unit and rng and unit.strip("()[] ") == rng:
            unit = None                         # range copied into the unit slot
        test = BULLET_RE.sub("", str(v["test"]).strip())   # model copies "(cid:127) TSH" as printed
        values.append({"test": test, "value": value.replace(" ", ""),
                       "unit": unit, "range": rng, "page": page})
    meds = []
    for m in out.get("medicines") or []:
        name = m.get("name") if isinstance(m, dict) else m
        if name:
            meds.append({"name": parse_medicines(f"Tab. {name}")[0]["name"]
                         if parse_medicines(f"Tab. {name}") else str(name).strip()})
    date = out.get("date")
    time = out.get("collected_time")
    return {
        "kind": out["kind"],
        "person": clean_person(out.get("person")),
        "date": date if isinstance(date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else None,
        "collected_time": time if isinstance(time, str) and re.fullmatch(r"\d{2}:\d{2}", time) else None,
        "lab": clean_lab(out.get("lab")),
        "values": values if out["kind"] == "lab" else [],
        "medicines": meds if out["kind"] == "prescription" else [],
    }, None


def read_llm(pages: list[str]) -> ExtractedReport | None:
    """Local-LLM reader. One retry with the error message; None if it still fails."""
    if not llm.available():
        return None
    doc = "\n\n".join(f"=== PAGE {n} ===\n{p}" for n, p in enumerate(pages, start=1))
    system = _system_prompt()
    user = doc
    for _ in range(2):
        report, error = _check(llm.chat_json(system, user))
        if report:
            return report
        user = f"{doc}\n\nYour previous reply was invalid: {error}. Reply with JSON only, in the exact shape."
    return None


def extract(path: str | Path, mode: str = "auto") -> ExtractedReport:
    """PDF → ExtractedReport. mode: auto | llm | rules."""
    pages = read_pdf(path)
    rules = read_rules(pages)
    if mode == "rules":
        return rules
    model = read_llm(pages)
    if mode == "llm":
        return model or {**rules, "values": [], "medicines": []}
    if model is None:
        return rules
    # auto: trust the model, but not if it skipped most of what rules could see
    if len(model["values"]) < len(rules["values"]) / 2:
        return rules
    for key in ("person", "date", "collected_time", "lab"):
        model[key] = model[key] or rules[key]
    return model
