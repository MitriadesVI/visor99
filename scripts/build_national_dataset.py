from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import APP_SETTINGS
from app.models.dataset import DatasetSpec
from app.services.loader import inspect_column_mapping
from app.utils.text import normalize_identifier


CANONICAL_COLUMNS = tuple(APP_SETTINGS.column_aliases.keys())
OUTPUT_COLUMNS = (*CANONICAL_COLUMNS, "source_dataset")
STRING_COLUMNS = tuple(column for column in OUTPUT_COLUMNS if column != "votes")


def normalize_chunk(
    chunk: pd.DataFrame,
    spec: DatasetSpec,
    raw_to_canonical: dict[str, str],
) -> pd.DataFrame:
    renamed_columns: dict[str, str] = {}
    for raw_column in chunk.columns:
        canonical_name = raw_to_canonical.get(raw_column)
        if canonical_name:
            renamed_columns[raw_column] = canonical_name
        else:
            renamed_columns[raw_column] = f"extra__{normalize_identifier(raw_column)}"

    normalized = chunk.rename(columns=renamed_columns).copy()
    for column in normalized.columns:
        if column in APP_SETTINGS.numeric_columns:
            normalized[column] = (
                pd.to_numeric(normalized[column], errors="coerce").fillna(0).astype("Int64")
            )
        else:
            normalized[column] = normalized[column].astype("string").str.strip()
            normalized[column] = normalized[column].replace({"": pd.NA})

    normalized = normalized.reindex(columns=OUTPUT_COLUMNS)
    normalized["source_dataset"] = pd.Series(
        [spec.display_name] * len(normalized.index),
        dtype="string",
    )

    for column in STRING_COLUMNS:
        normalized[column] = normalized[column].astype("string")
    normalized["votes"] = pd.to_numeric(normalized["votes"], errors="coerce").astype("Int64")
    return normalized


def build_arrow_schema() -> pa.Schema:
    ordered_fields = []
    for column in OUTPUT_COLUMNS:
        if column == "votes":
            ordered_fields.append(pa.field("votes", pa.int64()))
        else:
            ordered_fields.append(pa.field(column, pa.string()))
    return pa.schema(ordered_fields)


def iter_source_specs(input_dir: Path, outputs: set[Path]) -> list[DatasetSpec]:
    specs: list[DatasetSpec] = []
    for path in sorted(input_dir.glob("*.csv")):
        if path.resolve() in outputs:
            continue
        specs.append(
            DatasetSpec(
                dataset_id=normalize_identifier(path.stem),
                display_name=path.relative_to(APP_SETTINGS.data_dir).as_posix(),
                path=path,
            )
        )
    return specs


def build_national_dataset(
    input_dir: Path,
    output_csv: Path,
    output_parquet: Path,
    chunk_size: int,
) -> tuple[int, list[dict[str, str | int]]]:
    input_dir = input_dir.resolve()
    output_csv = output_csv.resolve()
    output_parquet = output_parquet.resolve()
    outputs = {output_csv, output_parquet}

    source_specs = iter_source_specs(input_dir, outputs)
    if not source_specs:
        raise FileNotFoundError(f"No se encontraron CSV fuente en {input_dir}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_parquet.parent.mkdir(parents=True, exist_ok=True)

    if output_csv.exists():
        output_csv.unlink()
    if output_parquet.exists():
        output_parquet.unlink()

    total_rows = 0
    summaries: list[dict[str, str | int]] = []
    parquet_writer: pq.ParquetWriter | None = None
    schema = build_arrow_schema()
    csv_header_written = False

    try:
        for spec in source_specs:
            csv_format, mapping = inspect_column_mapping(spec)
            if mapping.conflicts:
                raise ValueError(
                    f"Conflictos detectados en {spec.path.name}: {'; '.join(mapping.conflicts)}"
                )
            if mapping.missing_required:
                raise ValueError(
                    f"Faltan columnas requeridas en {spec.path.name}: {', '.join(mapping.missing_required)}"
                )

            dtype_map = {
                raw_column: ("Int64" if canonical_name == "votes" else "string")
                for raw_column, canonical_name in mapping.raw_to_canonical.items()
            }

            file_rows = 0
            for chunk in pd.read_csv(
                spec.path,
                sep=csv_format.delimiter,
                encoding=csv_format.encoding,
                dtype=dtype_map,
                chunksize=chunk_size,
                low_memory=False,
            ):
                normalized = normalize_chunk(chunk, spec, mapping.raw_to_canonical)
                file_rows += len(normalized.index)
                total_rows += len(normalized.index)

                normalized.to_csv(
                    output_csv,
                    mode="a",
                    index=False,
                    header=not csv_header_written,
                    encoding="utf-8",
                )
                csv_header_written = True

                table = pa.Table.from_pandas(normalized, schema=schema, preserve_index=False)
                if parquet_writer is None:
                    parquet_writer = pq.ParquetWriter(output_parquet, schema=schema)
                parquet_writer.write_table(table)

            summaries.append(
                {
                    "file": spec.path.name,
                    "dataset": spec.display_name,
                    "rows": file_rows,
                }
            )
    finally:
        if parquet_writer is not None:
            parquet_writer.close()

    return total_rows, summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolida los CSV departamentales en un dataset nacional CSV y Parquet."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=APP_SETTINGS.data_dir / "elecciones 2026",
        help="Directorio con los CSV fuente por departamento.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=APP_SETTINGS.data_dir / "elecciones 2026" / "nacional.csv",
        help="Ruta del CSV nacional derivado.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=APP_SETTINGS.data_dir / "elecciones 2026" / "nacional.parquet",
        help="Ruta del Parquet nacional derivado.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=250_000,
        help="Filas por bloque para la consolidacion.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total_rows, summaries = build_national_dataset(
        input_dir=args.input_dir,
        output_csv=args.output_csv,
        output_parquet=args.output_parquet,
        chunk_size=args.chunk_size,
    )

    print(f"CSV nacional: {args.output_csv}")
    print(f"Parquet nacional: {args.output_parquet}")
    print(f"Filas consolidadas: {total_rows:,}".replace(",", "."))
    print(f"Archivos fuente: {len(summaries)}")
    for summary in summaries[:5]:
        print(
            f" - {summary['file']} | {summary['rows']:,} filas".replace(",", ".")
        )
    if len(summaries) > 5:
        print(f" ... y {len(summaries) - 5} archivos mas")


if __name__ == "__main__":
    main()
