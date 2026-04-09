from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config import APP_SETTINGS
from app.models.dataset import DatasetSpec
from app.services.loader import inspect_column_mapping
from app.utils.text import normalize_identifier


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
            )
        )

    specs.sort(
        key=lambda spec: (
            spec.display_name != APP_SETTINGS.default_dataset_filename,
            spec.display_name.lower(),
        )
    )
    return specs


def get_dataset_spec(dataset_id: str, data_dir: Path | None = None) -> DatasetSpec:
    for spec in discover_datasets(data_dir=data_dir):
        if spec.dataset_id == dataset_id:
            return spec
    raise KeyError(f"Dataset no encontrado: {dataset_id}")


def build_municipality_directory(data_dir: Path | None = None) -> pd.DataFrame:
    records: list[dict[str, str]] = []

    for spec in discover_datasets(data_dir=data_dir):
        csv_format, mapping = inspect_column_mapping(spec)
        municipality_raw = mapping.canonical_to_raw.get("municipality_name")
        department_raw = mapping.canonical_to_raw.get("department_name")

        if not municipality_raw:
            continue

        usecols = [municipality_raw]
        rename_map = {municipality_raw: "municipality_name"}

        if department_raw:
            usecols.append(department_raw)
            rename_map[department_raw] = "department_name"

        if spec.path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(spec.path, columns=usecols).rename(columns=rename_map)
            frame = frame.astype("string")
        else:
            frame = pd.read_csv(
                spec.path,
                sep=csv_format.delimiter,
                encoding=csv_format.encoding,
                usecols=usecols,
                dtype="string",
                low_memory=False,
            ).rename(columns=rename_map)

        if "department_name" not in frame.columns:
            frame["department_name"] = pd.Series([""] * len(frame.index), dtype="string")

        unique_rows = (
            frame[["department_name", "municipality_name"]]
            .dropna(subset=["municipality_name"])
            .drop_duplicates()
        )

        for _, row in unique_rows.iterrows():
            municipality_name = str(row["municipality_name"]).strip()
            department_name = str(row["department_name"]).strip()
            if not municipality_name:
                continue

            records.append(
                {
                    "dataset_id": spec.dataset_id,
                    "dataset_display_name": spec.display_name,
                    "department_name": department_name,
                    "municipality_name": municipality_name,
                    "search_label": (
                        f"{municipality_name} · {department_name}"
                        if department_name
                        else municipality_name
                    ),
                }
            )

    if not records:
        return pd.DataFrame(
            columns=[
                "dataset_id",
                "dataset_display_name",
                "department_name",
                "municipality_name",
                "search_label",
            ]
        )

    directory = pd.DataFrame.from_records(records).drop_duplicates(
        subset=["dataset_id", "department_name", "municipality_name"]
    )
    return directory.sort_values(
        ["municipality_name", "department_name", "dataset_display_name"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
