from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DatasetItem(BaseModel):
    name: str
    path: str
    format: str
    row_count: int


class FilterOptionsResponse(BaseModel):
    contests: list[str]
    departments: list[str]
    municipalities: list[str]
    parties: list[str]
    candidates: list[str]


class CandidateIdentity(BaseModel):
    name: str
    party: str | None = None
    contest: str | None = None


class CandidateScope(BaseModel):
    dataset: str
    department: str | None = None
    municipality: str | None = None
    party: str | None = None


class CandidateStats(BaseModel):
    total_votes: int
    total_tables: int
    tables_with_votes: int
    tables_without_votes: int
    coverage_pct: float
    avg_participation: float
    municipalities_with_votes: int
    winning_tables: int
    narrow_loss_tables: int
    narrow_loss_margin_threshold: int


class ZoneSummary(BaseModel):
    department_name: str | None = None
    municipality_name: str | None = None
    zone_code: str | None = None
    zone_label: str
    votes: int
    total_votes: int
    participation: float
    tables: int
    places: int
    winning_tables: int


class TableSummary(BaseModel):
    table_key: str
    department_name: str | None = None
    municipality_name: str | None = None
    zone_code: str | None = None
    polling_place_name: str | None = None
    table_code: str | None = None
    votes: int
    total_table_votes: int
    pct: float
    margin: int
    rival_name: str | None = None
    rival_votes: int | None = None
    winner_label: str | None = None
    winner_votes: int | None = None


class CandidateSummaryResponse(BaseModel):
    candidate: CandidateIdentity
    scope: CandidateScope
    stats: CandidateStats
    top_zones: list[ZoneSummary]
    top_tables: list[TableSummary]
    tables_won: list[TableSummary]
    tables_lost_narrow: list[TableSummary]


class CompetitiveRival(BaseModel):
    rival_name: str
    rival_party: str | None = None
    rival_votes: int
    candidate_votes: int
    tables_candidate_wins: int
    tables_rival_wins: int
    tables_tied: int
    avg_rival_participation: float
    avg_candidate_participation: float


class HeadToHeadPoint(BaseModel):
    table_key: str
    municipality_name: str | None = None
    zone_code: str | None = None
    polling_place_code: str | None = None
    polling_place_name: str | None = None
    table_code: str | None = None
    candidate_votes: int
    rival_votes: int
    vote_difference: int
    winner_name: str
    candidate_pct: float
    rival_pct: float
    rival_name: str


class CompetitiveResponse(BaseModel):
    candidate: CandidateIdentity
    scope: CandidateScope
    total_candidate_tables: int
    rivals: list[CompetitiveRival]
    head_to_head: list[HeadToHeadPoint]


class MunicipalHighlight(BaseModel):
    municipality_name: str | None = None
    department_name: str | None = None
    value: float | int


class MunicipalSummary(BaseModel):
    total_municipalities: int
    total_municipalities_available: int
    best_municipality: MunicipalHighlight | None = None
    most_efficient_municipality: MunicipalHighlight | None = None


class MunicipalRow(BaseModel):
    municipality_name: str
    department_name: str | None = None
    total_votes: int
    total_tables: int
    tables_with_votes: int
    coverage_pct: float
    efficiency: float
    rank_in_department: int
    top_rival_name: str | None = None
    top_rival_votes: int


class MunicipalComparisonResponse(BaseModel):
    candidate: CandidateIdentity
    scope: CandidateScope
    summary: MunicipalSummary
    municipalities: list[MunicipalRow]


class DrilldownContext(BaseModel):
    municipality: str | None = None
    zone_code: str | None = None
    polling_place_code: str | None = None
    polling_place_name: str | None = None


class TableTopRival(BaseModel):
    name: str
    votes: int
    pct: float


class ZoneDrilldownItem(BaseModel):
    zone_code: str | None = None
    candidate_votes: int
    total_votes: int
    candidate_pct: float
    tables_total: int
    tables_with_votes: int
    places_count: int
    rank_in_zone: int
    zone_winner: str | None = None
    zone_winner_votes: int


class PollingPlaceDrilldownItem(BaseModel):
    polling_place_code: str | None = None
    polling_place_name: str | None = None
    candidate_votes: int
    total_votes: int
    candidate_pct: float
    tables_total: int
    tables_with_votes: int
    rank_in_place: int
    place_winner: str | None = None
    place_winner_votes: int


class TableDrilldownItem(BaseModel):
    table_code: str | None = None
    candidate_votes: int
    total_votes: int
    candidate_pct: float
    rank_in_table: int
    table_winner: str | None = None
    table_winner_votes: int
    margin_vs_second: int
    top_rivals: list[TableTopRival]


class ZoneDrilldownResponse(BaseModel):
    level: Literal["zone"]
    context: DrilldownContext
    items: list[ZoneDrilldownItem]


class PollingPlaceDrilldownResponse(BaseModel):
    level: Literal["polling_place"]
    context: DrilldownContext
    items: list[PollingPlaceDrilldownItem]


class TableDrilldownResponse(BaseModel):
    level: Literal["table"]
    context: DrilldownContext
    items: list[TableDrilldownItem]
