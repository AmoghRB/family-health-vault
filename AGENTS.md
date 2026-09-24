# Instructions for AI coding assistants

You are helping one member of a 4-person hackathon team (Team Ghost Kernel,
ASYNC'26) build **Family Health Vault**, an offline app that reads family lab
reports and prescriptions (PDF), standardizes the values, tracks trends and
flags questions to ask a doctor.

## Hard rules

1. **Only edit the file(s) the user asked about.** Each file has one owner
   (table in README.md). Do not "fix" or refactor other files. If the task
   needs a change elsewhere, stop and say what is needed instead of doing it.
2. **Follow the header of the file.** The docstring or comment at the top of
   each stub is the spec: inputs, outputs, steps, and a DONE WHEN check.
   Keep that header in the file after you implement it (trim the TODOs only).
3. **Use the shapes in `src/contracts.py` exactly.** Same key names, same types.
   Do not rename, add or remove keys. These shapes are how the four people's
   code connects.
4. **Stack is fixed:** Python 3.12, FastAPI, pdfplumber, PyYAML, ReportLab,
   built-in `sqlite3`, pytest; frontend is plain HTML/CSS/vanilla JS with
   Chart.js 4 from `web/vendor/`. **Do not add dependencies**, frameworks
   (no React, no SQLAlchemy, no LangChain, no requests/openai SDKs) or a build step.
5. **Offline only.** No internet calls at runtime. The only network call
   allowed is to the local Ollama server at `http://127.0.0.1:11434`, and
   only from `src/llm.py`.
6. **The LLM never does maths.** It only reads text (extraction) or writes
   sentences from numbers Python already computed (summary). Unit
   conversion, comparisons and trends are plain Python.
7. **No medical advice.** Never output a diagnosis, a dose, or "stop/start
   taking X". Every flag ends with a question for the doctor.
8. Keep code simple and readable: small functions, type hints, short
   docstrings, no classes unless the header asks for one.
9. After writing code, run the test named in DONE WHEN (`pytest -q tests/<file>`)
   and fix failures in *your* file only.
