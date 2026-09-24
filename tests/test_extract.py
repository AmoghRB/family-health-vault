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
