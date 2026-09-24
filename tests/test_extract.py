"""Tests for src/extract.py (rules path, no LLM needed).  OWNER: Extraction (Person 2): Amogh R B.
Run: pytest -q tests/test_extract.py
"""

from src.extract import read_rules

LAB_PAGE = """SRI SAI CLINICAL LABORATORY
Patient Name : Mr. RAMESH KUMAR        Age/Sex : 58/M
Sample Collected : 14-08-26  08:15 AM
Blood Sugar F        : 131
S. Creatinine        : 1.3   mg/dL    0.6 - 1.3
HbA1c                : 7.2   %
"""

RX_PAGE = """Dr. Anil Rao, MBBS MD
Date: 05/10/2024     Patient: Ramesh Kumar
Rx
Tab. Metformin 500mg  1-0-1
Tab. Atorvastatin 10 mg  0-0-1
"""


def test_rules_reads_lab_header():
    r = read_rules([LAB_PAGE])
    assert r["kind"] == "lab"
    assert r["date"] == "2026-08-14"
    assert r["collected_time"] == "08:15"
    assert "RAMESH KUMAR" in r["person"].upper()


def test_rules_reads_values_as_printed():
    r = read_rules([LAB_PAGE])
    by_test = {v["test"]: v for v in r["values"]}
    assert by_test["Blood Sugar F"]["value"] == "131"
    assert by_test["Blood Sugar F"]["unit"] is None
    assert by_test["S. Creatinine"]["unit"] == "mg/dL"


def test_rules_prescription_has_no_doses():
    r = read_rules([RX_PAGE])
    assert r["kind"] == "prescription"
    names = [m["name"].lower() for m in r["medicines"]]
    assert names == ["metformin", "atorvastatin"]


# ── LLM path, with a fake model (no Ollama needed) ────────────────────────────
from pathlib import Path  # noqa: E402

from src import extract as ex  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
GOOD = {"kind": "lab", "person": "RAMESH KUMAR", "date": "2026-08-14", "collected_time": "11:40",
        "lab": "Sri Sai", "values": [{"test": "HbA1c", "value": 7.2, "unit": "%", "range": None,
                                      "page": "1"}], "medicines": []}


def _fake_llm(monkeypatch, replies):
    calls = []
    monkeypatch.setattr(ex.llm, "available", lambda refresh=False: True)
    monkeypatch.setattr(ex.llm, "chat_json", lambda s, u: calls.append(u) or replies.pop(0))
    return calls


def test_llm_reply_normalised(monkeypatch):
    _fake_llm(monkeypatch, [GOOD])
    r = ex.read_llm(["some text"])
    assert r["person"] == "Ramesh Kumar"
    assert r["values"][0] == {"test": "HbA1c", "value": "7.2", "unit": "%", "range": None, "page": 1}


def test_llm_retries_once_then_gives_up(monkeypatch):
    calls = _fake_llm(monkeypatch, [{"kind": "??"}, None])
    assert ex.read_llm(["x"]) is None
    assert len(calls) == 2 and "previous reply was invalid" in calls[1]


def test_llm_medicine_doses_stripped(monkeypatch):
    _fake_llm(monkeypatch, [{**GOOD, "kind": "prescription", "values": [],
                             "medicines": [{"name": "Metformin 500mg BD"}]}])
    assert ex.read_llm(["x"])["medicines"] == [{"name": "Metformin"}]


def test_auto_falls_back_to_rules_when_llm_skips_values(monkeypatch):
    _fake_llm(monkeypatch, [GOOD])            # model found 1 value, rules find 6
    r = ex.extract(FIX / "ramesh_2026-08-14_srisai.pdf", mode="auto")
    assert len(r["values"]) == 6


def test_auto_uses_rules_when_ollama_off(monkeypatch):
    monkeypatch.setattr(ex.llm, "available", lambda refresh=False: False)
    r = ex.extract(FIX / "ramesh_2024-03-11_sunrise.pdf")
    assert len(r["values"]) == 10 and r["date"] == "2024-03-11"
