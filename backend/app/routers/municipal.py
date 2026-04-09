from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend.app.analytics.municipal import build_municipal_comparison
from backend.app.config import APP_SETTINGS
from backend.app.models.schemas import MunicipalComparisonResponse
from backend.app.routers.common import (
    get_scope_frame,
    records_from_frame,
    resolve_candidate_party,
    resolve_dataset,
)


router = APIRouter(prefix="/api/municipal", tags=["municipal"])


@router.get("/comparison", response_model=MunicipalComparisonResponse)
def municipal_comparison(
    request: Request,
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str = Query(default=APP_SETTINGS.default_candidate_name),
    sort_by: str = Query(default="votes", pattern="^(votes|efficiency|coverage)$"),
    limit: int = Query(default=30, ge=5, le=100),
) -> MunicipalComparisonResponse:
    spec, source_sql = resolve_dataset(request, dataset)
    scope_frame = get_scope_frame(source_sql, contest, department, municipality, party)
    candidate_party = resolve_candidate_party(scope_frame, candidate)
    if candidate_party is None:
        raise HTTPException(status_code=404, detail=f"Candidato no encontrado: {candidate}")

    comparison, summary = build_municipal_comparison(
        scope_frame,
        candidate_name=candidate,
        sort_by=sort_by,
        limit=limit,
    )

    return MunicipalComparisonResponse(
        candidate={
            "name": candidate,
            "party": candidate_party,
            "contest": contest or APP_SETTINGS.default_contest_name,
        },
        scope={
            "dataset": spec.display_name,
            "department": department if department and department != "Todos" else None,
            "municipality": municipality if municipality and municipality != "Todos" else None,
            "party": party if party and party != "Todos" else None,
        },
        summary=summary,
        municipalities=records_from_frame(comparison),
    )
