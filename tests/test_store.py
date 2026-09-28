"""Tests for src/store.py.  OWNER: Data & Standards role — name: ________ (fill in when you pick this).  Run: pytest -q tests/test_store.py"""

from src.store import Store


def value(test_id="creatinine", v=1.1):
    return {"test_id": test_id, "name": "Creatinine", "value": v, "unit": "mg/dL",
            "normal": [0.6, 1.3], "status": "normal", "guessed": False,
            "raw": {"test": "S. Creatinine", "value": str(v), "unit": "mg/dL",
                    "range": None, "page": 1}}


def test_roundtrip(tmp_path):
    s = Store(tmp_path)
    pid = s.find_or_create_person("Ramesh Kumar")
    assert s.find_or_create_person("RAMESH KUMAR") == pid
    rid = s.add_report(pid, "a.pdf", str(tmp_path / "a.pdf"), "abc", "lab",
                       "Sunrise", "2025-01-01", "08:00")
    s.add_result(rid, value())
    rows = s.results(pid)
    assert rows[0]["test_id"] == "creatinine"
    assert rows[0]["report_date"] == "2025-01-01"
    assert rows[0]["filename"] == "a.pdf"
    assert s.report_by_hash("abc")["id"] == rid


def test_delete_cascades(tmp_path):
    s = Store(tmp_path)
    pid = s.find_or_create_person("Lakshmi Kumar")
    rid = s.add_report(pid, "b.pdf", "b.pdf", "def", "lab", None, "2025-02-02", None)
    s.add_result(rid, value())
    assert s.delete_report(rid) is True
    assert s.results(pid) == []
