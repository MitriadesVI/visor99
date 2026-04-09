from __future__ import annotations


def format_int(value: int | float) -> str:
    return f"{int(value):,}".replace(",", ".")


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"
