"""End-to-end API tests.  OWNER: Frontend, API & Demo role — name: ________ (fill in when you pick this).  Run: pytest -q tests/test_api.py
Needs everyone's modules, so expect these to pass last (target: 27 Sep).
"""

import pytest
from fastapi.testclient import TestClient

from src import SAMPLES
from src.api import app

client = TestClient(app)


def test_status():
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_index_served():
    assert client.get("/").status_code == 200


@pytest.mark.skipif(not (SAMPLES / "ground_truth.json").exists(),
                    reason="run tools/make_fake_reports.py first")
def test_upload_sample():
    pdf = sorted(SAMPLES.glob("ramesh_*.pdf"))[0]
    with open(pdf, "rb") as f:
        r = client.post("/api/upload", files=[("files", (pdf.name, f, "application/pdf"))])
    assert r.status_code == 200
    res = r.json()[0]
    assert res["ok"] or "Already in the vault" in res["message"]
    people = client.get("/api/people").json()
    assert any("Ramesh" in p["name"] for p in people)
