from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend.app.analytics.candidate import candidate_vote_options
from backend.app.models.schemas import FilterOptionsResponse
from backend.app.routers.common import get_dataset_bundle, records_from_frame


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
    bundle = get_dataset_bundle(request, dataset)
    data = bundle.data

    contest_frame = data
    if contest:
        contest_frame = contest_frame[contest_frame["contest_name"].eq(contest)]

    department_frame = contest_frame
    if department and department != "Todos":
        department_frame = department_frame[department_frame["department_name"].eq(department)]

    municipality_frame = department_frame
    if municipality and municipality != "Todos":
        municipality_frame = municipality_frame[
            municipality_frame["municipality_name"].eq(municipality)
        ]

    party_frame = municipality_frame
    if party and party != "Todos":
        party_frame = party_frame[party_frame["party_name"].eq(party)]

    contests = sorted(
        data["contest_name"].dropna().astype("string").unique().tolist()
    )
    departments = sorted(
        contest_frame["department_name"].dropna().astype("string").unique().tolist()
    )
    municipalities = sorted(
        department_frame["municipality_name"].dropna().astype("string").unique().tolist()
    )
    parties = sorted(
        municipality_frame["party_name"].dropna().astype("string").unique().tolist()
    )
    candidates = (
        candidate_vote_options(party_frame)["candidate_name"].dropna().astype("string").tolist()
    )

    return FilterOptionsResponse(
        contests=contests,
        departments=departments,
        municipalities=municipalities,
        parties=parties,
        candidates=candidates,
    )
