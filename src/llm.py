"""The ONLY place that talks to the local LLM (Ollama). Used by extract.py and summary.py.

OWNER: Extraction (Person 2): Amogh R B
LANGUAGE / LIBS: Python 3.12, built-in `urllib.request` + `json`. No `requests`,
no `ollama` package, no OpenAI SDK.

────────────────────────────────── AI PROMPT ──────────────────────────────────
Paste this docstring + AGENTS.md into your AI, then say:
"Implement src/llm.py exactly as described. Only edit this file."

GOAL
  Small wrapper around Ollama's HTTP API at http://127.0.0.1:11434 so the
  rest of the code never deals with HTTP.

CONFIG (environment variables, with defaults)
  OLLAMA_URL    default "http://127.0.0.1:11434"
  VAULT_MODEL   default "qwen2.5:7b-instruct"

FUNCTIONS
  available(refresh=False) -> bool
      GET {OLLAMA_URL}/api/tags with a 2-second timeout. True if the server
      answers AND VAULT_MODEL is in the returned model list. Cache the answer
      in a module variable; refresh=True re-checks. Never raise.
  chat(system, user, as_json=False, timeout=180) -> str
      POST {OLLAMA_URL}/api/chat with
        {"model": MODEL, "stream": false,
         "messages": [{"role":"system","content":system},{"role":"user","content":user}],
         "options": {"temperature": 0},
         "format": "json"   ← only when as_json=True}
      Return response["message"]["content"]. Raise RuntimeError on failure.
  chat_json(system, user) -> dict | None
      chat(..., as_json=True), then json.loads. Return None on any error.

RULES
  - Only ever call 127.0.0.1 / localhost. Never an internet URL.
  - temperature 0 always (repeatable output for the accuracy test).

DONE WHEN
  With Ollama running: python -c "from src import llm; print(llm.available(), llm.chat('Reply OK','hi'))"
  prints True and a reply. With Ollama stopped: available() is False, no crash.
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("VAULT_MODEL", "qwen2.5:7b-instruct")


_available: bool | None = None


def _get(path: str, timeout: float) -> dict:
    with urllib.request.urlopen(OLLAMA_URL + path, timeout=timeout) as r:
        return json.load(r)


def _post(path: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        OLLAMA_URL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def available(refresh: bool = False) -> bool:
    """True if Ollama answers and MODEL is pulled. Cached; never raises."""
    global _available
    if _available is None or refresh:
        try:
            names = {m["name"] for m in _get("/api/tags", timeout=2).get("models", [])}
            _available = MODEL in names or f"{MODEL}:latest" in names
        except Exception:
            _available = False
    return _available


def chat(system: str, user: str, as_json: bool = False, timeout: int = 180) -> str:
    """One chat turn at temperature 0. Raises RuntimeError on any failure."""
    body = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": 0},
    }
    if as_json:
        body["format"] = "json"
    try:
        return _post("/api/chat", body, timeout)["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Ollama chat failed: {e}") from e


def chat_json(system: str, user: str) -> dict | None:
    """chat() in JSON mode, parsed. None on any error or if the reply isn't a JSON object."""
    try:
        out = json.loads(chat(system, user, as_json=True))
    except Exception:
        return None
    return out if isinstance(out, dict) else None
