from __future__ import annotations

import pandas as pd

from app.config import APP_SETTINGS
from app.services.normalizer import apply_column_mapping, build_column_mapping


def test_build_column_mapping_detects_expected_columns() -> None:
    raw_columns = [
        "DEP",
        "DEPNOMBRE",
        "MUN",
        "MUNNOMBRE",
        "PARNOMBRE",
        "CANNOMBRE",
        "VOTOS",
    ]

    mapping = build_column_mapping(
        raw_columns=raw_columns,
        column_aliases=APP_SETTINGS.column_aliases,
        required_columns=APP_SETTINGS.required_columns,
    )

    assert mapping.raw_to_canonical["DEP"] == "department_code"
    assert mapping.raw_to_canonical["MUNNOMBRE"] == "municipality_name"
    assert mapping.raw_to_canonical["VOTOS"] == "votes"
    assert not mapping.missing_required


def test_apply_column_mapping_normalizes_strings_and_votes() -> None:
    frame = pd.DataFrame(
        {
            "DEP": ["03"],
            "DEPNOMBRE": [" Atlantico "],
            "CANNOMBRE": [" Lidio Arturo Garcia Turbay "],
            "VOTOS": ["15"],
        }
    )
    mapping = build_column_mapping(
        raw_columns=frame.columns,
        column_aliases=APP_SETTINGS.column_aliases,
        required_columns=APP_SETTINGS.required_columns,
    )

    normalized = apply_column_mapping(frame, mapping, APP_SETTINGS.numeric_columns)

    assert normalized.loc[0, "department_name"] == "Atlantico"
    assert normalized.loc[0, "candidate_name"] == "Lidio Arturo Garcia Turbay"
    assert int(normalized.loc[0, "votes"]) == 15

