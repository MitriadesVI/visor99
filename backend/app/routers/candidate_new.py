from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services.json_reader import read_json, sanitize

router = APIRouter(prefix="/api/candidate", tags=["candidate"])


@router.get("/summary")
def candidate_summary(
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str | None = Query(default=None),
) -> dict:
    if department and department != "Todos" and municipality and municipality != "Todos":
        return read_json(f"candidate/{sanitize(department)}/{sanitize(municipality)}.json")
    if department and department != "Todos":
        return read_json(f"candidate/{sanitize(department)}/_summary.json")
    return read_json("candidate/_national.json")


@router.get("/drilldown")
def candidate_drilldown(
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str | None = Query(default=None),
    level: str = Query(default="zone", pattern="^(zone|polling_place|table)$"),
    zone_code: str | None = Query(default=None),
    polling_place_code: str | None = Query(default=None),
) -> dict:
    dept = sanitize(department) if department and department != "Todos" else ""
    muni = sanitize(municipality) if municipality and municipality != "Todos" else ""

    if not dept or not muni:
        # Fallback: shouldn't happen in practice, frontend always sends dept+muni for drilldown
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="department y municipality son requeridos para drilldown")

    base = f"drilldown/{dept}/{muni}"

    if level == "zone":
        return read_json(f"{base}/zones.json")

    if level == "polling_place":
        if not zone_code:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="zone_code es requerido para este nivel")
        zone_key = sanitize(f"ZONE_{zone_code}")
        return read_json(f"{base}/{zone_key}/places.json")

    # level == "table"
    if not zone_code or not polling_place_code:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="zone_code y polling_place_code son requeridos para el nivel table")
    zone_key = sanitize(f"ZONE_{zone_code}")
    place_key = sanitize(f"PLACE_{polling_place_code}")
    return read_json(f"{base}/{zone_key}/{place_key}.json")
