from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services.json_reader import read_json, sanitize

router = APIRouter(prefix="/api/competitive", tags=["competitive"])


@router.get("/rivals")
def competitive_rivals(
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str | None = Query(default=None),
    top_n: int = Query(default=15, ge=1, le=20),
) -> dict:
    if department and department != "Todos" and municipality and municipality != "Todos":
        return read_json(f"competitive/{sanitize(department)}/{sanitize(municipality)}.json")
    if department and department != "Todos":
        return read_json(f"competitive/{sanitize(department)}/_rivals.json")
    return read_json("competitive/_national.json")
