"""Tests for src/chat.py (Ask the vault).  OWNER: Amogh R B.  Run: pytest -q tests/test_chat.py"""

import pytest

from src import chat
from src.store import Store


def value(test_id, name, v, unit, normal):
    return {"test_id": test_id, "name": name, "value": v, "unit": unit, "normal": normal,
            "status": "normal", "guessed": False,
            "raw": {"test": name, "value": str(v), "unit": unit, "range": None, "page": 1}}


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path)
    pid = s.find_or_create_person("Ramesh Kumar")
    for i, (date, cr) in enumerate([("2024-03-11", 0.9), ("2026-08-14", 1.3)]):
        rid = s.add_report(pid, f"r{i}.pdf", None, f"h{i}", "lab", "Sunrise", date, "08:00")
        s.add_result(rid, value("creatinine", "Creatinine", cr, "mg/dL", [0.6, 1.3]))
    rx = s.add_report(pid, "rx.pdf", None, "hrx", "prescription", None, "2024-10-01", None)
    s.add_medicine(rx, pid, "Metformin", "metformin", "2024-10-01")
    return s


def fake_llm(monkeypatch, reply):
    calls = []
    monkeypatch.setattr(chat.llm, "available", lambda refresh=False: True)
    monkeypatch.setattr(chat.llm, "chat", lambda system, user, timeout=120: calls.append(user) or reply)
    return calls


def test_facts_come_from_python(store):
    f = chat.facts(store, 1)
    assert f["person"] == "Ramesh Kumar"
    assert [r["value"] for r in f["tests"][0]["readings"]] == [0.9, 1.3]
    assert f["medicines"][0]["name"] == "Metformin"


def test_llm_answer_used_when_numbers_check_out(store, monkeypatch):
    calls = fake_llm(monkeypatch, "Creatinine went from 0.9 mg/dL on 2024-03-11 to 1.3 mg/dL (r1.pdf).")
    r = chat.answer(store, 1, "How has my creatinine changed?")
    assert r["mode"] == "llm" and "1.3" in r["answer"]
    assert "r1.pdf" in r["sources"]
    assert "Metformin" in calls[0]            # the model is given the facts


def test_invented_number_falls_back_to_facts(store, monkeypatch):
    fake_llm(monkeypatch, "Creatinine rose by 44% to 1.3 mg/dL.")   # 44 was computed by the model
    r = chat.answer(store, 1, "How has my creatinine changed?")
    assert r["mode"] == "facts" and "latest 1.3 mg/dL" in r["answer"]


@pytest.mark.parametrize("q", ["How much metformin should I take?", "Can I stop taking metformin?",
                               "Is 1000 mg ok?", "should i take more"])
def test_dosing_questions_refused_without_the_model(store, monkeypatch, q):
    calls = fake_llm(monkeypatch, "anything")
    r = chat.answer(store, 1, q)
    assert r["mode"] == "refused" and "doctor" in r["answer"] and not calls


def test_works_offline_from_facts(store, monkeypatch):
    monkeypatch.setattr(chat.llm, "available", lambda refresh=False: False)
    assert "latest 1.3 mg/dL" in chat.answer(store, 1, "creatinine?")["answer"]
    assert "Metformin" in chat.answer(store, 1, "what medicines am I on")["answer"]


def test_unknown_person_and_empty_person(store):
    assert chat.answer(store, 99, "hi") is None
    pid = store.find_or_create_person("New Person")
    assert "no reports" in chat.answer(store, pid, "anything?")["answer"]
