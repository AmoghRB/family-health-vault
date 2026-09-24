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
