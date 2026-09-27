"""OWNER: Pankaj Kumar B S"""

import pytest

from src.store import (
    get_connection,
    init_db,
    get_or_create_person,
    report_exists,
    save_report,
    save_result,
    save_medicine,
    get_timeline_rows,
    get_person_reports,
    hash_file,
)


@pytest.fixture
def conn():
    connection = get_connection(path=":memory:")
    init_db(connection)
    yield connection
    connection.close()


def test_get_or_create_person_creates_and_reuses(conn):
    id1 = get_or_create_person(conn, "Ramesh Kumar")
    id2 = get_or_create_person(conn, "Ramesh Kumar")
    assert id1 == id2  # same name → same person, not duplicated

    id3 = get_or_create_person(conn, "Lakshmi Iyer")
    assert id3 != id1


def test_report_dedup_by_sha256(conn):
    person_id = get_or_create_person(conn, "Ramesh Kumar")
    sha = hash_file(b"fake pdf bytes")

    assert report_exists(conn, sha) is False
    save_report(conn, person_id, "report1.pdf", sha, "lab", "Sunrise", "2026-01-01", "08:00")
    assert report_exists(conn, sha) is True


def test_save_result_and_get_timeline(conn):
    person_id = get_or_create_person(conn, "Ramesh Kumar")
    sha = hash_file(b"fake pdf bytes 2")
    report_id = save_report(conn, person_id, "report2.pdf", sha, "lab", "Sunrise", "2026-01-01", "08:00")

    standard_value = {
        "test_id": "glucose_fasting",
        "name": "Fasting glucose",
        "value": 108.0,
        "unit": "mg/dL",
        "normal": [70, 100],
        "status": "high",
        "raw": {"test": "FBS", "value": "108", "unit": "mg/dL", "range": None, "page": 1},
        "guessed": False,
    }
    save_result(conn, report_id, standard_value)

    rows = get_timeline_rows(conn, person_id, "glucose_fasting")
    assert len(rows) == 1
    assert rows[0]["value"] == 108.0
    assert rows[0]["guessed"] == 0


def test_timeline_ordered_by_date(conn):
    person_id = get_or_create_person(conn, "Ramesh Kumar")

    for i, (date, val) in enumerate([("2026-03-01", 100), ("2026-01-01", 90), ("2026-02-01", 95)]):
        sha = hash_file(f"report {i}".encode())
        report_id = save_report(conn, person_id, f"r{i}.pdf", sha, "lab", "Lab", date, "08:00")
        save_result(conn, report_id, {
            "test_id": "glucose_fasting", "name": "Fasting glucose", "value": val,
            "unit": "mg/dL", "normal": [70, 100], "status": "normal",
            "raw": {"test": "FBS", "value": str(val), "unit": "mg/dL", "range": None, "page": 1},
            "guessed": False,
        })

    rows = get_timeline_rows(conn, person_id, "glucose_fasting")
    dates = [row["report_date"] for row in rows]
    assert dates == ["2026-01-01", "2026-02-01", "2026-03-01"]  # oldest first


def test_save_medicine(conn):
    person_id = get_or_create_person(conn, "Ramesh Kumar")
    sha = hash_file(b"prescription bytes")
    report_id = save_report(conn, person_id, "presc.pdf", sha, "prescription", None, "2026-01-01", None)
    save_medicine(conn, report_id, person_id, "Metformin")

    reports = get_person_reports(conn, person_id)
    assert len(reports) == 1
