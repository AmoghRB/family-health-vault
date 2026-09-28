# Family Health Vault

**Team Ghost Kernel · ASYNC'26 · Track 1 (Sovereign AI)**

An offline "second brain" for a family's lab reports and prescriptions. Upload
PDFs; the vault reads them, converts every value to one standard unit, tracks
each test over time, and flags what is worth asking the doctor about, including
patterns that only show up across documents (e.g. metformin on a prescription +
rising creatinine on lab reports). Nothing leaves the laptop.

> **Status: working end to end (28 Sep).** Upload PDFs → extraction (rules + local
> LLM) → standard units → SQLite → trends and cross-document flags → timeline,
> flag cards and doctor summary in the browser. On the 16 generated sample reports:
> 78/78 values read (rules and LLM), metformin × creatinine flag fires for Ramesh.
> See [CONTRIBUTING.md](CONTRIBUTING.md) before you write any code.

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

Four roles, assigned 24 Sep. **Your first commit:** put your name in the `OWNER:`
line at the top of each of your files (it checks your Git setup works).

| Role | Name | Files |
|---|---|---|
| **Data & Standards** (Person 1) | Pankaj Kumar B S (@PunkK9) | `tools/make_fake_reports.py`, `data/tests.yaml`, `src/standard.py`, `src/store.py`, `tests/test_standard.py`, `tests/test_store.py` |
| **Frontend, API & Demo** (Person 4) | Abhishek Chugh (@abhichugh2006-design) | `web/index.html`, `web/app.js`, `web/style.css`, `web/sample.json`, `web/vendor/`, `src/api.py`, `tests/test_api.py`, `demo/` |
| **Extraction** (Person 2) | Amogh R B (@AmoghRB) | `src/extract.py`, `src/llm.py`, `prompts/extract.txt`, `src/ingest.py`, `tools/accuracy.py`, `tools/make_test_pdfs.py`, `tests/fixtures/`, `tests/test_extract.py`, `tests/test_ingest.py` |
| **Reasoning & Submission** (Person 3) | Aditya Jibrael (@Aditya-JIB3012) | `src/reason.py`, `src/summary.py`, `data/rules.yaml`, `data/medicines.yaml`, `prompts/summary.txt`, `tests/test_reason.py`, `README.md` |
| **Shared** (change only after the group agrees) | everyone | `src/contracts.py`, `docs/interfaces.md`, `requirements.txt`, `AGENTS.md` |

### How to pick a role

| Role | Load | Blocks others? | Best for someone who… |
|---|---|---|---|
| **Extraction** | Heaviest: messy PDFs, regex, local LLM, upload glue | Partly: nothing gets into the app without it | is strongest in Python and can debug when AI-written code breaks |
| **Data & Standards** | Medium, but **most urgent** | **Yes:** everyone needs the fake reports + `tests.yaml` | can start **immediately** and is careful with details (units, ranges, SQL) |
| **Reasoning & Submission** | Medium; builds the metformin flag, the demo's best moment | No: builds on fake rows | thinks logically, writes well, will own the final submission (the lead fits) |
| **Frontend, API & Demo** | Light–medium; fully independent via `web/sample.json`, and `api.py` is thin routes returning exactly what the page reads | No | enjoys UI work, or has the least free time this week |

**Picking order:** Data & Standards first, to whoever can start today (not anyone
tied up until the 25th) → Extraction to the strongest Python person → Reasoning
& Submission to the lead → Frontend, API & Demo to whoever is left.

**So nobody waits:** Frontend builds against `web/sample.json`; Reasoning tests
`trend()` and flags on hand-written rows; Extraction tests on the report text in
`tests/test_extract.py` until the fake PDFs exist. Everything connects on **27 Sep**.

## Setup

```bash
git clone https://github.com/AmoghRB/family-health-vault.git
cd family-health-vault
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Local LLM (once): install Ollama from https://ollama.com, then
ollama pull qwen2.5:7b-instruct     # or qwen2.5:3b-instruct on 8 GB RAM

pytest -q                            # 50 tests
./run.sh --samples                   # makes the 16 fake PDFs in samples/, starts the app
```

**Windows** (no `run.sh`): after `pip install`, run
`python tools/make_fake_reports.py` then
`python -m uvicorn src.api:app --host 127.0.0.1 --port 8765`.

Open http://127.0.0.1:8765 → **Upload** tab → drop all the PDFs from `samples/`
(about 15 s each with Ollama on; instant without it, the rules reader takes over) →
pick **Ramesh Kumar** → **Flags** / **Timeline** / **Doctor Summary**.
Uploads are stored in `vault_data/` (git-ignored); delete that folder to start over.

**Your own reports:** digital PDFs only (the kind a lab emails, where you can select
the text). Photos or scans are refused, since there's no OCR yet. Only the 10 tests
in `data/tests.yaml` are tracked; anything else on the report is skipped.
If the page shows "Address already in use", the app is already running: just open the link.

Check extraction accuracy: `python tools/accuracy.py --set samples --mode rules`
(or `--mode llm`).

Demo data without uploading: `FHV_SAMPLE=1 ./run.sh` serves `web/sample.json`.
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
