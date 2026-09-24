# Family Health Vault

**Team Ghost Kernel · ASYNC'26 · Track 1 (Wellness & Lifestyle)**

An offline "second brain" for a family's lab reports and prescriptions. Upload
PDFs; the vault reads them, converts every value to one standard unit, tracks
each test over time, and flags what is worth asking the doctor about, including
patterns that only show up across documents (e.g. metformin on a prescription +
rising creatinine on lab reports). Nothing leaves the laptop.

> ⚠️ **Status: skeleton.** Every file is a stub with instructions in its header.
> The owner builds it (with AI help) by following that header. See
> [CONTRIBUTING.md](CONTRIBUTING.md) before you write any code.

---

## Tech stack (fixed, don't add to it without telling the group)

| Layer | Use | Notes |
|---|---|---|
| Language | **Python 3.12** | Backend, tools, tests |
| API | **FastAPI** + **Uvicorn** | Serves the API *and* the `web/` folder |
| PDF reading | **pdfplumber** | Text + tables from digital PDFs |
| Local LLM | **Ollama**, model `qwen2.5:7b-instruct` (`qwen2.5:3b-instruct` on smaller laptops) | Called over `http://127.0.0.1:11434` with Python's `urllib`, no SDK |
| Database | **SQLite** via Python's built-in `sqlite3` | One file in `vault_data/`, no ORM |
| Config data | **YAML** via **PyYAML** | `data/*.yaml` |
| Fake reports | **ReportLab** | Generates synthetic lab PDFs |
| Frontend | **Plain HTML + CSS + vanilla JavaScript** | No React, no npm, no build step |
| Charts | **Chart.js 4** (file saved in `web/vendor/`, not loaded from a CDN) | The demo runs with Wi-Fi off |
| Tests | **pytest** (+ `httpx` for API tests) | `pytest -q` must pass before merging |
| Formatting | **ruff** (VS Code extension, format on save) | 4-space indents, double quotes |

## Architecture

```
            PDF upload (web/)
                  │
                  ▼
  src/api.py  POST /api/upload ──► src/extract.py ──► src/llm.py ──► Ollama (local)
                  │                     │ ExtractedReport (raw text values)
                  │                     ▼
                  │               src/standard.py  ◄── data/tests.yaml
                  │                     │ StandardValue (canonical unit + range)
                  │                     ▼
                  │               src/store.py  ──► vault_data/vault.db (SQLite)
                  │
  GET /api/timeline/{id} ──► src/reason.py ◄── data/rules.yaml, data/medicines.yaml
                  │                     │ Timeline (series + flags)
  GET /api/summary/{id}  ──► src/summary.py ──► src/llm.py (sentences only)
                  │
                  ▼
            web/app.js  (Chart.js timeline, flag cards, doctor summary)
```

The JSON shapes passed between modules are defined **once** in
[`src/contracts.py`](src/contracts.py) and explained in
[`docs/interfaces.md`](docs/interfaces.md). Build against them with fake data
and nobody waits on anybody.

## Who owns what

Four roles. **Not assigned yet:** each person picks one and writes their name
in the `Name` column (and in the `OWNER:` line at the top of each of their files).

| Role | Name | Files |
|---|---|---|
| **Data & Standards** | _______ | `tools/make_fake_reports.py`, `data/tests.yaml`, `src/standard.py`, `src/store.py`, `tests/test_standard.py`, `tests/test_store.py` |
| **Frontend & Demo** | _______ | `web/index.html`, `web/app.js`, `web/style.css`, `web/sample.json`, `web/vendor/`, `demo/` |
| **Extraction & API** | _______ | `src/extract.py`, `src/llm.py`, `prompts/extract.txt`, `src/api.py`, `src/ingest.py`, `tools/accuracy.py`, `tests/test_extract.py`, `tests/test_api.py` |
| **Reasoning & Submission** | _______ | `src/reason.py`, `src/summary.py`, `data/rules.yaml`, `data/medicines.yaml`, `prompts/summary.txt`, `tests/test_reason.py`, `README.md` |
| **Shared** (change only after the group agrees) | everyone | `src/contracts.py`, `docs/interfaces.md`, `requirements.txt`, `AGENTS.md` |

## Setup

```bash
git clone https://github.com/AmoghRB/family-health-vault.git
cd family-health-vault
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Local LLM (once): install Ollama from https://ollama.com, then
ollama pull qwen2.5:7b-instruct     # or qwen2.5:3b-instruct on 8 GB RAM

./run.sh                             # → http://127.0.0.1:8765
pytest -q                            # tests (they fail until the stubs are built)
```

Frontend only, no backend: `cd web && python -m http.server 8000` → open
http://127.0.0.1:8000. `app.js` falls back to `sample.json`.

## Ground rules (these cost marks if ignored)

- **Offline.** Nothing calls the internet at runtime. Test with Wi-Fi off.
- **No diagnoses, no doses.** Every flag ends with a question for the doctor.
- **Numbers come from Python, sentences from the LLM.** If the model computes a value, it's a bug.
- **Synthetic reports only.** Never commit a real person's report.
- **Everyone commits under their own name, several times a day.** Judges read the history.

## Prior work disclosure

Amogh built a solo exploratory prototype of this idea on 23 Sep 2026 (local,
not published) before the team split the work. This repository is a fresh
build by the full team. Any code carried over from that prototype will be
listed here explicitly, per ASYNC'26 rules 3 and 4.

## License

MIT, see [LICENSE](LICENSE).
