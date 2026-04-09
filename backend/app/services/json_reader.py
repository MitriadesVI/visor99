"""Utility to read precomputed JSON files."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import HTTPException

_SANITIZE_RE = re.compile(r"[^A-Z0-9_]")

# Resolve precomputed/ relative to project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRECOMPUTED_DIR = _PROJECT_ROOT / "precomputed"


def sanitize(name: str) -> str:
    return _SANITIZE_RE.sub("_", name.upper().strip()).strip("_") or "UNKNOWN"


def read_json(relative_path: str) -> dict | list:
    """Read a precomputed JSON file. Raises 404 if not found."""
    full = PRECOMPUTED_DIR / relative_path
    # Prevent path traversal
    try:
        full.resolve().relative_to(PRECOMPUTED_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ruta inválida")
    if not full.is_file():
        raise HTTPException(status_code=404, detail=f"Datos no encontrados: {relative_path}")
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)
