"""SQLite storage. One local file; every value keeps its source report and page.

OWNER: Data & Standards role — name: ________ (fill in when you pick this)
LANGUAGE / LIBS: Python 3.12, built-in `sqlite3` only. No ORM (no SQLAlchemy).

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py + docs/interfaces.md
(the "SQLite tables" section) into your AI, then say:
"Implement src/store.py exactly as described. Only edit this file."

GOAL
  Save people, reports, lab results and medicines in one SQLite file at
  vault_data/vault.db, and read them back for reason.py and api.py.

SCHEMA  (write it as one SCHEMA string with CREATE TABLE IF NOT EXISTS)
  people    (id INTEGER PK, name TEXT NOT NULL)
  reports   (id INTEGER PK, person_id → people, filename, stored_path,
             sha256 TEXT UNIQUE, kind TEXT  -- 'lab' | 'prescription',
             lab, report_date, collected_time, uploaded_at DEFAULT now)
  results   (id INTEGER PK, report_id → reports ON DELETE CASCADE, test_id,
             value REAL, unit, raw_test, raw_value, raw_unit, page INTEGER,
             guessed INTEGER)
  medicines (id INTEGER PK, report_id → reports ON DELETE CASCADE, person_id,
             name, drug_class, start_date)
  Turn on `PRAGMA foreign_keys = ON`. Use `row_factory = sqlite3.Row` and
  return plain dicts (dict(row)), never Row objects.

CLASS  Store(home: Path | None = None)   (home defaults to src.VAULT_DIR;
       tests pass a tmp_path so they never touch the real vault)
  people() -> list[dict]                          [{id, name, reports}]
  person(person_id) -> dict | None
  find_or_create_person(name) -> int              case-insensitive match on name;
                                                  "RAMESH KUMAR" == "Ramesh Kumar"
  report_by_hash(sha256) -> dict | None           for duplicate-upload detection
  add_report(person_id, filename, stored_path, sha256, kind, lab,
             report_date, collected_time) -> int
  add_result(report_id, v: StandardValue) -> None
  add_medicine(report_id, person_id, name, drug_class, start_date) -> None
  results(person_id) -> list[dict]                joined with reports: each row has
                                                  test_id, value, unit, page,
                                                  report_date, filename; oldest first
  medicines(person_id) -> list[dict]
  reports(person_id) -> list[dict]
  delete_report(report_id) -> bool

RULES
  - Parameterised queries only (`?` placeholders), never f-strings in SQL.
  - Call conn.commit() after writes.
  - Store only what is listed above. Never store doses.

DONE WHEN
  pytest -q tests/test_store.py passes.
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src import VAULT_DIR
from src.contracts import StandardValue

SCHEMA = """
-- TODO(DATA): CREATE TABLE IF NOT EXISTS people / reports / results / medicines
"""


class Store:
    def __init__(self, home: str | Path | None = None):
        self.home = Path(home) if home else VAULT_DIR
        self.home.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.home / "vault.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # TODO(DATA): PRAGMA foreign_keys, executescript(SCHEMA)

    def people(self) -> list[dict]:
        raise NotImplementedError  # TODO(DATA)

    def person(self, person_id: int) -> dict | None:
        raise NotImplementedError  # TODO(DATA)

    def find_or_create_person(self, name: str) -> int:
        raise NotImplementedError  # TODO(DATA)

    def report_by_hash(self, sha256: str) -> dict | None:
        raise NotImplementedError  # TODO(DATA)

    def add_report(self, person_id: int, filename: str, stored_path: str, sha256: str,
                   kind: str, lab: str | None, report_date: str | None,
                   collected_time: str | None) -> int:
        raise NotImplementedError  # TODO(DATA)

    def add_result(self, report_id: int, v: StandardValue) -> None:
        raise NotImplementedError  # TODO(DATA)

    def add_medicine(self, report_id: int, person_id: int, name: str,
                     drug_class: str | None, start_date: str | None) -> None:
        raise NotImplementedError  # TODO(DATA)

    def results(self, person_id: int) -> list[dict]:
        raise NotImplementedError  # TODO(DATA)

    def medicines(self, person_id: int) -> list[dict]:
        raise NotImplementedError  # TODO(DATA)

    def reports(self, person_id: int) -> list[dict]:
        raise NotImplementedError  # TODO(DATA)

    def delete_report(self, report_id: int) -> bool:
        raise NotImplementedError  # TODO(DATA)
