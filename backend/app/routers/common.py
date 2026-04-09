from __future__ import annotations

from fastapi import HTTPException, Request
import pandas as pd

from backend.app.analytics.candidate import candidate_vote_options
from backend.app.config import APP_SETTINGS
from backend.app.services.dataset_loader import DatasetSpec, DatasetStore
from backend.app.services.query_engine import query_scope


def get_dataset_store(request: Request) -> DatasetStore:
    return request.app.state.dataset_store


def resolve_dataset(
    request: Request,
    dataset: str | None,
) -> tuple[DatasetSpec, str]:
    """Return ``(spec, source_sql)`` or raise 404."""
    try:
        return get_dataset_store(request).resolve(dataset)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_scope_frame(
    source_sql: str,
    contest: str | None = None,
    department: str | None = None,
    municipality: str | None = None,
    party: str | None = None,
) -> pd.DataFrame:
    contest_name = contest or APP_SETTINGS.default_contest_name
    return query_scope(
        source_sql,
        contest=contest_name,
        department=department,
        municipality=municipality,
        party=party,
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
