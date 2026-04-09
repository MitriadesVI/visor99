from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services.json_reader import read_json, sanitize

router = APIRouter(prefix="/api/municipal", tags=["municipal"])


@router.get("/comparison")
def municipal_comparison(
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str | None = Query(default=None),
    sort_by: str = Query(default="votes", pattern="^(votes|efficiency|coverage)$"),
    limit: int = Query(default=30, ge=5, le=100),
) -> dict:
    if department and department != "Todos":
        return read_json(f"municipal/{sanitize(department)}.json")
    return read_json("municipal/_national.json")
