from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services.json_reader import read_json, sanitize

router = APIRouter(prefix="/api", tags=["filters"])


@router.get("/filters")
def get_filters(
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
) -> dict:
    if department and department != "Todos":
        return read_json(f"filters/{sanitize(department)}.json")
    return read_json("filters/all.json")
