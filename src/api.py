import json
import os
import urllib.request
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MODEL = "qwen2.5:7b-instruct"

app = FastAPI(title="Family Health Vault")
_store = None


def use_sample() -> bool:
    """FHV_SAMPLE=1 (the default until the pipeline is wired) serves web/sample.json."""
    return os.environ.get("FHV_SAMPLE", "1") == "1"


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


# --- Pipeline adapters: fill these three from the headers of ingest.py / reason.py / summary.py ---
def _real_timeline(person_id: int) -> dict | None:
    raise NotImplementedError("call reason.py (see its header)")


def _real_summary(person_id: int) -> dict | None:
    raise NotImplementedError("call summary.py (see its header)")


def _real_ingest(filename: str, content: bytes) -> dict:
    raise NotImplementedError("call ingest.py (see its header); return an UploadResult")


@app.get("/api/status")
def status():
    return {"ok": True, "llm": ollama_up(), "model": MODEL}


@app.get("/api/people")
def people():
    return sample()["people"] if use_sample() else store().people()


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


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    results = []
    for f in files:
        content = await f.read()
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
