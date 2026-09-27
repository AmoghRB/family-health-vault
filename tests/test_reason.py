"""Tests for src/reason.py and src/summary.py.  OWNER: Reasoning & Submission role — name: ________ (fill in when you pick this).
Run: pytest -q tests/test_reason.py
"""

from src.reason import drug_class, timeline, trend
from src.summary import build, guard


def test_drug_class():
    assert drug_class("Metformin") == "biguanide"
    assert drug_class("Tab Glycomet GP") == "biguanide"
    assert drug_class("Paracetamol") is None


def test_trend_rising():
    pts = [{"date": "2024-01-01", "value": 0.9},
           {"date": "2025-01-01", "value": 1.1},
           {"date": "2026-01-01", "value": 1.3}]
    t = trend(pts)
    assert t["direction"] == "rising"
    assert abs(t["change"] - 0.4) < 1e-9


def test_trend_flat():
    pts = [{"date": "2024-01-01", "value": 100},
           {"date": "2025-01-01", "value": 101},
           {"date": "2026-01-01", "value": 100.5}]
    assert trend(pts)["direction"] == "flat"


def test_guard_blocks_invented_numbers_and_doses():
    facts = {"flags": [{"detail": "HbA1c 6.1 → 7.2%"}]}
    assert guard("HbA1c went from 6.1 to 7.2%.", facts) is not None
    assert guard("HbA1c went from 6.1 to 9.9%.", facts) is None
    assert guard("Consider 500 mg of metformin.", facts) is None


def test_summary_template():
    tl = {"person": "Ramesh Kumar", "person_id": 1, "series": [], "caveats": [],
          "flags": [{"level": "red", "title": "Kidney values changing",
                     "detail": "Creatinine 0.9 → 1.3 mg/dL", "ask_doctor": "Kidney test?",
                     "sources": ["a.pdf"]}]}
    s = build(tl, medicines=["Metformin"], use_llm=False)
    assert s["person"] == "Ramesh Kumar"
    assert s["questions"] == ["Kidney test?"]
    assert s["intro"]


def test_ramesh_timeline(monkeypatch):
    import src.standard

    mock_cat = {
        "creatinine": {"name": "Creatinine", "unit": "mg/dL", "range": [0.6, 1.3], "bad": "high", "ask": "Should my kidney function be checked while on metformin?"},
        "glucose_fasting": {"name": "Fasting glucose", "unit": "mg/dL", "range": [70, 100], "bad": "high", "ask": "Is my blood sugar control on track?"},
        "hba1c": {"name": "HbA1c", "unit": "%", "range": [None, 5.7], "bad": "high", "ask": "Is my HbA1c under control?"},
    }
    monkeypatch.setattr(src.standard, "catalogue", lambda: mock_cat)

    class FakeStore:
        def person(self, person_id):
            return {"id": 1, "name": "Ramesh Kumar"} if person_id == 1 else None

        def reports(self, person_id):
            return [
                {"id": 1, "filename": "ramesh_2024-03-11_sunrise.pdf", "lab": "Sunrise Diagnostics", "report_date": "2024-03-11", "collected_time": "08:30"},
                {"id": 2, "filename": "ramesh_2025-01-10_thyroplus.pdf", "lab": "ThyroPlus Labs", "report_date": "2025-01-10", "collected_time": "11:40"},
                {"id": 3, "filename": "ramesh_2026-08-14_srisai.pdf", "lab": "Sri Sai Clinical Lab", "report_date": "2026-08-14", "collected_time": "09:00"},
                {"id": 4, "filename": "ramesh_2026-08-14_srisai_dup.pdf", "lab": "Sri Sai Clinical Lab", "report_date": "2026-08-14", "collected_time": "09:00"},
            ]

        def medicines(self, person_id):
            return [
                {"name": "Metformin", "drug_class": "biguanide", "start_date": "2024-10-01", "filename": "rx_2024-10-01.pdf"},
            ]

        def results(self, person_id):
            return [
                # Creatinine rising across metformin start date
                {"test_id": "creatinine", "value": 0.9, "unit": "mg/dL", "page": 1, "report_date": "2024-03-11", "filename": "ramesh_2024-03-11_sunrise.pdf", "report_id": 1, "guessed": 0},
                {"test_id": "creatinine", "value": 1.1, "unit": "mg/dL", "page": 1, "report_date": "2025-01-10", "filename": "ramesh_2025-01-10_thyroplus.pdf", "report_id": 2, "guessed": 0},
                {"test_id": "creatinine", "value": 1.3, "unit": "mg/dL", "page": 1, "report_date": "2026-08-14", "filename": "ramesh_2026-08-14_srisai.pdf", "report_id": 3, "guessed": 0},
                # Fasting glucose rising out of range
                {"test_id": "glucose_fasting", "value": 108.0, "unit": "mg/dL", "page": 1, "report_date": "2024-03-11", "filename": "ramesh_2024-03-11_sunrise.pdf", "report_id": 1, "guessed": 0},
                {"test_id": "glucose_fasting", "value": 125.0, "unit": "mg/dL", "page": 1, "report_date": "2025-01-10", "filename": "ramesh_2025-01-10_thyroplus.pdf", "report_id": 2, "guessed": 0},
                {"test_id": "glucose_fasting", "value": 142.0, "unit": "mg/dL", "page": 1, "report_date": "2026-08-14", "filename": "ramesh_2026-08-14_srisai.pdf", "report_id": 3, "guessed": 1},
                # HbA1c rising 6.1 -> 7.2
                {"test_id": "hba1c", "value": 6.1, "unit": "%", "page": 1, "report_date": "2024-03-11", "filename": "ramesh_2024-03-11_sunrise.pdf", "report_id": 1, "guessed": 0},
                {"test_id": "hba1c", "value": 6.6, "unit": "%", "page": 1, "report_date": "2025-01-10", "filename": "ramesh_2025-01-10_thyroplus.pdf", "report_id": 2, "guessed": 0},
                {"test_id": "hba1c", "value": 7.2, "unit": "%", "page": 1, "report_date": "2026-08-14", "filename": "ramesh_2026-08-14_srisai.pdf", "report_id": 3, "guessed": 0},
            ]

    store = FakeStore()
    tl = timeline(store, 1)

    assert tl is not None
    assert tl["person"] == "Ramesh Kumar"
    assert len(tl["series"]) == 3

    # At least 3 correct flags
    assert len(tl["flags"]) >= 3

    # Including the metformin cross-document flag
    metformin_flag = next((f for f in tl["flags"] if "metformin" in f["title"].lower() or "metformin" in f["ask_doctor"].lower()), None)
    assert metformin_flag is not None
    assert metformin_flag["level"] == "red"
    assert "rx_2024-10-01.pdf" in metformin_flag["sources"]

    # Data quality caveats captured
    assert any("fasting" in c.lower() for c in tl["caveats"])
    assert any("duplicate" in c.lower() for c in tl["caveats"])
    assert any("inferred" in c.lower() for c in tl["caveats"])

    # Doctor summary generation works cleanly
    summary = build(tl, medicines=["Metformin"], use_llm=False)
    assert summary["person"] == "Ramesh Kumar"
    assert len(summary["top_trends"]) <= 3
    assert len(summary["questions"]) >= 1
    assert summary["intro"]

