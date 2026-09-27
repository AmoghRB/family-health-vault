"""OWNER: Pankaj Kumar B S

SQLite storage layer. Raw sqlite3, no ORM. One file: vault_data/vault.db.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "vault_data" / "vault.db"


def get_connection(path: Path | str = DB_PATH) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL REFERENCES people(id),
            filename TEXT NOT NULL,
            sha256 TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            lab TEXT,
            report_date TEXT,
            collected_time TEXT,
            uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            test_id TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            raw_test TEXT NOT NULL,
            raw_value TEXT NOT NULL,
            raw_unit TEXT,
            page INTEGER,
            guessed INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            person_id INTEGER NOT NULL REFERENCES people(id),
            name TEXT NOT NULL,
            drug_class TEXT,
            start_date TEXT
        );
    """)
    conn.commit()


def hash_file(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def get_or_create_person(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM people WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO people (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


def report_exists(conn: sqlite3.Connection, sha256: str) -> bool:
    row = conn.execute("SELECT id FROM reports WHERE sha256 = ?", (sha256,)).fetchone()
    return row is not None


def save_report(
    conn: sqlite3.Connection,
    person_id: int,
    filename: str,
    sha256: str,
    kind: str,
    lab: str | None,
    report_date: str | None,
    collected_time: str | None,
) -> int:
    cur = conn.execute(
        """INSERT INTO reports (person_id, filename, sha256, kind, lab, report_date, collected_time)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (person_id, filename, sha256, kind, lab, report_date, collected_time),
    )
    conn.commit()
    return cur.lastrowid


def save_result(conn: sqlite3.Connection, report_id: int, standard_value: dict) -> int:
    raw = standard_value["raw"]
    cur = conn.execute(
        """INSERT INTO results (report_id, test_id, value, unit, raw_test, raw_value, raw_unit, page, guessed)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            report_id,
            standard_value["test_id"],
            standard_value["value"],
            standard_value["unit"],
            raw["test"],
            raw["value"],
            raw.get("unit"),
            raw.get("page"),
            int(standard_value["guessed"]),
        ),
    )
    conn.commit()
    return cur.lastrowid


def save_medicine(
    conn: sqlite3.Connection,
    report_id: int,
    person_id: int,
    name: str,
    drug_class: str | None = None,
    start_date: str | None = None,
) -> int:
    cur = conn.execute(
        """INSERT INTO medicines (report_id, person_id, name, drug_class, start_date)
           VALUES (?, ?, ?, ?, ?)""",
        (report_id, person_id, name, drug_class, start_date),
    )
    conn.commit()
    return cur.lastrowid


def get_timeline_rows(conn: sqlite3.Connection, person_id: int, test_id: str) -> list[sqlite3.Row]:
    """All results for one person + test, oldest first, with source info for traceability."""
    return conn.execute(
        """SELECT results.*, reports.filename, reports.report_date
           FROM results
           JOIN reports ON reports.id = results.report_id
           WHERE reports.person_id = ? AND results.test_id = ?
           ORDER BY reports.report_date ASC""",
        (person_id, test_id),
    ).fetchall()


def get_person_reports(conn: sqlite3.Connection, person_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM reports WHERE person_id = ? ORDER BY report_date ASC", (person_id,)
    ).fetchall()
