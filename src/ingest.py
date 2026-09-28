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
  4. Copy the PDF to <store.home> / "files" / f"{sha[:12]}.pdf"  (store.home is VAULT_DIR
     by default; tests use a temp dir so they never touch the real vault)
  5. report_id = store.add_report(...)
  6. Lab: for each raw value → standard.standardize(raw); skip None;
     store.add_result(report_id, v). Count saved values.
     Prescription: for each medicine → store.add_medicine(report_id, person_id,
     name, reason.drug_class(name), report["date"]).
  7. Return ok=True with a message like "Read 14 values for Ramesh Kumar (14 Aug 2026)."

RULES
  - Never raise to the API: catch exceptions and return ok=False with the message.

DONE WHEN
  tests/test_ingest.py passes (stand-ins for standard/store/reason), and
  tests/test_api.py::test_upload_sample passes once those modules are merged.
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
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _nice(d: str | None) -> str:
    """'2026-08-14' → '14 Aug 2026'."""
    if not d:
        return "no date"
    y, m, day = d.split("-")
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{int(day)} {months[int(m) - 1]} {y}"


def _result(filename: str, ok: bool, message: str, **kw) -> UploadResult:
    return {"filename": filename, "ok": ok, "report_id": kw.get("report_id"),
            "person_id": kw.get("person_id"), "kind": kw.get("kind"),
            "values_saved": kw.get("values_saved", 0), "message": message}


def _drug_class(name: str) -> str | None:
    """reason.drug_class, but a missing class never loses the prescription."""
    try:
        return reason.drug_class(name)
    except Exception:
        return None


def ingest(store: Store, path: str | Path, filename: str | None = None) -> UploadResult:
    """One PDF → extracted → standardized → saved. Never raises."""
    path = Path(path)
    filename = filename or path.name
    try:
        sha = sha256(path)
        seen = store.report_by_hash(sha)
        if seen:
            return _result(filename, False, f"Already in the vault (uploaded as {seen['filename']}).",
                           report_id=seen["id"], person_id=seen.get("person_id"))

        report = extract.extract(path)
        if not report["person"]:
            return _result(filename, False, "Couldn't find a patient name on this report.",
                           kind=report["kind"])
        person_id = store.find_or_create_person(report["person"])

        files = Path(getattr(store, "home", VAULT_DIR)) / "files"
        files.mkdir(parents=True, exist_ok=True)
        stored = files / f"{sha[:12]}.pdf"
        shutil.copyfile(path, stored)

        report_id = store.add_report(person_id, filename, str(stored), sha, report["kind"],
                                     report["lab"], report["date"], report["collected_time"])
        saved = 0
        if report["kind"] == "lab":
            for raw in report["values"]:
                v = standard.standardize(raw)
                if v:
                    store.add_result(report_id, v)
                    saved += 1
            what = f"{saved} value{'s' if saved != 1 else ''}"
        else:
            for m in report["medicines"]:
                store.add_medicine(report_id, person_id, m["name"],
                                   _drug_class(m["name"]), report["date"])
            n = len(report["medicines"])
            what = f"{n} medicine{'s' if n != 1 else ''}"
        return _result(filename, True, f"Read {what} for {report['person']} ({_nice(report['date'])}).",
                       report_id=report_id, person_id=person_id, kind=report["kind"],
                       values_saved=saved)
    except Exception as e:  # never raise to the API
        return _result(filename, False, f"Couldn't read this file: {e or type(e).__name__}")
