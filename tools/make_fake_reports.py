"""Generate synthetic lab reports + prescriptions as PDFs, with ground truth.

OWNER: Data & Standards role — name: ________ (fill in when you pick this)
LANGUAGE / LIBS: Python 3.12, ReportLab (reportlab.pdfgen.canvas), PyYAML, json.
RUN: python tools/make_fake_reports.py   → writes samples/*.pdf + samples/ground_truth.json

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md into your AI, then say:
"Implement tools/make_fake_reports.py exactly as described. Only edit this file."

GOAL
  We can't use real medical reports, so we generate realistic fake ones. They
  are (a) the demo data and (b) the accuracy test: extract.py reads these PDFs
  and tools/accuracy.py compares what it read against ground_truth.json.

WHAT TO GENERATE
  2 people:  "Ramesh Kumar" (58, diabetic, on metformin) and
             "Lakshmi Kumar" (54, thyroid, low vitamin D).
  12+ lab PDFs, dated between 2024-03 and 2026-08, in 3 different layouts:
    - "Sunrise Diagnostics"  → Apollo-style: bordered TABLE with columns
                                Test | Result | Unit | Reference Range
    - "ThyroPlus Labs"       → Thyrocare-style: LIST "TEST NAME ..... value unit"
    - "Sri Sai Clinical Lab" → plain local printout: "Blood Sugar F : 131",
                                some units NOT printed, dates as dd-mm-yy
  Units must differ between labs (glucose mg/dL in one, mmol/L in another;
  creatinine mg/dL vs µmol/L) so the standardizer has real work to do.
  2 prescription PDFs (one per person): doctor name, date, medicine names
  (Ramesh: Metformin 500mg, Atorvastatin 10mg; Lakshmi: Thyronorm 50mcg,
  Uprise D3). Doses are printed on the PDF (like real ones) but the extractor
  must ignore them.

  STORY THE DATA MUST TELL (the demo depends on it):
    - Ramesh: HbA1c rising 6.1 → 7.2 over the period; creatinine rising
      0.9 → 1.3 after metformin started (2024-10). This triggers the
      cross-document flag in reason.py.
    - Ramesh: one "fasting" sample collected at 11:40 (after 10 AM)
      → data-quality caveat.
    - Lakshmi: vitamin D low then improving after supplements (a green flag).

  Each report also carries: patient name, sample collection date AND time,
  lab name, a header/footer, and at least one page with 8–15 tests.

GROUND TRUTH  samples/ground_truth.json
  {"<filename>.pdf": {"kind": "lab", "person": "...", "date": "YYYY-MM-DD",
                      "values": {"<test_id>": <value in CANONICAL unit>, ...},
                      "medicines": ["metformin", ...]}}
  Store the canonical (mg/dL etc.) value, i.e. what standardize() should
  produce, so accuracy can be checked end to end.

RULES
  - Deterministic: use random.Random(42), same output every run.
  - Filenames: <firstname>_<YYYY-MM-DD>_<labslug>.pdf, e.g. ramesh_2026-08-14_srisai.pdf
  - Read test ids / units / conversion factors from data/tests.yaml, don't hardcode twice.

DONE WHEN
  Running the script writes ≥14 PDFs + ground_truth.json, and the PDFs look
  like three visibly different labs when opened.
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import DATA, SAMPLES  # noqa: E402


def main() -> None:
    raise NotImplementedError  # TODO(DATA)


if __name__ == "__main__":
    main()
