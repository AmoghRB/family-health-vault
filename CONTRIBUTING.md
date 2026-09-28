# How we work (read this once, fully)

## 1. First-time setup

```bash
git clone https://github.com/AmoghRB/family-health-vault.git
cd family-health-vault
code .                                  # open in VS Code
```

VS Code will offer to install the recommended extensions (Python, Ruff, etc.). Say yes.
Then follow **Setup** in the README.

Set your git name so commits show up as *you*:

```bash
git config user.name  "Your Name"
git config user.email "the-email-on-your-github-account"
```

## 2. The daily loop

```bash
git checkout main && git pull           # start from the latest main
git checkout -b abhishek/standard       # one branch per task: <yourname>/<thing>
# ... work, only in YOUR files ...
git add <your files>
git commit -m "standard: unit conversion for mmol/L"
git push -u origin abhishek/standard
```

Then on GitHub: **Compare & pull request** → base `main`. Someone else glances at
it, runs `pytest -q`, and merges. Delete the branch after merging.

- Commit **small and often** (several times a day). `wip:` commits are fine.
- Merge into `main` **at least once a day**. Don't sit on a branch for three days.
- Never force-push to `main`.

## 3. Using AI on your files (important)

Every stub file starts with a header that is written as a prompt. To build a file:

1. Open the file in VS Code.
2. Give your AI (Claude Code, Copilot, Cursor, ChatGPT…) **the whole header plus
   [`AGENTS.md`](AGENTS.md) and [`src/contracts.py`](src/contracts.py)**.
3. Say: *"Implement this file exactly as the header says. Only edit this file."*
4. Run the test named under **DONE WHEN**, and check that it passes.
5. **Read the diff before you commit.** If the AI touched a file you don't own,
   undo that part (`git checkout -- <file>`) and tell the owner what you needed.

The one rule that prevents merge pain: **you only edit files you own** (see the
table in the README). If you need something from someone else's module, code
against the shape in `src/contracts.py` using fake data, and message the owner.

## 4. Changing a shared shape

`src/contracts.py` and `docs/interfaces.md` are the agreement between all four of
us. To change them, post the change in the group, get a 👍 from the people it
affects, then change **both files in the same commit**.

## 5. Merge conflicts

If you only touched your own files, you won't get any. If you do get one:
`git pull origin main` on your branch, open the file in VS Code, pick
*Accept Current / Incoming / Both* in the conflict view, commit, push.


## Who owns which files

Each file has one owner; change someone else's file only through a PR they review.

| Role | Name | Files |
|---|---|---|
| **Data & Standards** (Person 1) | Pankaj Kumar B S (@PunkK9) | `tools/make_fake_reports.py`, `data/tests.yaml`, `src/standard.py`, `src/store.py`, `tests/test_standard.py`, `tests/test_store.py` |
| **Frontend, API & Demo** (Person 4) | Abhishek Chugh (@abhichugh2006-design) | `web/index.html`, `web/app.js`, `web/style.css`, `web/sample.json`, `web/vendor/`, `src/api.py`, `tests/test_api.py`, `demo/` |
| **Extraction** (Person 2) | Amogh R B (@AmoghRB) | `src/extract.py`, `src/llm.py`, `prompts/extract.txt`, `src/ingest.py`, `tools/accuracy.py`, `tools/make_test_pdfs.py`, `tests/fixtures/`, `tests/test_extract.py`, `tests/test_ingest.py` |
| **Reasoning & Submission** (Person 3) | Aditya Jibrael (@Aditya-JIB3012) | `src/reason.py`, `src/summary.py`, `data/rules.yaml`, `data/medicines.yaml`, `prompts/summary.txt`, `tests/test_reason.py`, `README.md` |
| **Shared** (change only after the group agrees) | everyone | `src/contracts.py`, `docs/interfaces.md`, `requirements.txt`, `AGENTS.md` |

## Ground rules (these cost marks if ignored)

- **Offline.** Nothing calls the internet at runtime. Test with Wi-Fi off.
- **No diagnoses, no doses.** Every flag ends with a question for the doctor.
- **Numbers come from Python, sentences from the LLM.** If the model computes a value, it's a bug.
- **Synthetic reports only.** Never commit a real person's report.
- **Everyone commits under their own name, several times a day.** Judges read the history.
