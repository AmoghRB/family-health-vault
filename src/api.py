"""HTTP API + serves the web/ frontend. Run with ./run.sh (localhost only).

OWNER: Frontend, API & Demo role — Amogh R B (covering for Abhishek Chugh)
LANGUAGE / LIBS: Python 3.12, FastAPI, Uvicorn, python-multipart.

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md + src/contracts.py + docs/interfaces.md into
your AI, then say: "Implement the TODO routes in src/api.py exactly as described.
Only edit this file."

ROUTES (response shapes are in docs/interfaces.md, sections 3–5)
  GET    /api/status                → {"ok": True, "llm": llm.available(), "model": llm.MODEL}
  GET    /api/people                → store.people()
  POST   /api/upload                → multipart field "files" (one or more PDFs).
                                      Save each to a temp file, call
                                      ingest.ingest(store, tmp, filename), return list
                                      of UploadResult. Reject non-PDFs with ok=False.
  GET    /api/timeline/{person_id}  → reason.timeline(store, person_id); 404 if None
  GET    /api/summary/{person_id}   → summary.build(reason.timeline(...),
                                      [m["name"] for m in store.medicines(id)]); 404 if None
  DELETE /api/reports/{report_id}   → {"deleted": store.delete_report(id)}
  /  and every other path            → static files from web/ (already done, bottom of file)

WHY THIS IS IN THE FRONTEND ROLE
  These routes only return the JSON web/app.js reads, so whoever builds the page
  builds the routes too. Until the other modules are ready, a route may return the
  matching part of web/sample.json so the page works end to end; swap in the real
  call (reason.timeline, ingest.ingest, …) as each owner merges.

RULES
  - One module-level Store() shared by all routes.
  - Bind to 127.0.0.1 only (run.sh does this). No CORS needed: the frontend is
    served from the same origin.
  - Keep routes thin: no business logic here, just call the modules.
  - The static mount MUST stay the last line, or it hides the /api routes.

DONE WHEN
  pytest -q tests/test_api.py passes and ./run.sh shows the UI at http://127.0.0.1:8765
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src import ROOT, ingest, llm, reason, summary
from src.contracts import UploadResult
from src.store import Store

WEB = ROOT / "web"

app = FastAPI(title="Family Health Vault")
store = Store()


def _sample(section: str, key: str | None = None):
    """The matching part of web/sample.json, used until a module is merged."""
    data = json.loads((WEB / "sample.json").read_text())[section]
    return data if key is None else data.get(key)


def _found(value):
    if value is None:
        raise HTTPException(404, "Not found")
    return value


@app.get("/api/status")
def status():
    return {"ok": True, "llm": llm.available(), "model": llm.MODEL}


@app.get("/api/people")
def people():
    try:
        return store.people()
    except NotImplementedError:
        return _sample("people")


@app.post("/api/upload")
def upload(files: list[UploadFile] = File(...)) -> list[UploadResult]:
    results: list[UploadResult] = []
    for f in files:
        name = Path(f.filename or "upload.pdf").name
        if not name.lower().endswith(".pdf"):
            results.append(UploadResult(filename=name, ok=False, report_id=None, person_id=None,
                                        kind=None, values_saved=0, message="Only PDF files can be added."))
            continue
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            shutil.copyfileobj(f.file, tmp)
        try:
            results.append(ingest.ingest(store, tmp.name, name))
        except NotImplementedError:
            results.append(UploadResult(filename=name, ok=False, report_id=None, person_id=None,
                                        kind=None, values_saved=0,
                                        message="The vault database isn't connected yet."))
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    return results


@app.get("/api/timeline/{person_id}")
def timeline(person_id: int):
    try:
        return _found(reason.timeline(store, person_id))
    except NotImplementedError:
        return _found(_sample("timelines", str(person_id)))


@app.get("/api/summary/{person_id}")
def doctor_summary(person_id: int):
    try:
        tl = _found(reason.timeline(store, person_id))
        return summary.build(tl, [m["name"] for m in store.medicines(person_id)])
    except NotImplementedError:
        return _found(_sample("summaries", str(person_id)))


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: int):
    return {"deleted": store.delete_report(report_id)}


# Serves web/index.html at "/" and web/* files. Keep this LAST.
app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
