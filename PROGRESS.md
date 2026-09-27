# Progress log

Dated, newest last. Everyone appends a line when something real lands.

- **2026-09-24** (Amogh): repo created. Skeleton with one stub per file, each header written as an AI prompt; contracts in `src/contracts.py` + `docs/interfaces.md`; VS Code workspace settings.
- **2026-09-24** (Amogh): moved `src/api.py` + `tests/test_api.py` from the Extraction role to the Frontend role (renamed *Frontend, API & Demo*) to balance the load; added a role-picking guide to the README.
- **2026-09-27** (Reasoning & Submission): implemented `src/reason.py` (`drug_class`, `trend`, `timeline`), `src/summary.py` (`guard`, `template`, `build`), extended `data/medicines.yaml` and `data/rules.yaml`. Verified Ramesh fake data with 6/6 tests passing in `tests/test_reason.py`.
