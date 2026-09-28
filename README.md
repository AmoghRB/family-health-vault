# Family Health Vault

**Team Ghost Kernel · ASYNC'26 · Track 1: Sovereign AI**

An offline "second brain" for a family's lab reports and prescriptions. Upload the
PDFs; the vault reads them with a **local** model, converts every value to one
standard unit, tracks each test over the years, and flags what is worth asking the
doctor about, including patterns that only show up **across documents** (metformin
on a prescription + creatinine rising on later lab reports). Nothing leaves the laptop.

> **Status (28 Sep): working prototype, end to end.** Upload → extraction → standard
> units → SQLite → trends and cross-document flags → timeline, flag cards and a
> one-page doctor summary in the browser.

## Why

Families keep years of lab reports from different labs, each with its own layout,
test names and units ("Blood Sugar F" in mmol/L at one lab, "Glucose, Fasting" in
mg/dL at another). Nobody lines them up, so slow trends and interactions between a
prescription and later results go unnoticed. Health records are also the data people
least want to upload to a cloud AI, which is why this runs fully on the user's machine
(the Sovereign AI track).

## What it does

- **Reads PDFs from different labs.** `pdfplumber` gets the text; a local LLM
  (Qwen2.5-7B via Ollama) turns it into structured values, with a rules-based reader
  as fallback when the model is off or misses values.
- **Standardizes.** Test-name aliases and unit conversion from `data/tests.yaml`
  (e.g. glucose mmol/L × 18 → mg/dL). Duplicate uploads are detected by file hash.
- **Remembers.** Every value is stored in a local SQLite file with the report and
  page it came from, so every number on screen links back to its source.
- **Reasons across documents.** Trends per test, plus rules in `data/rules.yaml`
  that combine a medicine with later results (metformin × creatinine fires on the
  demo data; thyroid medicine × TSH and others are written and fire as more tests
  are added). Data-quality caveats too, e.g. a "fasting" sample collected at 11:40.
- **Writes a doctor summary.** Python picks the facts; the LLM only writes the
  sentences, and a guard rejects any sentence with a number that isn't in the facts
  or with diagnosis/dosing words (falls back to a template).
- **Stays private.** The only network call is to Ollama on `127.0.0.1`; `src/llm.py`
  refuses any non-local address. Works with Wi-Fi off (Chart.js is vendored).

**It never diagnoses or suggests doses.** Every flag ends in a question for the doctor.

## Results

| Check | Result |
|---|---|
| Test suite (`pytest -q`) | 50 passed |
| Extraction on 16 synthetic reports, 3 lab layouts + 2 prescriptions | **78/78** values correct (rules reader), **78/78** (local LLM), header fields 18/18 |
| Extraction on separate hand-made fixtures | 22/22 |
| Demo case (Ramesh) | Metformin × creatinine flag fires, plus glucose / HbA1c trends |

Reproduce: `python tools/accuracy.py --set samples --mode rules` (or `--mode llm`).

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

Module boundaries are typed once in [`src/contracts.py`](src/contracts.py)
(explained in [`docs/interfaces.md`](docs/interfaces.md)).

## Tech stack

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
If the terminal says "Address already in use", the app is already running: just open the link.

Check extraction accuracy: `python tools/accuracy.py --set samples --mode rules`
(or `--mode llm`).

Demo data without uploading: `FHV_SAMPLE=1 ./run.sh` serves `web/sample.json`.
Frontend only, no backend: `cd web && python -m http.server 8000` → open
http://127.0.0.1:8000. `app.js` falls back to `sample.json`.

## Limitations

- Digital PDFs only; photos and scans are refused (no OCR yet).
- 10 tests are tracked so far (`data/tests.yaml`); others on a report are skipped.
- Tested on synthetic reports only. Not a medical device and not medical advice.

## Team

| Role | Name | GitHub |
|---|---|---|
| Data & Standards | Pankaj Kumar B S | [@PunkK9](https://github.com/PunkK9) |
| Extraction | Amogh R B | [@AmoghRB](https://github.com/AmoghRB) |
| Reasoning & Submission | Aditya Jibrael | [@Aditya-JIB3012](https://github.com/Aditya-JIB3012) |
| Frontend, API & Demo | Abhishek Chugh | [@abhichugh2006-design](https://github.com/abhichugh2006-design) |

Who built what is in the commit history and merged pull requests; file ownership is
in [CONTRIBUTING.md](CONTRIBUTING.md).

## Work scope and prior work disclosure (rules 3 and 4)

- **Built for ASYNC'26, 24–28 Sep 2026**, as the prototype for the 28 Sep
  submission. The first commit is an empty scaffold (24 Sep). Work done at the
  finals (30 Sep – 1 Oct) comes after the git tag `prototype-2026-09-28`.
- **Prior work:** Amogh built a solo exploratory prototype of this idea on
  23 Sep 2026 (local, never published) before the team split the work. This
  repository was started from scratch on 24 Sep; no code was copied from it.
- **Data:** all reports in this repo are synthetic, generated by
  `tools/make_fake_reports.py` and `tools/make_test_pdfs.py`. No real patient data.
- **Models and third-party code:** Qwen2.5-7B-Instruct (Apache 2.0) run through
  Ollama (MIT); Chart.js 4.4.2 (MIT, vendored in `web/vendor/`); Python libraries in
  `requirements.txt` (FastAPI, Uvicorn, pdfplumber, ReportLab, PyYAML, pytest, httpx),
  all open-source. No external APIs.
- **AI assistance:** team members used AI coding assistants while building;
  [`AGENTS.md`](AGENTS.md) holds the rules the team gave them.

## License

MIT, see [LICENSE](LICENSE).
