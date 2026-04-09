from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend.app.analytics.competitive import build_competitive_overview
from backend.app.config import APP_SETTINGS
from backend.app.models.schemas import CompetitiveResponse
from backend.app.routers.common import (
    ANALYTICS_COLUMNS,
    get_dataset_bundle,
    get_scope_frame,
    records_from_frame,
    resolve_candidate_party,
)


router = APIRouter(prefix="/api/competitive", tags=["competitive"])


@router.get("/rivals", response_model=CompetitiveResponse)
def competitive_rivals(
    request: Request,
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str = Query(default=APP_SETTINGS.default_candidate_name),
    top_n: int = Query(default=15, ge=1, le=20),
) -> CompetitiveResponse:
    bundle = get_dataset_bundle(request, dataset, required_columns=ANALYTICS_COLUMNS)
    scope_frame = get_scope_frame(bundle, contest, department, municipality, party)
    candidate_party = resolve_candidate_party(scope_frame, candidate)
    if candidate_party is None:
        raise HTTPException(status_code=404, detail=f"Candidato no encontrado: {candidate}")

    rivals_frame, head_to_head, total_candidate_tables = build_competitive_overview(
        scope_frame,
        candidate_name=candidate,
        thresholds=APP_SETTINGS.classification,
        top_n=top_n,
    )

    return CompetitiveResponse(
        candidate={
            "name": candidate,
            "party": candidate_party,
            "contest": contest or APP_SETTINGS.default_contest_name,
        },
        scope={
            "dataset": bundle.spec.display_name,
            "department": department if department and department != "Todos" else None,
            "municipality": municipality if municipality and municipality != "Todos" else None,
            "party": party if party and party != "Todos" else None,
        },
        total_candidate_tables=total_candidate_tables,
        rivals=records_from_frame(rivals_frame),
        head_to_head=records_from_frame(head_to_head),
    )
