"""Ingest: one uploaded PDF → extracted → standardized → saved. Glue between modules.

OWNER: Extraction (Person 2): Amogh R B
LANGUAGE / LIBS: Python 3.12, hashlib, shutil. Calls extract, standard, store, and
reason.drug_class (the Reasoning & Submission owner) for medicines.

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py into your AI, then say:
"Implement src/ingest.py exactly as described. Only edit this file."

FUNCTION  ingest(store, path, filename=None) -> UploadResult  (see src/contracts.py)
  1. sha256 of the file. If store.report_by_hash(sha) exists → return
     ok=False, message "Already in the vault (uploaded as <filename>)."
  2. report = extract.extract(path)
  3. If report["person"] is None → ok=False, "Couldn't find a patient name."
     person_id = store.find_or_create_person(report["person"])
  4. Copy the PDF to VAULT_DIR / "files" / f"{sha[:12]}.pdf"
  5. report_id = store.add_report(...)
  6. Lab: for each raw value → standard.standardize(raw); skip None;
     store.add_result(report_id, v). Count saved values.
     Prescription: for each medicine → store.add_medicine(report_id, person_id,
     name, reason.drug_class(name), report["date"]).
  7. Return ok=True with a message like "Read 14 values for Ramesh Kumar (14 Aug 2026)."

RULES
  - Never raise to the API: catch exceptions and return ok=False with the message.

DONE WHEN
  tests/test_api.py::test_upload_sample passes.
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from src import VAULT_DIR, extract, reason, standard
from src.contracts import UploadResult
from src.store import Store


def sha256(path: str | Path) -> str:
    raise NotImplementedError  # TODO(EXTRACT)


def ingest(store: Store, path: str | Path, filename: str | None = None) -> UploadResult:
    raise NotImplementedError  # TODO(EXTRACT)
