from __future__ import annotations

import re
import unicodedata


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_identifier(value: str) -> str:
    cleaned = strip_accents(value).lower().strip()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")
