from __future__ import annotations

from fastapi import HTTPException, Request
import pandas as pd

from backend.app.analytics.candidate import apply_scope_filters, candidate_vote_options
from backend.app.config import APP_SETTINGS
from backend.app.services.dataset_loader import DatasetBundle, DatasetStore

FILTER_COLUMNS = frozenset(
    {
        "contest_name",
        "department_name",
        "municipality_name",
        "party_name",
        "candidate_code",
        "candidate_name",
        "votes",
    }
)

ANALYTICS_COLUMNS = frozenset(
    {
        "department_code",
        "department_name",
        "municipality_code",
        "municipality_name",
        "zone_code",
        "polling_place_code",
        "polling_place_name",
        "table_code",
        "contest_name",
        "party_name",
        "candidate_code",
        "candidate_name",
        "votes",
    }
)


def get_dataset_store(request: Request) -> DatasetStore:
    return request.app.state.dataset_store


def get_dataset_bundle(
    request: Request,
    dataset: str | None,
    required_columns: frozenset[str] | None = None,
) -> DatasetBundle:
    try:
        return get_dataset_store(request).get_bundle(dataset, required_columns=required_columns)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_scope_frame(
    bundle: DatasetBundle,
    contest: str | None = None,
    department: str | None = None,
    municipality: str | None = None,
    party: str | None = None,
) -> pd.DataFrame:
    contest_name = contest or APP_SETTINGS.default_contest_name
    return apply_scope_filters(
        bundle.data,
        contest_name=contest_name,
        department_name=department,
        municipality_name=municipality,
        party_name=party,
    )


def resolve_candidate_party(frame: pd.DataFrame, candidate_name: str) -> str | None:
    options = candidate_vote_options(frame)
    matches = options[options["candidate_name"].eq(candidate_name)]
    if matches.empty:
        return None
    value = matches.iloc[0]["party_name"]
    return None if pd.isna(value) else str(value)


def records_from_frame(frame: pd.DataFrame) -> list[dict[str, object]]:
    if frame.empty:
        return []
    cleaned = frame.astype(object).where(pd.notna(frame), None)
    return cleaned.to_dict(orient="records")
