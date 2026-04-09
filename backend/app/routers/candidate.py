from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend.app.analytics.candidate import (
    build_polling_place_drilldown,
    build_table_drilldown,
    build_candidate_table_performance,
    build_zone_drilldown,
    rank_tables,
    rank_zones,
    summarize_candidate_scope,
    tables_lost_by_close_margin,
    tables_won,
)
from backend.app.config import APP_SETTINGS
from backend.app.models.schemas import (
    CandidateSummaryResponse,
    PollingPlaceDrilldownResponse,
    TableDrilldownResponse,
    ZoneDrilldownResponse,
)
from backend.app.routers.common import (
    get_scope_frame,
    records_from_frame,
    resolve_candidate_party,
    resolve_dataset,
)


router = APIRouter(prefix="/api/candidate", tags=["candidate"])


def _matches_code(series, code: str) -> bool:
    return bool(series.astype("string").fillna("").eq(str(code)).any())


def _first_value(frame, column: str) -> str | None:
    values = frame[column].dropna()
    if values.empty:
        return None
    return str(values.iloc[0])


@router.get("/summary", response_model=CandidateSummaryResponse)
def candidate_summary(
    request: Request,
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str = Query(default=APP_SETTINGS.default_candidate_name),
) -> CandidateSummaryResponse:
    spec, source_sql = resolve_dataset(request, dataset)
    scope_frame = get_scope_frame(source_sql, contest, department, municipality, party)

    candidate_party = resolve_candidate_party(scope_frame, candidate)
    if candidate_party is None:
        raise HTTPException(status_code=404, detail=f"Candidato no encontrado: {candidate}")

    performance = build_candidate_table_performance(
        scope_frame,
        candidate_name=candidate,
        thresholds=APP_SETTINGS.classification,
    )
    summary = summarize_candidate_scope(performance)
    narrow_losses = tables_lost_by_close_margin(
        performance,
        margin_threshold=APP_SETTINGS.narrow_loss_margin_threshold,
    )
    summary["narrow_loss_tables"] = int(narrow_losses["table_id"].nunique())
    summary["narrow_loss_margin_threshold"] = APP_SETTINGS.narrow_loss_margin_threshold

    detail_columns = [
        "table_key",
        "municipality_name",
        "zone_code",
        "polling_place_name",
        "table_code",
        "votes",
        "total_table_votes",
        "pct",
        "margin",
        "rival_name",
        "rival_votes",
        "winner_label",
        "winner_votes",
    ]

    top_zones = rank_zones(performance).head(8).rename(
        columns={
            "candidate_votes": "votes",
            "candidate_share": "participation",
            "polling_places": "places",
        }
    )[
        [
            "department_name",
            "municipality_name",
            "zone_code",
            "zone_label",
            "votes",
            "total_votes",
            "participation",
            "tables",
            "places",
            "winning_tables",
        ]
    ]
    top_zones["participation"] = top_zones["participation"] * 100

    top_tables = rank_tables(performance).head(50).rename(
        columns={
            "table_id": "table_key",
            "candidate_votes": "votes",
            "candidate_share": "pct",
            "margin_against_best_competitor": "margin",
            "best_competitor_label": "rival_name",
            "best_competitor_votes": "rival_votes",
        }
    )[detail_columns]
    top_tables["pct"] = top_tables["pct"] * 100

    won = tables_won(performance).head(15).rename(
        columns={
            "table_id": "table_key",
            "candidate_votes": "votes",
            "candidate_share": "pct",
            "margin_against_best_competitor": "margin",
            "best_competitor_label": "rival_name",
            "best_competitor_votes": "rival_votes",
        }
    )[detail_columns]
    won["pct"] = won["pct"] * 100

    lost = narrow_losses.head(15).rename(
        columns={
            "table_id": "table_key",
            "candidate_votes": "votes",
            "candidate_share": "pct",
            "margin_against_best_competitor": "margin",
            "best_competitor_label": "rival_name",
            "best_competitor_votes": "rival_votes",
        }
    )[detail_columns]
    lost["pct"] = lost["pct"] * 100

    return CandidateSummaryResponse(
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
        stats=summary,
        top_zones=records_from_frame(top_zones),
        top_tables=records_from_frame(top_tables),
        tables_won=records_from_frame(won),
        tables_lost_narrow=records_from_frame(lost),
    )


@router.get(
    "/drilldown",
    response_model=ZoneDrilldownResponse | PollingPlaceDrilldownResponse | TableDrilldownResponse,
)
def candidate_drilldown(
    request: Request,
    dataset: str | None = Query(default=None),
    contest: str | None = Query(default=None),
    department: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    party: str | None = Query(default=None),
    candidate: str = Query(default=APP_SETTINGS.default_candidate_name),
    level: str = Query(default="zone", pattern="^(zone|polling_place|table)$"),
    zone_code: str | None = Query(default=None),
    polling_place_code: str | None = Query(default=None),
) -> ZoneDrilldownResponse | PollingPlaceDrilldownResponse | TableDrilldownResponse:
    spec, source_sql = resolve_dataset(request, dataset)
    scope_frame = get_scope_frame(source_sql, contest, department, municipality, party)

    candidate_party = resolve_candidate_party(scope_frame, candidate)
    if candidate_party is None:
        raise HTTPException(status_code=404, detail=f"Candidato no encontrado: {candidate}")

    municipality_name = (
        municipality
        if municipality and municipality != "Todos"
        else _first_value(scope_frame, "municipality_name")
    )

    if level == "zone":
        items = build_zone_drilldown(scope_frame, candidate, APP_SETTINGS.classification)
        return ZoneDrilldownResponse(
            level="zone",
            context={"municipality": municipality_name},
            items=records_from_frame(items),
        )

    if not zone_code:
        raise HTTPException(status_code=400, detail="zone_code es requerido para este nivel")
    if scope_frame.empty or not _matches_code(scope_frame["zone_code"], zone_code):
        raise HTTPException(status_code=404, detail=f"Zona no encontrada en el alcance actual: {zone_code}")

    if level == "polling_place":
        items = build_polling_place_drilldown(
            scope_frame,
            candidate,
            APP_SETTINGS.classification,
            zone_code=zone_code,
        )
        return PollingPlaceDrilldownResponse(
            level="polling_place",
            context={
                "municipality": municipality_name,
                "zone_code": zone_code,
            },
            items=records_from_frame(items),
        )

    if not polling_place_code:
        raise HTTPException(status_code=400, detail="polling_place_code es requerido para el nivel table")

    place_frame = scope_frame[
        scope_frame["zone_code"].astype("string").fillna("").eq(str(zone_code))
        & scope_frame["polling_place_code"].astype("string").fillna("").eq(str(polling_place_code))
    ].copy()
    if place_frame.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Puesto no encontrado en el alcance actual: {polling_place_code}",
        )

    items = build_table_drilldown(
        scope_frame,
        candidate,
        APP_SETTINGS.classification,
        zone_code=zone_code,
        polling_place_code=polling_place_code,
    )
    return TableDrilldownResponse(
        level="table",
        context={
            "municipality": municipality_name,
            "zone_code": zone_code,
            "polling_place_code": polling_place_code,
            "polling_place_name": _first_value(place_frame, "polling_place_name"),
        },
        items=records_from_frame(items),
    )
