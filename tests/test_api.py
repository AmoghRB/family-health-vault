"""End-to-end API tests.  OWNER: Frontend, API & Demo role — name: ________ (fill in when you pick this).  Run: pytest -q tests/test_api.py
Needs everyone's modules, so expect these to pass last (target: 27 Sep).
"""

# OWNER: Abhishek Chugh (contract alignment: Pankaj Kumar B S)
import pytest
from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)

PERSON = {"id", "name", "reports"}
TIMELINE = {"person", "person_id", "series", "flags", "caveats"}
SERIES = {"test", "test_id", "unit", "normal", "points"}
FLAG = {"level", "title", "detail", "ask_doctor", "sources"}
SUMMARY = {"person", "generated", "medicines", "top_trends", "questions", "caveats", "intro"}
UPLOAD = {"filename", "ok", "report_id", "person_id", "kind", "values_saved", "message"}


@pytest.fixture(autouse=True)
def sample_mode(monkeypatch):
    monkeypatch.setenv("FHV_SAMPLE", "1")


def first_person_id():
    return client.get("/api/people").json()[0]["id"]


def test_status():
    assert {"ok", "llm", "model"} <= client.get("/api/status").json().keys()


def test_people_is_a_list_with_int_ids():
    people = client.get("/api/people").json()
    assert isinstance(people, list) and people
    for p in people:
        assert PERSON <= p.keys()
        assert isinstance(p["id"], int)


def test_timeline_matches_contract():
    tl = client.get(f"/api/timeline/{first_person_id()}").json()
    assert TIMELINE <= tl.keys()
    for s in tl["series"]:
        assert SERIES <= s.keys()
        assert all("#p" in pt["source"] for pt in s["points"])
    for f in tl["flags"]:
        assert FLAG <= f.keys()
        assert f["level"] in ("red", "amber", "green")
        assert f["ask_doctor"].endswith("?")


def test_summary_matches_contract():
    assert SUMMARY <= client.get(f"/api/summary/{first_person_id()}").json().keys()


def test_unknown_person_is_404():
    assert client.get("/api/timeline/999").status_code == 404
    assert client.get("/api/summary/999").status_code == 404


def test_upload_returns_one_result_per_file():
    pdf = ("a.pdf", b"%PDF-1.4", "application/pdf")
    results = client.post("/api/upload", files=[("files", pdf), ("files", pdf)]).json()
    assert len(results) == 2
    assert all(UPLOAD <= r.keys() for r in results)


def test_frontend_is_served():
    assert "Family Health Vault" in client.get("/").text


def test_add_person_real_store(monkeypatch, tmp_path):
    import src.api as api
    from src.store import Store

    monkeypatch.setenv("FHV_SAMPLE", "0")
    monkeypatch.setattr(api, "_store", Store(tmp_path))
    r = client.post("/api/people", json={"name": "  priya   Kumar "})
    assert r.status_code == 201 and r.json() == {"id": 1, "name": "priya Kumar", "reports": 0}
    assert client.post("/api/people", json={"name": "PRIYA KUMAR"}).json()["id"] == 1  # same person
    assert client.post("/api/people", json={"name": "<script>"}).status_code == 422
    assert client.get("/api/timeline/1").status_code == 200  # a person with no reports still loads


def test_remove_person_deletes_vault_copy(monkeypatch, tmp_path):
    import src.api as api
    from src.store import Store

    monkeypatch.setenv("FHV_SAMPLE", "0")
    st = Store(tmp_path)
    monkeypatch.setattr(api, "_store", st)
    pid = st.find_or_create_person("Priya Kumar")
    copy = tmp_path / "files" / "abc.pdf"
    copy.parent.mkdir()
    copy.write_bytes(b"%PDF")
    st.add_report(pid, "p.pdf", str(copy), "h", "lab", None, "2025-01-01", None)
    assert client.delete(f"/api/people/{pid}").json() == {"ok": True, "removed_reports": 1}
    assert not copy.exists()
    assert client.delete(f"/api/people/{pid}").status_code == 404
