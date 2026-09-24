"""HTTP API + serves the web/ frontend. Run with ./run.sh (localhost only).

OWNER: Extraction & API role — name: ________ (fill in when you pick this)
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

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src import ROOT, llm

WEB = ROOT / "web"

app = FastAPI(title="Family Health Vault")


@app.get("/api/status")
def status():
    # TODO(EXTRACT): use llm.available() once src/llm.py is implemented
    return {"ok": True, "llm": False, "model": llm.MODEL}


# TODO(EXTRACT): /api/people, /api/upload, /api/timeline/{person_id},
#              /api/summary/{person_id}, DELETE /api/reports/{report_id}


# Serves web/index.html at "/" and web/* files. Keep this LAST.
app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
