"""Accuracy test: how many values does extraction + standardization read correctly?

OWNER: Extraction role — name: ________ (fill in when you pick this)
LANGUAGE / LIBS: Python 3.12, json, argparse.
RUN: python tools/accuracy.py [--mode auto|llm|rules] [-v]

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
from src import SAMPLES  # noqa: E402
from src.extract import extract  # noqa: E402
from src.standard import standardize  # noqa: E402


def main() -> None:
    raise NotImplementedError  # TODO(EXTRACT)


if __name__ == "__main__":
    main()
