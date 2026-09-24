"""Family Health Vault backend package. SHARED FILE.

Import paths from here so every module agrees on where things live.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # repo root
DATA = ROOT / "data"                            # tests.yaml, rules.yaml, medicines.yaml
PROMPTS = ROOT / "prompts"                      # LLM prompt files
SAMPLES = ROOT / "samples"                      # fake PDFs + ground_truth.json (generated)
VAULT_DIR = ROOT / "vault_data"                 # SQLite db + uploaded PDFs (git-ignored)
