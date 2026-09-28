"""Reasoning: trends, flags and data-quality caveats. Plain Python, NO LLM.

OWNER: Reasoning & Submission role
LANGUAGE / LIBS: Python 3.12, PyYAML, statistics, datetime. No LLM, no numpy needed.

GOAL
  Turn a person's stored values + medicines into a Timeline (src/contracts.py):
  one series per test for the chart, a list of flags for the cards, and
  data-quality caveats. This is where the demo's "wow" moment comes from.

FUNCTIONS
  drug_class(name) -> str | None
  trend(points) -> dict
  timeline(store, person_id) -> Timeline | None

DONE WHEN
  pytest -q tests/test_reason.py passes, and on the fake data Ramesh gets ≥ 3
  flags including the metformin one.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from functools import lru_cache

import yaml

from src import DATA
from src.contracts import Flag, Point, Series, Timeline

RULES_FILE = DATA / "rules.yaml"
MEDICINES_FILE = DATA / "medicines.yaml"


# ── helpers ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_medicines() -> dict[str, list[str]]:
    """Load medicines.yaml once: {drug_class: [alias, ...]}."""
    with open(MEDICINES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def _load_rules() -> list[dict]:
    """Load rules.yaml once."""
    with open(RULES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _parse_date(s: str) -> date:
    """Parse 'YYYY-MM-DD' to a date object."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def _within_10pct(value: float, limit: float) -> bool:
    """True if value is within 10% of limit (measured from the limit)."""
    if limit == 0:
        return abs(value) < 0.1
    return abs(value - limit) / abs(limit) <= 0.10


# ── public API ───────────────────────────────────────────────────────────────

def drug_class(name: str) -> str | None:
    """Look the medicine name up in data/medicines.yaml (case-insensitive).

    Also match if an alias is a word inside the name, so
    "Tab Glycomet GP" matches "glycomet" → "biguanide".
    """
    meds = _load_medicines()
    lower = name.lower()
    for cls, aliases in meds.items():
        for alias in aliases:
            # alias can be multi-word ("vitamin d3"), check if it appears in the name
            if alias in lower:
                return cls
    return None


def trend(points: list[dict]) -> dict:
    """Compute trend over ≥ 3 points (oldest first).

    Hand-written least-squares slope per year.
    Returns {"direction", "slope", "change", "years"}.
    """
    if len(points) < 3:
        return {"direction": "flat", "slope": 0.0, "change": 0.0, "years": 0.0}

    d0 = _parse_date(points[0]["date"])
    # x = years from first point, y = value
    xs = [(_parse_date(p["date"]) - d0).days / 365.25 for p in points]
    ys = [p["value"] for p in points]

    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)

    denom = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / denom if denom != 0 else 0.0

    change = ys[-1] - ys[0]
    years = xs[-1]

    # "flat" if |total change| < 5% of the first value
    first = ys[0] if ys[0] != 0 else 1.0  # avoid division by zero
    if abs(change) < 0.05 * abs(first):
        direction = "flat"
    elif change > 0:
        direction = "rising"
    else:
        direction = "falling"

    return {"direction": direction, "slope": slope, "change": change, "years": years}


def timeline(store, person_id: int) -> Timeline | None:
    """Build the full Timeline for a person: series, flags, caveats."""
    person = store.person(person_id)
    if person is None:
        return None

    try:
        from src.standard import catalogue
        cat = catalogue()
    except (ImportError, NotImplementedError):
        with open(DATA / "tests.yaml", encoding="utf-8") as f:
            cat = yaml.safe_load(f) or {}
    rows = store.results(person_id)
    meds = store.medicines(person_id)
    reports = store.reports(person_id)

    # ── 1. Series: group rows by test_id ─────────────────────────────────
    by_test: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_test[r["test_id"]].append(r)

    series_list: list[Series] = []
    for test_id, test_rows in by_test.items():
        info = cat.get(test_id, {})
        points: list[Point] = []
        for r in test_rows:
            points.append({
                "date": r["report_date"] or "",
                "value": r["value"],
                "source": f"{r['filename']}#p{r['page']}",
            })
        series_list.append({
            "test": info.get("name", test_id),
            "test_id": test_id,
            "unit": info.get("unit", r.get("unit", "")),
            "normal": info.get("range", [None, None]),
            "points": points,
        })

    # ── 2. Flags ─────────────────────────────────────────────────────────
    flags: list[Flag] = []
    flagged_tests: set[str] = set()  # avoid double-flagging

    # 2a. Cross-document flags (MOST IMPORTANT)
    rules = _load_rules()
    for rule in rules:
        # Does the person take a medicine of this drug_class?
        matching_meds = [m for m in meds if m.get("drug_class") == rule["drug_class"]]
        if not matching_meds:
            continue

        med = matching_meds[0]
        med_start = med.get("start_date")
        rx_file = med.get("filename", "prescription")

        for when in rule["when"]:
            test_id = when["test"]
            if test_id not in by_test:
                continue

            test_rows = by_test[test_id]
            info = cat.get(test_id, {})
            normal = info.get("range", [None, None])
            unit = info.get("unit", "")

            # Filter readings: from the last one before medicine start onwards
            if med_start:
                relevant = []
                last_before = None
                for r in test_rows:
                    rd = r.get("report_date", "")
                    if rd and rd < med_start:
                        last_before = r
                    else:
                        relevant.append(r)
                if last_before:
                    relevant.insert(0, last_before)
                if not relevant:
                    relevant = test_rows
            else:
                relevant = test_rows

            condition = when["condition"]
            fired = False

            if condition in ("rising", "falling"):
                if len(relevant) >= 3:
                    pts = [{"date": r["report_date"], "value": r["value"]}
                           for r in relevant if r.get("report_date")]
                    if len(pts) >= 3:
                        t = trend(pts)
                        if t["direction"] == condition:
                            fired = True
            elif condition == "above":
                if relevant:
                    latest = relevant[-1]["value"]
                    if normal[1] is not None and latest > normal[1]:
                        fired = True
            elif condition == "below":
                if relevant:
                    latest = relevant[-1]["value"]
                    if normal[0] is not None and latest < normal[0]:
                        fired = True

            if fired:
                # Build detail string from the data
                vals = [r["value"] for r in relevant if r.get("report_date")]
                if len(vals) >= 2:
                    detail_str = (f"{info.get('name', test_id)} "
                                  f"{vals[0]} → {vals[-1]} {unit}")
                else:
                    detail_str = (f"{info.get('name', test_id)} "
                                  f"{vals[-1]} {unit}")

                lab_files = list({r["filename"] for r in relevant
                                  if r.get("filename")})
                sources = lab_files + ([rx_file] if rx_file not in lab_files
                                       else [])

                flags.append({
                    "level": rule["level"],
                    "title": rule["title"],
                    "detail": detail_str,
                    "ask_doctor": rule["ask"],
                    "sources": sources,
                })
                flagged_tests.add(test_id)
                break  # one flag per rule

    # 2b. Trend flags
    for test_id, test_rows in by_test.items():
        if test_id in flagged_tests:
            continue
        if len(test_rows) < 3:
            continue

        info = cat.get(test_id, {})
        normal = info.get("range", [None, None])
        bad_dir = info.get("bad", None)
        unit = info.get("unit", "")

        pts = [{"date": r["report_date"], "value": r["value"]}
               for r in test_rows if r.get("report_date")]
        if len(pts) < 3:
            continue

        t = trend(pts)
        if bad_dir and t["direction"] == ("rising" if bad_dir == "high" else
                                           "falling" if bad_dir == "low" else ""):
            latest = pts[-1]["value"]
            out_of_range = False
            near_limit = False

            if normal[1] is not None and latest > normal[1]:
                out_of_range = True
            if normal[0] is not None and latest < normal[0]:
                out_of_range = True
            if normal[1] is not None and _within_10pct(latest, normal[1]):
                near_limit = True
            if normal[0] is not None and _within_10pct(latest, normal[0]):
                near_limit = True

            if out_of_range or near_limit:
                level = "red" if out_of_range else "amber"
                months = int(t["years"] * 12)
                detail_str = (f"{info.get('name', test_id)} "
                              f"{pts[0]['value']} → {pts[-1]['value']}{unit} "
                              f"over {months} months")
                ask = info.get("ask", f"Should {info.get('name', test_id)} "
                               "be discussed at the next visit?")

                flags.append({
                    "level": level,
                    "title": f"{info.get('name', test_id)} trending "
                             f"{t['direction']}",
                    "detail": detail_str,
                    "ask_doctor": ask,
                    "sources": list({r["filename"] for r in test_rows
                                     if r.get("filename")}),
                })
                flagged_tests.add(test_id)

    # 2c. Out-of-range flags (latest reading outside range, not already flagged)
    for test_id, test_rows in by_test.items():
        if test_id in flagged_tests:
            continue
        info = cat.get(test_id, {})
        normal = info.get("range", [None, None])
        unit = info.get("unit", "")

        latest_row = test_rows[-1]
        latest = latest_row["value"]
        status = "normal"
        if normal[0] is not None and latest < normal[0]:
            status = "low"
        if normal[1] is not None and latest > normal[1]:
            status = "high"

        if status != "normal":
            ask = info.get("ask", f"Should {info.get('name', test_id)} "
                           "be discussed at the next visit?")
            flags.append({
                "level": "amber",
                "title": f"{info.get('name', test_id)} is {status}",
                "detail": f"{info.get('name', test_id)} "
                          f"{latest} {unit} "
                          f"(normal: {normal[0]}–{normal[1]})",
                "ask_doctor": ask,
                "sources": [latest_row["filename"]]
                           if latest_row.get("filename") else [],
            })
            flagged_tests.add(test_id)

    # 2d. Good-news flags (was out of range, now back inside)
    for test_id, test_rows in by_test.items():
        if test_id in flagged_tests:
            continue
        if len(test_rows) < 2:
            continue

        info = cat.get(test_id, {})
        normal = info.get("range", [None, None])
        unit = info.get("unit", "")

        prev = test_rows[-2]["value"]
        latest = test_rows[-1]["value"]

        prev_out = False
        if normal[0] is not None and prev < normal[0]:
            prev_out = True
        if normal[1] is not None and prev > normal[1]:
            prev_out = True

        latest_in = True
        if normal[0] is not None and latest < normal[0]:
            latest_in = False
        if normal[1] is not None and latest > normal[1]:
            latest_in = False

        if prev_out and latest_in:
            flags.append({
                "level": "green",
                "title": f"{info.get('name', test_id)} is back to normal",
                "detail": f"{info.get('name', test_id)} "
                          f"{prev} → {latest} {unit}",
                "ask_doctor": f"Is {info.get('name', test_id)} now stable?",
                "sources": list({r["filename"] for r in test_rows[-2:]
                                 if r.get("filename")}),
            })

    # Sort flags: red → amber → green
    level_order = {"red": 0, "amber": 1, "green": 2}
    flags.sort(key=lambda f: level_order.get(f["level"], 9))

    # ── 3. Caveats ───────────────────────────────────────────────────────
    caveats: list[str] = []

    # Late fasting sample
    for r in rows:
        if r["test_id"] and r["test_id"].startswith("glucose_fasting"):
            # Find the report to get collected_time
            for rpt in reports:
                if rpt.get("id") == r.get("report_id"):
                    ct = rpt.get("collected_time")
                    if ct and ct > "10:00":
                        caveats.append(
                            f"The fasting sample on {rpt.get('report_date', '?')} "
                            f"was collected at {ct}, so it may not be a true "
                            f"fasting value."
                        )
                    break

    # Duplicate reports (same date + lab)
    seen_date_lab: dict[tuple, str] = {}
    for rpt in reports:
        key = (rpt.get("report_date"), rpt.get("lab"))
        if key[0] and key[1] and key in seen_date_lab:
            caveats.append(
                f"Reports '{seen_date_lab[key]}' and '{rpt.get('filename', '?')}' "
                f"have the same date and lab — possible duplicate."
            )
        elif key[0] and key[1]:
            seen_date_lab[key] = rpt.get("filename", "?")

    # Guessed units
    for r in rows:
        if r.get("guessed"):
            info = cat.get(r["test_id"], {})
            caveats.append(
                f"Unit for {info.get('name', r['test_id'])} on "
                f"{r.get('report_date', '?')} was not printed and was inferred."
            )

    return {
        "person": person["name"],
        "person_id": person_id,
        "series": series_list,
        "flags": flags,
        "caveats": caveats,
    }
