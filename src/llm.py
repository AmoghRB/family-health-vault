"""The ONLY place that talks to the local LLM (Ollama). Used by extract.py and summary.py.

OWNER: Extraction role — name: ________ (fill in when you pick this)
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


def available(refresh: bool = False) -> bool:
    raise NotImplementedError  # TODO(EXTRACT)


def chat(system: str, user: str, as_json: bool = False, timeout: int = 180) -> str:
    raise NotImplementedError  # TODO(EXTRACT)


def chat_json(system: str, user: str) -> dict | None:
    raise NotImplementedError  # TODO(EXTRACT)
