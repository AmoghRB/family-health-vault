"""Tests for src/extract.py (rules path, no LLM needed).  OWNER: Extraction (Person 2): Amogh R B.
Run: pytest -q tests/test_extract.py
"""

import pytest

from src.extract import parse_date as ex_parse_date, read_rules

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


@pytest.mark.parametrize("s, want", [
    ("Sample Date: 2024-03-11 Collected: 08:15", "2024-03-11"),  # ISO (fake reports)
    ("Date: 11/03/2024", "2024-03-11"),                           # day-first
    ("Reported 20 Sep 2024", "2024-09-20"),
    ("14-08-26", "2026-08-14"),
])
def test_parse_date_formats(s, want):
    assert ex_parse_date(s) == want



def test_rules_bullet_lines_with_ref_range():
    r = read_rules(["THYROPLUS LABORATORIES INDIA\nPatient Name: Ramesh Kumar\n"
                    "Report Date: 2024-07-15 | Collection Time: 08:30\n"
                    "(cid:127) FBS : 6.1 mmol/L (Ref: 3.9-5.6)\n"
                    "\u2022 Triglycerides : 165 mg/dL (Ref: < 150)"])
    assert [(v["test"], v["value"], v["unit"], v["range"]) for v in r["values"]] == [
        ("FBS", "6.1", "mmol/L", "3.9-5.6"), ("Triglycerides", "165", "mg/dL", "< 150")]
    assert r["collected_time"] == "08:30"


def test_rules_numbered_prescription():
    r = read_rules(["Dr. Meenakshi Sundaram, MD\nPatient: Lakshmi Kumar | Date: 2024-05-01\nRx\n"
                    "1. Thyronorm 25 mcg \u2014 1 tab daily morning\n"
                    "2. Uprise D3 60,000 IU \u2014 1 capsule once weekly for 8 weeks"])
    assert r["kind"] == "prescription"
    assert [m["name"] for m in r["medicines"]] == ["Thyronorm", "Uprise D3"]
    assert r["date"] == "2024-05-01" and r["person"] == "Lakshmi Kumar"


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


def test_llm_unit_inside_value_and_range_as_unit(monkeypatch):
    # real qwen2.5 output on the Sri Sai layout, before clean-up
    _fake_llm(monkeypatch, [{**GOOD, "person": "Mr. Ramesh Kumar (58Y/M)",
                             "lab": "SRI SAI LAB · Main Road", "values": [
        {"test": "HbA1c", "value": "7.2 %", "unit": None, "range": None, "page": 1},
        {"test": "Urea", "value": "41", "unit": "(15-40)", "range": "(15-40)", "page": 1}]}])
    r = ex.read_llm(["x"])
    assert r["person"] == "Ramesh Kumar" and r["lab"] == "Sri Sai Lab"
    assert r["values"][0] == {"test": "HbA1c", "value": "7.2", "unit": "%", "range": None, "page": 1}
    assert r["values"][1] == {"test": "Urea", "value": "41", "unit": None, "range": "15-40", "page": 1}


def test_llm_bullet_glyph_stripped_from_test_name(monkeypatch):
    # real qwen2.5 output on the ThyroPlus layout: the PDF bullet comes through as "(cid:127)"
    _fake_llm(monkeypatch, [{**GOOD, "values": [
        {"test": "(cid:127) TSH", "value": "5.2", "unit": "mIU/L", "range": "0.4-4.0", "page": 1}]}])
    assert ex.read_llm(["x"])["values"][0]["test"] == "TSH"


# ── llm.py: only ever talks to Ollama on this machine ────────────────────────
from src import llm  # noqa: E402


def test_llm_refuses_remote_ollama_url(monkeypatch):
    monkeypatch.setattr(llm, "OLLAMA_URL", "http://example.com:11434")
    monkeypatch.setattr(llm.urllib.request, "urlopen",
                        lambda *a, **k: pytest.fail("request left the machine"))
    assert llm.available(refresh=True) is False
    with pytest.raises(RuntimeError, match="local"):
        llm.chat("s", "u")
    assert llm.chat_json("s", "u") is None
    monkeypatch.setattr(llm, "_available", None)


def test_llm_accepts_loopback_urls(monkeypatch):
    for url in ("http://127.0.0.1:11434", "http://localhost:11434/", "http://[::1]:11434"):
        monkeypatch.setattr(llm, "OLLAMA_URL", url)
        assert llm._base().startswith("http://")
