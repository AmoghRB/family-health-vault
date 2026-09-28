"""Accuracy test: how many values does extraction + standardization read correctly?

OWNER: Extraction (Person 2): Amogh R B
LANGUAGE / LIBS: Python 3.12, json, argparse.
RUN: python tools/accuracy.py [--set samples|fixtures] [--mode auto|llm|rules] [-v]

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py into your AI, then say:
"Implement tools/accuracy.py exactly as described. Only edit this file."

GOAL
  Produce the accuracy number that goes on the final slide.

STEPS
  1. Load samples/ground_truth.json (made by tools/make_fake_reports.py).
  2. For each PDF listed: report = extract(path, mode); standardize each raw
     value; build {test_id: value}.
  3. A value is correct if the test_id matches and |got − expected| ≤ 1% of
     expected. Count: correct, wrong (value off), missed (in truth, not read),
     extra (read, not in truth).
  4. Print a table per file with -v, then the total:
       "Accuracy (rules): 172/180 = 95.6%   missed 5 · wrong 3 · extra 1"
  5. Exit code 0 if accuracy ≥ 95%, else 1.

TWO SETS
  --set samples   Person 1's full fake set (samples/ground_truth.json, canonical
                  values by test_id): scores extract + standardize together.
  --set fixtures  Person 2's small set (tests/fixtures/truth.json, values AS
                  PRINTED): scores extraction alone, works before standard.py exists.
                  A value is correct if test name, value and unit all match.
  Default: samples if its ground truth exists, else fixtures.
  Header fields (kind, person, date, collected_time, lab) are scored too.

DONE WHEN
  Running it on the fake reports prints ≥ 95% for --mode auto.
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import ROOT, SAMPLES  # noqa: E402
from src.extract import extract  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
HEADER = ("kind", "person", "date", "collected_time", "lab")


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", "").lstrip("<>").strip())
    except ValueError:
        return None


def _close(got, exp) -> bool:
    g, e = _num(got), _num(exp)
    return g is not None and e is not None and abs(g - e) <= 0.01 * abs(e) + 1e-9


def score_printed(truth: dict, report: dict) -> tuple[int, int, int, int, list[str]]:
    """Fixtures: compare values as printed, keyed by test name."""
    exp = {v["test"].lower(): v for v in truth["values"]}
    got = {v["test"].lower(): v for v in report["values"]}
    ok = wrong = 0
    notes = []
    for k, e in exp.items():
        g = got.get(k)
        if g is None:
            continue
        if _close(g["value"], e["value"]) and (g["unit"] or "") == (e["unit"] or ""):
            ok += 1
        else:
            wrong += 1
            notes.append(f"wrong  {e['test']}: got {g['value']} {g['unit']}, want {e['value']} {e['unit']}")
    missed = [e["test"] for k, e in exp.items() if k not in got]
    extra = [g["test"] for k, g in got.items() if k not in exp]
    notes += [f"missed {t}" for t in missed] + [f"extra  {t}" for t in extra]
    return ok, wrong, len(missed), len(extra), notes


def score_canonical(truth: dict, report: dict) -> tuple[int, int, int, int, list[str]]:
    """Samples: standardize, then compare canonical values by test_id."""
    from src.standard import standardize
    exp = truth["values"]
    got = {}
    for raw in report["values"]:
        v = standardize(raw)
        if v:
            got[v["test_id"]] = v["value"]
    ok = sum(1 for k, e in exp.items() if k in got and _close(got[k], e))
    wrong = sum(1 for k, e in exp.items() if k in got and not _close(got[k], e))
    missed = [k for k in exp if k not in got]
    extra = [k for k in got if k not in exp]
    notes = [f"wrong  {k}: got {got[k]}, want {e}" for k, e in exp.items() if k in got and not _close(got[k], e)]
    notes += [f"missed {k}" for k in missed] + [f"extra  {k}" for k in extra]
    return ok, wrong, len(missed), len(extra), notes


def header_ok(truth: dict, report: dict) -> list[str]:
    bad = []
    for k in HEADER:
        if k in truth and str(report.get(k) or "").lower() != str(truth[k] or "").lower():
            bad.append(f"header {k}: got {report.get(k)!r}, want {truth[k]!r}")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--set", choices=["samples", "fixtures"])
    ap.add_argument("--mode", choices=["auto", "llm", "rules"], default="auto")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    which = a.set or ("samples" if (SAMPLES / "ground_truth.json").exists() else "fixtures")
    folder = SAMPLES if which == "samples" else FIXTURES
    truth_file = folder / ("ground_truth.json" if which == "samples" else "truth.json")
    truth_all = json.loads(truth_file.read_text())
    scorer = score_canonical if which == "samples" else score_printed

    tot = [0, 0, 0, 0]
    head_bad = head_all = 0
    for name, truth in truth_all.items():
        report = extract(folder / name, a.mode)
        ok, wrong, missed, extra, notes = scorer(truth, report)
        hb = header_ok(truth, report)
        head_bad += len(hb)
        head_all += sum(1 for k in HEADER if k in truth)
        tot = [x + y for x, y in zip(tot, (ok, wrong, missed, extra))]
        n = ok + wrong + missed
        if a.verbose:
            print(f"{name:42s} {ok:>3}/{n:<3} {'✓' if not notes and not hb else ''}")
            for line in hb + notes:
                print(f"    {line}")
    ok, wrong, missed, extra = tot
    n = ok + wrong + missed
    pct = 100 * ok / n if n else 0.0
    print(f"Accuracy ({which}, {a.mode}): {ok}/{n} = {pct:.1f}%   "
          f"missed {missed} · wrong {wrong} · extra {extra}   "
          f"header fields {head_all - head_bad}/{head_all}")
    sys.exit(0 if pct >= 95 else 1)


if __name__ == "__main__":
    main()
