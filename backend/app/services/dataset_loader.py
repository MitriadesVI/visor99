from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from backend.app.config import APP_SETTINGS
from backend.app.services.normalizer import (
    ColumnMappingResult,
    apply_column_mapping,
    build_column_mapping,
)
from backend.app.services.text_utils import normalize_identifier


SUPPORTED_DELIMITERS = (",", ";", "\t", "|")
SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")


@dataclass(frozen=True)
class CSVFormat:
    delimiter: str
    encoding: str


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    display_name: str
    path: Path
    file_format: str
    row_count: int


@dataclass(frozen=True)
class DatasetProfile:
    row_count: int
    available_contests: tuple[str, ...]
    available_departments: tuple[str, ...]
    column_names: tuple[str, ...]


@dataclass
class DatasetBundle:
    spec: DatasetSpec
    csv_format: CSVFormat
    mapping: ColumnMappingResult
    profile: DatasetProfile
    data: pd.DataFrame
    loaded_columns: frozenset[str] = field(default_factory=frozenset)


def detect_csv_format(path: Path) -> CSVFormat:
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


def dataset_row_count(path: Path) -> int:
    if path.suffix.lower() == ".parquet":
        return pq.ParquetFile(path).metadata.num_rows

    csv_format = detect_csv_format(path)
    with path.open("r", encoding=csv_format.encoding, errors="replace") as handle:
        line_count = sum(1 for _ in handle)
    return max(line_count - 1, 0)


def discover_datasets(data_dir: Path | None = None) -> list[DatasetSpec]:
    source_dir = data_dir or APP_SETTINGS.data_dir
    specs: list[DatasetSpec] = []

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".parquet"}:
            continue
        if any(part.startswith(".") for part in path.relative_to(source_dir).parts):
            continue

        relative_path = path.relative_to(source_dir)
        relative_stem = relative_path.with_suffix("")
        specs.append(
            DatasetSpec(
                dataset_id=normalize_identifier(str(relative_stem)),
                display_name=relative_path.as_posix(),
                path=path,
                file_format=path.suffix.lower().lstrip("."),
                row_count=dataset_row_count(path),
            )
        )

    specs.sort(
        key=lambda spec: (
            spec.display_name != APP_SETTINGS.default_dataset_path,
            spec.display_name.lower(),
        )
    )
    return specs


def inspect_column_mapping(spec: DatasetSpec) -> tuple[CSVFormat, ColumnMappingResult]:
    if spec.path.suffix.lower() == ".parquet":
        csv_format = CSVFormat(delimiter="parquet", encoding="binary")
        header_columns = pq.ParquetFile(spec.path).schema.names
    else:
        csv_format = detect_csv_format(spec.path)
        header_columns = pd.read_csv(
            spec.path,
            sep=csv_format.delimiter,
            encoding=csv_format.encoding,
            nrows=0,
        ).columns

    mapping = build_column_mapping(
        raw_columns=header_columns,
        column_aliases=APP_SETTINGS.column_aliases,
        required_columns=APP_SETTINGS.required_columns,
    )
    return csv_format, mapping


def load_dataset_bundle(
    spec: DatasetSpec,
    required_columns: frozenset[str] | None = None,
) -> DatasetBundle:
    csv_format, mapping = inspect_column_mapping(spec)

    if mapping.conflicts:
        raise ValueError("Conflictos de columnas detectados: " + "; ".join(mapping.conflicts))

    if mapping.missing_required:
        raise ValueError(
            "Faltan columnas requeridas: " + ", ".join(mapping.missing_required)
        )

    selected_columns = (
        frozenset(mapping.canonical_to_raw)
        if required_columns is None
        else frozenset(required_columns | APP_SETTINGS.required_columns)
    )
    raw_columns = [
        mapping.canonical_to_raw[column_name]
        for column_name in selected_columns
        if column_name in mapping.canonical_to_raw
    ]

    if spec.path.suffix.lower() == ".parquet":
        raw_frame = pd.read_parquet(spec.path, columns=raw_columns or None)
    else:
        dtype_map = {
            raw_column: (
                "Int64" if mapping.raw_to_canonical[raw_column] == "votes" else "string"
            )
            for raw_column in raw_columns
            if raw_column in mapping.raw_to_canonical
        }
        raw_frame = pd.read_csv(
            spec.path,
            sep=csv_format.delimiter,
            encoding=csv_format.encoding,
            dtype=dtype_map,
            usecols=raw_columns or None,
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
        loaded_columns=selected_columns,
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
        [
            "department_code",
            "municipality_code",
            "zone_code",
            "polling_place_code",
            "table_code",
        ],
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


class DatasetStore:
    def __init__(self) -> None:
        self._specs = discover_datasets()
        self._by_id = {spec.dataset_id: spec for spec in self._specs}
        self._by_path = {spec.display_name: spec for spec in self._specs}
        self._cache: dict[str, DatasetBundle] = {}
        self._lock = Lock()

    def list_specs(self) -> list[DatasetSpec]:
        return list(self._specs)

    def verify_dataset_exists(self, dataset_ref: str | None = None) -> DatasetSpec:
        dataset_key = dataset_ref or APP_SETTINGS.default_dataset_path
        spec = self._by_path.get(dataset_key) or self._by_id.get(dataset_key)
        if spec is None:
            raise KeyError(f"Dataset no encontrado: {dataset_key}")
        return spec

    def get_bundle(
        self,
        dataset_ref: str | None = None,
        required_columns: frozenset[str] | None = None,
    ) -> DatasetBundle:
        spec = self.verify_dataset_exists(dataset_ref)

        with self._lock:
            bundle = self._cache.get(spec.display_name)
            needs_reload = bundle is None
            if bundle is not None and required_columns is None:
                needs_reload = bundle.loaded_columns != frozenset(bundle.mapping.canonical_to_raw)
            if bundle is not None and required_columns is not None:
                needs_reload = not required_columns.issubset(bundle.loaded_columns)

            if needs_reload:
                expanded_columns = required_columns
                if bundle is not None and required_columns is not None:
                    expanded_columns = frozenset(bundle.loaded_columns | required_columns)
                bundle = load_dataset_bundle(spec, required_columns=expanded_columns)
                self._cache[spec.display_name] = bundle

        return bundle


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
