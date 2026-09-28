import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MODEL = "qwen2.5:7b-instruct"

app = FastAPI(title="Family Health Vault")
_store = None


def use_sample() -> bool:
    """FHV_SAMPLE=1 serves web/sample.json instead of the vault (frontend work without a database)."""
    return os.environ.get("FHV_SAMPLE", "0") == "1"


def store():
    global _store
    if _store is None:
        from src.store import Store  # imported lazily so sample mode never touches the database

        _store = Store()
    return _store


def sample() -> dict:
    return json.loads((WEB_DIR / "sample.json").read_text(encoding="utf-8"))


def ollama_up() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1).close()
        return True
    except OSError:
        return False


# --- Pipeline adapters: the real modules behind each route (used when FHV_SAMPLE=0) ---
def _real_timeline(person_id: int) -> dict | None:
    from src import reason

    return reason.timeline(store(), person_id)


def _real_summary(person_id: int) -> dict | None:
    from src import reason, summary

    tl = reason.timeline(store(), person_id)
    if tl is None:
        return None
    return summary.build(tl, [m["name"] for m in store().medicines(person_id)])


def _real_ingest(filename: str, content: bytes) -> dict:
    from src import ingest

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
    try:
        return ingest.ingest(store(), tmp.name, filename)
    finally:
        os.unlink(tmp.name)


@app.get("/api/status")
def status():
    return {"ok": True, "llm": ollama_up(), "model": MODEL}


@app.get("/api/people")
def people():
    return sample()["people"] if use_sample() else store().people()


class NewPerson(BaseModel):
    name: str


NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,59}$")


@app.post("/api/people", status_code=201)
def add_person(body: NewPerson):
    """Add a family member before their reports arrive. Reports match them by name later."""
    name = " ".join(body.name.split())
    if not NAME_RE.match(name):
        raise HTTPException(status_code=422, detail="Use letters only, 2 to 60 characters.")
    if use_sample():
        raise HTTPException(status_code=400, detail="Demo mode: start the backend to add people.")
    person_id = store().find_or_create_person(name)
    return next(p for p in store().people() if p["id"] == person_id)


@app.delete("/api/people/{person_id}")
def remove_person(person_id: int):
    """Remove a family member with all their reports, values, medicines and stored PDFs."""
    if use_sample():
        raise HTTPException(status_code=400, detail="Demo mode: start the backend to remove people.")
    paths = store().delete_person(person_id)
    if paths is None:
        raise HTTPException(status_code=404, detail="Unknown person")
    home = Path(store().home).resolve()
    for p in paths:
        f = Path(p).resolve()
        if f.is_relative_to(home):  # only ever delete copies inside the vault folder
            f.unlink(missing_ok=True)
    return {"ok": True, "removed_reports": len(paths)}


@app.get("/api/timeline/{person_id}")
def timeline(person_id: int):
    data = sample()["timelines"].get(str(person_id)) if use_sample() else _real_timeline(person_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Unknown person")
    return data


@app.get("/api/summary/{person_id}")
def summary(person_id: int):
    data = sample()["summaries"].get(str(person_id)) if use_sample() else _real_summary(person_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Unknown person")
    return data


class ChatRequest(BaseModel):
    person_id: int
    question: str
    history: list[dict] = []


@app.post("/api/chat")
def chat(body: ChatRequest):
    """Ask the vault about one person's records, answered by the local model (see src/chat.py)."""
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="Ask a question first.")
    if use_sample():
        return {"answer": "Demo mode: start the backend to ask questions about real reports.",
                "sources": [], "mode": "facts"}
    from src import chat as chat_mod

    result = chat_mod.answer(store(), body.person_id, body.question, body.history)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown person")
    return result


@app.post("/api/upload")
def upload(files: list[UploadFile] = File(...)):
    # Plain def, not async: reading a PDF with the LLM takes ~15 s and must not freeze the other routes.
    results = []
    for f in files:
        content = f.file.read()
        if use_sample():
            results.append(
                {
                    "filename": f.filename,
                    "ok": False,
                    "report_id": None,
                    "person_id": None,
                    "kind": None,
                    "values_saved": 0,
                    "message": "Demo mode: file not processed.",
                }
            )
        else:
            results.append(_real_ingest(f.filename, content))
    return results


# Must be mounted last: catch-all for the frontend files.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
