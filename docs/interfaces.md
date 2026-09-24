# Interfaces: the agreed JSON shapes

The code version is [`src/contracts.py`](../src/contracts.py). The two must match.
Change both together, and only after the group agrees.

## 1. `extract.py` → `standard.py` (Extraction → Data & Standards)

`extract(path)` returns one `ExtractedReport` per PDF. Values are copied **as printed**, as strings:

```json
{ "kind": "lab", "person": "Ramesh Kumar", "date": "2026-08-14",
  "collected_time": "08:15", "lab": "Sri Sai Diagnostics",
  "values": [ { "test": "Blood Sugar F", "value": "131", "unit": null,
                "range": "70-100", "page": 1 } ],
  "medicines": [] }
```

For a prescription: `"kind": "prescription"`, `"values": []`, `"medicines": [{"name": "Metformin"}]`.

## 2. `standard.py` output (Data & Standards)

`standardize(raw_value)` → `StandardValue`, or `None` if the test is unknown/implausible:

```json
{ "test_id": "glucose_fasting", "name": "Fasting glucose", "value": 118.8,
  "unit": "mg/dL", "normal": [70, 100], "status": "high",
  "raw": { "test": "FBS", "value": "6.6", "unit": "mmol/L", "range": null, "page": 1 },
  "guessed": false }
```

## 3. `GET /api/timeline/{person_id}` (Reasoning & Submission → Frontend, API & Demo)

```json
{ "person": "Ramesh Kumar", "person_id": 1,
  "series": [ { "test": "HbA1c", "test_id": "hba1c", "unit": "%", "normal": [null, 5.7],
                "points": [ { "date": "2024-03-11", "value": 6.1,
                              "source": "ramesh_2024-03-11_sunrise.pdf#p1" } ] } ],
  "flags": [ { "level": "red", "title": "Blood sugar rising steadily",
               "detail": "HbA1c 6.1 → 7.2% over 29 months.",
               "ask_doctor": "Is the current treatment enough?",
               "sources": ["ramesh_2024-03-11_sunrise.pdf", "ramesh_2026-08-14_srisai.pdf"] } ],
  "caveats": ["The 'fasting' sample on 2025-03-15 was collected at 11:40."] }
```

## 4. `GET /api/summary/{person_id}` (Reasoning & Submission → Frontend, API & Demo)

```json
{ "person": "Ramesh Kumar", "generated": "2026-09-28",
  "medicines": ["Metformin", "Atorvastatin"],
  "top_trends": [ /* up to 3 Flag objects */ ],
  "questions": ["Should my kidney function be checked while on metformin?"],
  "caveats": ["..."],
  "intro": "Ramesh has 7 reports from March 2024 to August 2026. ..." }
```

## 5. Other API routes (Extraction → Frontend, API & Demo)

| Route | Returns |
|---|---|
| `GET /api/status` | `{"ok": true, "llm": true/false, "model": "qwen2.5:7b-instruct"}` |
| `GET /api/people` | `[{"id": 1, "name": "Ramesh Kumar", "reports": 7}]` |
| `POST /api/upload` (multipart, field `files`, one or more PDFs) | `[UploadResult, ...]` |
| `GET /api/timeline/{person_id}` | `Timeline` (404 if no such person) |
| `GET /api/summary/{person_id}` | `DoctorSummary` |
| `GET /` and `/web/*` | the frontend files |

`UploadResult`:
```json
{ "filename": "ramesh_2026-08-14_srisai.pdf", "ok": true, "report_id": 7,
  "person_id": 1, "kind": "lab", "values_saved": 14,
  "message": "Read 14 values for Ramesh Kumar (14 Aug 2026)." }
```

## SQLite tables (Data & Standards, in `store.py`)

| Table | Columns |
|---|---|
| `people` | `id, name` |
| `reports` | `id, person_id, filename, sha256 (unique), kind, lab, report_date, collected_time, uploaded_at` |
| `results` | `id, report_id, test_id, value, unit, raw_test, raw_value, raw_unit, page, guessed` |
| `medicines` | `id, report_id, person_id, name, drug_class, start_date` |

(The split page called the lab-values table `values`, but `VALUES` is an SQL keyword, so the table is named `results`.)
