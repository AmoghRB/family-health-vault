# Progress log

Dated, newest last. Everyone appends a line when something real lands.

- **2026-09-24** (Amogh): repo created. Skeleton with one stub per file, each header written as an AI prompt; contracts in `src/contracts.py` + `docs/interfaces.md`; VS Code workspace settings.
- **2026-09-24** (Amogh): moved `src/api.py` + `tests/test_api.py` from the Extraction role to the Frontend role (renamed *Frontend, API & Demo*) to balance the load; added a role-picking guide to the README.
- **2026-09-24**: roles assigned. Person 1 Data & Standards: Pankaj · Person 2 Extraction: Amogh · Person 3 Reasoning & Submission: Aditya · Person 4 Frontend, API & Demo: Abhishek.
- **2026-09-24** (Amogh, Person 2): extraction done on branch `amogh/extract`. `llm.py` (Ollama wrapper, fails soft), `extract.py` (pdfplumber + rules reader + qwen2.5:7b reader with clean-up and one retry; auto mode falls back to rules), `ingest.py` (hash/dedupe → extract → standardize → save), `accuracy.py`, own test PDFs in `tests/fixtures/` (3 lab layouts + Rx). Accuracy on fixtures: rules 22/22, LLM 22/22, auto 22/22 + 20/20 header fields. 14 tests pass.
- **2026-09-27** (Amogh, Person 2): `llm.py` now refuses any `OLLAMA_URL` that isn't loopback (127.0.0.1 / localhost / ::1), so report text can't leave the machine (Codex review on PR #1). 16 extraction/ingest tests pass. Extraction is in PR #1 (not yet merged).
- **2026-09-28** (Amogh, Person 2): ran extraction on Pankaj's 6 fake PDFs (PR #2): 24/24 values correct; fixed dates printed as `2024-03-11` (ISO) being read as missing, + test. 20 extraction/ingest tests pass.
