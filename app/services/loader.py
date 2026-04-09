from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import APP_SETTINGS
from app.models.dataset import CSVFormat, DatasetBundle, DatasetProfile, DatasetSpec
from app.services.normalizer import apply_column_mapping, build_column_mapping
from app.utils.text import normalize_identifier


SUPPORTED_DELIMITERS = (",", ";", "\t", "|")
SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")


def detect_csv_format(path: Path) -> CSVFormat:
    sample_bytes = b""
    with path.open("rb") as handle:
        sample_bytes = handle.read(65536)

    for encoding in SUPPORTED_ENCODINGS:
        try:
            sample_text = sample_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        sample_text = sample_bytes.decode("utf-8", errors="replace")
        encoding = "utf-8"

    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters="".join(SUPPORTED_DELIMITERS))
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"

    return CSVFormat(delimiter=delimiter, encoding=encoding)


def inspect_column_mapping(spec: DatasetSpec):
    if spec.path.suffix.lower() == ".parquet":
        csv_format = CSVFormat(delimiter="parquet", encoding="binary")
        header_frame = pd.read_parquet(spec.path).head(0)
    else:
        csv_format = detect_csv_format(spec.path)
        header_frame = pd.read_csv(
            spec.path,
            sep=csv_format.delimiter,
            encoding=csv_format.encoding,
            nrows=0,
        )
    mapping = build_column_mapping(
        raw_columns=header_frame.columns,
        column_aliases=APP_SETTINGS.column_aliases,
        required_columns=APP_SETTINGS.required_columns,
    )
    return csv_format, mapping


def load_dataset_bundle(spec: DatasetSpec) -> DatasetBundle:
    csv_format, mapping = inspect_column_mapping(spec)

    if mapping.conflicts:
        raise ValueError("Conflictos de columnas detectados: " + "; ".join(mapping.conflicts))

    if mapping.missing_required:
        raise ValueError(
            "Faltan columnas requeridas: " + ", ".join(mapping.missing_required)
        )

    if spec.path.suffix.lower() == ".parquet":
        raw_frame = pd.read_parquet(spec.path)
    else:
        dtype_map = {
            raw_column: ("Int64" if canonical_name == "votes" else "string")
            for raw_column, canonical_name in mapping.raw_to_canonical.items()
        }

        raw_frame = pd.read_csv(
            spec.path,
            sep=csv_format.delimiter,
            encoding=csv_format.encoding,
            dtype=dtype_map,
            low_memory=False,
        )
    normalized = apply_column_mapping(raw_frame, mapping, APP_SETTINGS.numeric_columns)
    enriched = enrich_dataset(normalized, spec)
    profile = build_dataset_profile(enriched)

    return DatasetBundle(
        spec=spec,
        csv_format=csv_format,
        mapping=mapping,
        profile=profile,
        data=enriched,
    )


def enrich_dataset(frame: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    enriched = frame.copy()
    row_count = len(enriched.index)

    enriched["dataset_id"] = pd.Series([spec.dataset_id] * row_count, dtype="string")
    enriched["dataset_name"] = pd.Series([spec.display_name] * row_count, dtype="string")
    enriched["election_id"] = pd.Series([spec.dataset_id] * row_count, dtype="string")

    candidate_code = _string_column(enriched, "candidate_code", default="0")
    candidate_name = _string_column(enriched, "candidate_name")
    party_name = _string_column(enriched, "party_name")

    row_kind = np.where(candidate_code.fillna("0").eq("0"), "list", "candidate")
    enriched["row_kind"] = pd.Series(row_kind, dtype="string")
    enriched["ballot_label"] = (
        candidate_name.where(enriched["row_kind"].eq("candidate"), party_name)
        .fillna(candidate_name)
        .fillna(party_name)
        .fillna("SIN_ETIQUETA")
        .astype("string")
    )

    enriched["table_id"] = _build_compound_key(
        enriched,
        ["department_code", "municipality_code", "zone_code", "polling_place_code", "table_code"],
    )
    enriched["polling_place_id"] = _build_compound_key(
        enriched,
        ["department_code", "municipality_code", "zone_code", "polling_place_code"],
    )
    enriched["municipality_id"] = _build_compound_key(
        enriched,
        ["department_code", "municipality_code"],
    )

    return enriched


def build_dataset_profile(frame: pd.DataFrame) -> DatasetProfile:
    contests = sorted(_non_null_values(frame.get("contest_name")))
    departments = sorted(_non_null_values(frame.get("department_name")))

    return DatasetProfile(
        row_count=len(frame.index),
        available_contests=tuple(contests),
        available_departments=tuple(departments),
        column_names=tuple(frame.columns),
    )


def _build_compound_key(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    parts: list[pd.Series] = []
    for column_name in columns:
        parts.append(_string_column(frame, column_name, default="NA"))
    return parts[0].str.cat(parts[1:], sep="|")


def _string_column(frame: pd.DataFrame, column_name: str, default: str | None = None) -> pd.Series:
    if column_name not in frame.columns:
        return pd.Series([default] * len(frame.index), dtype="string", index=frame.index)

    series = frame[column_name].astype("string")
    if default is not None:
        return series.fillna(default)
    return series


def _non_null_values(series: pd.Series | None) -> list[str]:
    if series is None:
        return []
    values = series.dropna().astype("string")
    unique_values = pd.Index(values[values.ne("")].unique())
    return unique_values.astype("string").tolist()


def build_download_name(prefix: str, suffix: str) -> str:
    return f"{normalize_identifier(prefix)}_{normalize_identifier(suffix)}.csv"
