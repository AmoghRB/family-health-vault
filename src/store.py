"""SQLite storage. One local file; every value keeps its source report and page.
OWNER: Pankaj Kumar B S
LANGUAGE / LIBS: Python 3.12, built-in `sqlite3` only. No ORM (no SQLAlchemy).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

try:
    from src import VAULT_DIR
except ImportError:
    VAULT_DIR = Path(__file__).parent.parent / "vault_data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES people(id),
    filename TEXT NOT NULL,
    stored_path TEXT,
    sha256 TEXT UNIQUE,
    kind TEXT NOT NULL,
    lab TEXT,
    report_date TEXT,
    collected_time TEXT,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    test_id TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    raw_test TEXT,
    raw_value TEXT,
    raw_unit TEXT,
    page INTEGER,
    guessed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people(id),
    name TEXT NOT NULL,
    drug_class TEXT,
    start_date TEXT
);

CREATE TABLE IF NOT EXISTS doctor_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES people(id),
    question TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS saved_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES people(id),
    generated TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Store:
    def __init__(self, home: Path | str | None = None) -> None:
        if home is None:
            self.home = Path(VAULT_DIR)
        elif str(home) == ":memory:":
            self.home = Path(":memory:")
        else:
            self.home = Path(home)

        if str(self.home) != ":memory:":
            self.home.mkdir(parents=True, exist_ok=True)
            self.db_path = self.home / "vault.db"
        else:
            self.db_path = Path(":memory:")

        self.conn = self._get_connection()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def people(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT id, name FROM people ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]

    def person(self, person_id: int) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT id, name FROM people WHERE id = ?", (person_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def find_or_create_person(self, name: str) -> int:
        normalized = name.strip()
        # Case-insensitive name lookup (e.g. RAMESH KUMAR == Ramesh Kumar)
        cur = self.conn.execute(
            "SELECT id FROM people WHERE LOWER(name) = LOWER(?)", (normalized,)
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute("INSERT INTO people (name) VALUES (?)", (normalized,))
        self.conn.commit()
        return cur.lastrowid

    def report_by_hash(self, sha256: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM reports WHERE sha256 = ?", (sha256,))
        row = cur.fetchone()
        return dict(row) if row else None

    def add_report(
        self,
        person_id: int,
        filename: str,
        stored_path: str | None = None,
        sha256: str | None = None,
        kind: str = "lab",
        lab: str | None = None,
        date: str | None = None,
        collected_time: str | None = None,
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO reports (person_id, filename, stored_path, sha256, kind, lab, report_date, collected_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (person_id, filename, stored_path, sha256, kind, lab, date, collected_time),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_result(self, report_id: int, standard_value: dict[str, Any]) -> int:
        raw = standard_value.get("raw", {})
        cur = self.conn.execute(
            """INSERT INTO results (report_id, test_id, value, unit, raw_test, raw_value, raw_unit, page, guessed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report_id,
                standard_value["test_id"],
                standard_value["value"],
                standard_value["unit"],
                raw.get("test"),
                str(raw.get("value", "")),
                raw.get("unit"),
                raw.get("page"),
                int(standard_value.get("guessed", False)),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_medicine(
        self,
        report_id: int,
        person_id: int,
        name: str,
        drug_class: str | None = None,
        start_date: str | None = None,
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO medicines (report_id, person_id, name, drug_class, start_date)
               VALUES (?, ?, ?, ?, ?)""",
            (report_id, person_id, name, drug_class, start_date),
        )
        self.conn.commit()
        return cur.lastrowid

    def results(self, person_id: int) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT results.*, reports.filename, reports.report_date
               FROM results
               JOIN reports ON reports.id = results.report_id
               WHERE reports.person_id = ?
               ORDER BY reports.report_date ASC, results.id ASC""",
            (person_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def medicines(self, person_id: int) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT medicines.*, reports.filename, reports.report_date
               FROM medicines
               JOIN reports ON reports.id = medicines.report_id
               WHERE medicines.person_id = ?
               ORDER BY medicines.start_date ASC, medicines.id ASC""",
            (person_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def reports(self, person_id: int) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM reports WHERE person_id = ? ORDER BY report_date ASC, id ASC",
            (person_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def delete_report(self, report_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def add_question(self, person_id: int, question: str) -> int:
        q = question.strip()
        if not q:
            raise ValueError("question is empty")
        cur = self.conn.execute(
            "INSERT INTO doctor_questions (person_id, question) VALUES (?, ?)",
            (person_id, q),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_questions(self, person_id: int) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT id, person_id, question, created_at FROM doctor_questions WHERE person_id = ? ORDER BY id ASC",
            (person_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def delete_question(self, question_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM doctor_questions WHERE id = ?", (question_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def save_summary(self, person_id: int, summary: dict[str, Any]) -> int:
        cur = self.conn.execute(
            "INSERT INTO saved_summaries (person_id, generated, summary_json) VALUES (?, ?, ?)",
            (person_id, summary.get("generated", ""), json.dumps(summary)),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_summaries(self, person_id: int) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT id, person_id, generated, created_at FROM saved_summaries WHERE person_id = ? ORDER BY id DESC",
            (person_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_summary(self, summary_id: int) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT summary_json FROM saved_summaries WHERE id = ?",
            (summary_id,),
        )
        row = cur.fetchone()
        return json.loads(row["summary_json"]) if row else None
