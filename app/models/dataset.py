from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class CSVFormat:
    delimiter: str
    encoding: str


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    display_name: str
    path: Path


@dataclass(frozen=True)
class ColumnMappingResult:
    canonical_to_raw: dict[str, str]
    raw_to_canonical: dict[str, str]
    unresolved_raw: tuple[str, ...]
    missing_required: tuple[str, ...]
    conflicts: tuple[str, ...] = ()


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
    data: "pd.DataFrame"

