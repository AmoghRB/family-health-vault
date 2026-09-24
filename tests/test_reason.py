"""Tests for src/reason.py and src/summary.py.  OWNER: Reasoning & Submission role — name: ________ (fill in when you pick this).
Run: pytest -q tests/test_reason.py
"""

from src.reason import drug_class, trend
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
