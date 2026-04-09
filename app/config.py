from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "datos"
DEFAULT_DATASET_FILENAME = "elecciones 2026/nacional.parquet"
DEFAULT_CONTEST_NAME = "SENADO"
DEFAULT_CANDIDATE_NAME = "GONZALO DIMAS BAUTE GONZALEZ"

CANONICAL_COLUMN_ALIASES: Mapping[str, tuple[str, ...]] = {
    "department_code": ("dep", "departamento", "codigo_departamento"),
    "department_name": ("depnombre", "nombre_departamento", "departamento_nombre"),
    "municipality_code": ("mun", "municipio", "codigo_municipio"),
    "municipality_name": ("munnombre", "nombre_municipio", "municipio_nombre"),
    "zone_code": ("zona", "codigo_zona"),
    "polling_place_code": ("puesto", "codigo_puesto"),
    "polling_place_name": ("puesnombre", "nombre_puesto", "puesto_nombre"),
    "table_code": ("mesa", "codigo_mesa"),
    "commune_code": ("comucodigo", "codigo_comuna"),
    "commune_name": ("comunombre", "nombre_comuna"),
    "contest_code": ("corcodigo", "codigo_concurso", "codigo_corporacion"),
    "contest_name": ("cornombre", "concurso", "corporacion", "nombre_concurso"),
    "district_code": ("cir", "circunscripcion", "codigo_circunscripcion"),
    "party_code": ("par", "partido", "lista", "codigo_partido", "codigo_lista"),
    "party_name": ("parnombre", "nombre_partido", "nombre_lista"),
    "candidate_code": ("can", "codigo_candidato"),
    "candidate_id": ("cancedula", "cedula_candidato", "documento_candidato"),
    "candidate_name": ("cannombre", "nombre_candidato", "candidato"),
    "votes": ("votos", "total_votos"),
}

REQUIRED_CANONICAL_COLUMNS = frozenset({"votes"})
NUMERIC_CANONICAL_COLUMNS = frozenset({"votes"})


@dataclass(frozen=True)
class ClassificationThresholds:
    dominant_share: float = 0.20
    competitive_share: float = 0.08


@dataclass(frozen=True)
class AppSettings:
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    default_dataset_filename: str = DEFAULT_DATASET_FILENAME
    default_contest_name: str = DEFAULT_CONTEST_NAME
    column_aliases: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: CANONICAL_COLUMN_ALIASES
    )
    required_columns: frozenset[str] = field(
        default_factory=lambda: REQUIRED_CANONICAL_COLUMNS
    )
    numeric_columns: frozenset[str] = field(
        default_factory=lambda: NUMERIC_CANONICAL_COLUMNS
    )
    classification: ClassificationThresholds = field(
        default_factory=ClassificationThresholds
    )
    default_candidate_name: str = DEFAULT_CANDIDATE_NAME


APP_SETTINGS = AppSettings()
