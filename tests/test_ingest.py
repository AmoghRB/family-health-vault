"""Tests for src/ingest.py.  OWNER: Extraction (Person 2): Amogh R B.

Person 1's standard.py/store.py and Person 3's reason.py aren't merged yet, so
these use small stand-ins with the same method names as the stubs.
Run: pytest -q tests/test_ingest.py
"""

from pathlib import Path

import pytest

from src import ingest

FIX = Path(__file__).parent / "fixtures"


class FakeStore:
    def __init__(self, home):
        self.home = home
        self.people, self.reports, self.results, self.meds = {}, {}, [], []

    def report_by_hash(self, sha):
        return next((r for r in self.reports.values() if r["sha256"] == sha), None)

    def find_or_create_person(self, name):
        return self.people.setdefault(name.lower(), len(self.people) + 1)

    def add_report(self, person_id, filename, stored_path, sha256, kind, lab, date, time):
        rid = len(self.reports) + 1
        self.reports[rid] = {"id": rid, "person_id": person_id, "filename": filename,
                             "sha256": sha256, "stored_path": stored_path}
        return rid

    def add_result(self, report_id, v):
        self.results.append((report_id, v))

    def add_medicine(self, report_id, person_id, name, drug_class, start):
        self.meds.append((name, drug_class, start))


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest.extract, "read_llm", lambda pages: None)   # rules path only
    monkeypatch.setattr(ingest.standard, "standardize", lambda raw: {"test_id": raw["test"]})
    monkeypatch.setattr(ingest.reason, "drug_class",
                        lambda n: "biguanide" if n.lower() == "metformin" else None)
    return FakeStore(tmp_path)


def test_lab_report_saved(store):
    r = ingest.ingest(store, FIX / "ramesh_2026-08-14_srisai.pdf")
    assert r["ok"], r["message"]
    assert r["kind"] == "lab" and r["values_saved"] == 6
    assert r["message"] == "Read 6 values for Ramesh Kumar (14 Aug 2026)."
    assert Path(store.reports[1]["stored_path"]).exists()


def test_duplicate_upload_refused(store):
    ingest.ingest(store, FIX / "ramesh_2026-08-14_srisai.pdf")
    r = ingest.ingest(store, FIX / "ramesh_2026-08-14_srisai.pdf", "copy.pdf")
    assert not r["ok"]
    assert "Already in the vault" in r["message"]


def test_prescription_medicines(store):
    r = ingest.ingest(store, FIX / "ramesh_2024-10-05_prescription.pdf")
    assert r["ok"] and r["kind"] == "prescription"
    assert ("Metformin", "biguanide", "2024-10-05") in store.meds


def test_prescription_saved_without_drug_class(store, monkeypatch):
    def missing(name):
        raise NotImplementedError
    monkeypatch.setattr(ingest.reason, "drug_class", missing)
    r = ingest.ingest(store, FIX / "ramesh_2024-10-05_prescription.pdf")
    assert r["ok"], r["message"]
    assert ("Metformin", None, "2024-10-05") in store.meds


def test_same_person_across_reports(store):
    a = ingest.ingest(store, FIX / "ramesh_2024-03-11_sunrise.pdf")
    b = ingest.ingest(store, FIX / "ramesh_2024-09-20_thyroplus.pdf")   # printed in CAPS
    assert a["person_id"] == b["person_id"]


def test_never_raises(store, tmp_path):
    bad = tmp_path / "not_a.pdf"
    bad.write_text("hello")
    r = ingest.ingest(store, bad)
    assert not r["ok"]
