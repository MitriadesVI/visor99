from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

from backend.app.config import APP_SETTINGS
from backend.app.services.normalizer import (
    build_column_mapping,
)
from backend.app.services.text_utils import normalize_identifier


SUPPORTED_DELIMITERS = (",", ";", "\t", "|")
SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")

_ENCODING_MAP = {"utf-8": "UTF8", "utf-8-sig": "UTF8", "latin-1": "LATIN1"}


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


def _build_source_sql(spec: DatasetSpec) -> str:
    """Return a DuckDB SQL expression that reads *spec* with canonical column names."""
    path = str(spec.path.resolve()).replace("'", "''")
    if spec.file_format == "parquet":
        return f"SELECT * FROM read_parquet('{path}')"

    # CSV: inspect header and alias raw → canonical
    csv_format = detect_csv_format(spec.path)
    with spec.path.open("r", encoding=csv_format.encoding, errors="replace") as fh:
        reader = csv.reader(fh, delimiter=csv_format.delimiter)
        header = next(reader)

    mapping = build_column_mapping(
        raw_columns=header,
        column_aliases=APP_SETTINGS.column_aliases,
        required_columns=APP_SETTINGS.required_columns,
    )
    all_canonical = list(APP_SETTINGS.column_aliases.keys())
    aliases: list[str] = []
    for canonical in all_canonical:
        raw = mapping.canonical_to_raw.get(canonical)
        if raw:
            escaped = raw.replace('"', '""')
            aliases.append(f'"{escaped}" AS {canonical}')
        else:
            aliases.append(f"NULL AS {canonical}")

    select = ", ".join(aliases)
    delim = csv_format.delimiter.replace("'", "''")
    enc = _ENCODING_MAP.get(csv_format.encoding, "UTF8")
    return f"SELECT {select} FROM read_csv('{path}', delim='{delim}', header=true, encoding='{enc}')"


class DatasetStore:
    """Discovers datasets and provides DuckDB source-SQL expressions.

    No data is loaded into memory — each request queries via DuckDB.
    """

    def __init__(self) -> None:
        self._specs = discover_datasets()
        self._by_id = {spec.dataset_id: spec for spec in self._specs}
        self._by_path = {spec.display_name: spec for spec in self._specs}
        self._source_sql: dict[str, str] = {}
        for spec in self._specs:
            self._source_sql[spec.display_name] = _build_source_sql(spec)

    def list_specs(self) -> list[DatasetSpec]:
        return list(self._specs)

    def resolve(self, dataset_ref: str | None = None) -> tuple[DatasetSpec, str]:
        """Return ``(DatasetSpec, source_sql)`` for *dataset_ref*.

        *source_sql* is a DuckDB-compatible SQL snippet that reads the
        underlying parquet or CSV file with canonical column names.
        """
        key = dataset_ref or APP_SETTINGS.default_dataset_path
        spec = self._by_path.get(key) or self._by_id.get(key)
        if spec is None:
            raise KeyError(f"Dataset no encontrado: {key}")
        return spec, self._source_sql[spec.display_name]
