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
    assert s.people() == [{"id": pid, "name": "Ramesh Kumar", "reports": 1}]


def test_delete_cascades(tmp_path):
    s = Store(tmp_path)
    pid = s.find_or_create_person("Lakshmi Kumar")
    rid = s.add_report(pid, "b.pdf", "b.pdf", "def", "lab", None, "2025-02-02", None)
    s.add_result(rid, value())
    assert s.delete_report(rid) is True
    assert s.results(pid) == []

def test_doctor_questions_crud():
    store = Store(home=":memory:")
    pid = store.find_or_create_person("Ramesh Kumar")

    qid = store.add_question(pid, "Should Dad take a kidney test with Metformin?")
    questions = store.list_questions(pid)
    assert len(questions) == 1
    assert questions[0]["question"] == "Should Dad take a kidney test with Metformin?"

    assert store.delete_question(qid) is True
    assert len(store.list_questions(pid)) == 0


def test_saved_summaries_history():
    store = Store(home=":memory:")
    pid = store.find_or_create_person("Ramesh Kumar")

    summary_data = {
        "person": "Ramesh Kumar",
        "generated": "2026-09-28",
        "top_trends": [{"title": "HbA1c rising"}],
        "questions": ["Is diabetes under control?"]
    }

    sid = store.save_summary(pid, summary_data)
    summaries = store.list_summaries(pid)
    assert len(summaries) == 1

    loaded = store.get_summary(sid)
    assert loaded["person"] == "Ramesh Kumar"
    assert loaded["generated"] == "2026-09-28"


def test_delete_person_removes_everything(tmp_path):
    s = Store(tmp_path)
    pid = s.find_or_create_person("Priya Kumar")
    keep = s.find_or_create_person("Ramesh Kumar")
    rid = s.add_report(pid, "p.pdf", str(tmp_path / "p.pdf"), "hp", "lab", None, "2025-01-01", None)
    s.add_result(rid, value())
    s.add_medicine(rid, pid, "Uprise D3", "vitamin_d", "2025-01-01")
    s.add_question(pid, "Is my vitamin D ok?")
    s.add_report(keep, "r.pdf", None, "hr", "lab", None, "2025-01-01", None)
    assert s.delete_person(pid) == [str(tmp_path / "p.pdf")]
    assert [p["id"] for p in s.people()] == [keep]
    assert s.results(pid) == [] and s.medicines(pid) == [] and s.report_by_hash("hp") is None
    assert s.delete_person(pid) is None
