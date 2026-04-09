from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd

from app.models.dataset import ColumnMappingResult
from app.utils.text import normalize_identifier


def build_alias_index(column_aliases: Mapping[str, tuple[str, ...]]) -> dict[str, str]:
    alias_index: dict[str, str] = {}

    for canonical_name, aliases in column_aliases.items():
        alias_index[normalize_identifier(canonical_name)] = canonical_name
        for alias in aliases:
            alias_index[normalize_identifier(alias)] = canonical_name

    return alias_index


def build_column_mapping(
    raw_columns: Iterable[str],
    column_aliases: Mapping[str, tuple[str, ...]],
    required_columns: frozenset[str],
) -> ColumnMappingResult:
    alias_index = build_alias_index(column_aliases)
    canonical_to_raw: dict[str, str] = {}
    raw_to_canonical: dict[str, str] = {}
    unresolved_raw: list[str] = []
    conflicts: list[str] = []

    for raw_column in raw_columns:
        normalized_raw = normalize_identifier(raw_column)
        canonical_name = alias_index.get(normalized_raw)

        if canonical_name is None:
            unresolved_raw.append(raw_column)
            continue

        if canonical_name in canonical_to_raw:
            conflicts.append(
                f"Las columnas '{canonical_to_raw[canonical_name]}' y "
                f"'{raw_column}' apuntan a '{canonical_name}'."
            )
            continue

        canonical_to_raw[canonical_name] = raw_column
        raw_to_canonical[raw_column] = canonical_name

    missing_required = sorted(required_columns - set(canonical_to_raw))

    return ColumnMappingResult(
        canonical_to_raw=canonical_to_raw,
        raw_to_canonical=raw_to_canonical,
        unresolved_raw=tuple(unresolved_raw),
        missing_required=tuple(missing_required),
        conflicts=tuple(conflicts),
    )


def apply_column_mapping(
    frame: pd.DataFrame,
    mapping: ColumnMappingResult,
    numeric_columns: frozenset[str],
) -> pd.DataFrame:
    renamed_columns: dict[str, str] = {}

    for raw_column in frame.columns:
        canonical_name = mapping.raw_to_canonical.get(raw_column)
        if canonical_name:
            renamed_columns[raw_column] = canonical_name
            continue

        renamed_columns[raw_column] = f"extra__{normalize_identifier(raw_column)}"

    normalized = frame.rename(columns=renamed_columns).copy()

    for column_name in normalized.columns:
        if column_name in numeric_columns:
            normalized[column_name] = (
                pd.to_numeric(normalized[column_name], errors="coerce")
                .fillna(0)
                .astype("Int64")
            )
            continue

        normalized[column_name] = normalized[column_name].astype("string").str.strip()
        normalized[column_name] = normalized[column_name].replace({"": pd.NA})

    return normalized

