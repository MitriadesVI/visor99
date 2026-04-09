from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend.app.models.schemas import FilterOptionsResponse
from backend.app.routers.common import resolve_dataset
from backend.app.services.query_engine import query_filter_options


router = APIRouter(prefix="/api", tags=["filters"])


@router.get("/filters", response_model=FilterOptionsResponse)
def get_filters(
    request: Request,
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
) -> FilterOptionsResponse:
    _spec, source_sql = resolve_dataset(request, dataset)
    options = query_filter_options(
        source_sql,
        contest=contest,
        department=department,
        municipality=municipality,
        party=party,
    )
    return FilterOptionsResponse(**options)
