from __future__ import annotations

import pandas as pd

from backend.app.analytics.candidate import build_candidate_table_performance, tables_lost_by_close_margin
from backend.app.analytics.competitive import build_competitive_overview
from backend.app.analytics.municipal import build_municipal_comparison
from backend.app.config import ClassificationThresholds


def build_sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "table_id": "1|1|1|1|1",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "1",
                "candidate_name": "ANA PEREZ",
                "party_name": "PARTIDO A",
                "ballot_label": "ANA PEREZ",
                "votes": 30,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|1|1|1|1",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "1",
                "candidate_name": "JUAN LOPEZ",
                "party_name": "PARTIDO B",
                "ballot_label": "JUAN LOPEZ",
                "votes": 18,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|1|1|1|1",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "1",
                "candidate_name": "LUISA DIAZ",
                "party_name": "PARTIDO C",
                "ballot_label": "LUISA DIAZ",
                "votes": 12,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|1|1|1|1",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "1",
                "candidate_name": pd.NA,
                "party_name": "PARTIDO A",
                "ballot_label": "PARTIDO A",
                "votes": 4,
                "row_kind": "list",
            },
            {
                "table_id": "1|1|1|1|2",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "2",
                "candidate_name": "ANA PEREZ",
                "party_name": "PARTIDO A",
                "ballot_label": "ANA PEREZ",
                "votes": 12,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|1|1|1|2",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "2",
                "candidate_name": "JUAN LOPEZ",
                "party_name": "PARTIDO B",
                "ballot_label": "JUAN LOPEZ",
                "votes": 15,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|1|1|1|2",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "2",
                "candidate_name": "LUISA DIAZ",
                "party_name": "PARTIDO C",
                "ballot_label": "LUISA DIAZ",
                "votes": 4,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|1|1|1|2",
                "municipality_id": "1|1",
                "polling_place_id": "1|1|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "2",
                "candidate_name": pd.NA,
                "party_name": "PARTIDO A",
                "ballot_label": "PARTIDO A",
                "votes": 2,
                "row_kind": "list",
            },
            {
                "table_id": "1|2|1|1|1",
                "municipality_id": "1|2",
                "polling_place_id": "1|2|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "SOLEDAD",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO B",
                "table_code": "1",
                "candidate_name": "ANA PEREZ",
                "party_name": "PARTIDO A",
                "ballot_label": "ANA PEREZ",
                "votes": 20,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|2|1|1|1",
                "municipality_id": "1|2",
                "polling_place_id": "1|2|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "SOLEDAD",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO B",
                "table_code": "1",
                "candidate_name": "JUAN LOPEZ",
                "party_name": "PARTIDO B",
                "ballot_label": "JUAN LOPEZ",
                "votes": 35,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|2|1|1|1",
                "municipality_id": "1|2",
                "polling_place_id": "1|2|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "SOLEDAD",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO B",
                "table_code": "1",
                "candidate_name": "LUISA DIAZ",
                "party_name": "PARTIDO C",
                "ballot_label": "LUISA DIAZ",
                "votes": 8,
                "row_kind": "candidate",
            },
            {
                "table_id": "1|2|1|1|1",
                "municipality_id": "1|2",
                "polling_place_id": "1|2|1|1",
                "department_name": "ATLANTICO",
                "municipality_name": "SOLEDAD",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO B",
                "table_code": "1",
                "candidate_name": pd.NA,
                "party_name": "PARTIDO A",
                "ballot_label": "PARTIDO A",
                "votes": 3,
                "row_kind": "list",
            },
        ]
    )


def test_competitive_overview_ranks_rivals_on_shared_tables() -> None:
    frame = build_sample_frame()

    rivals, points, total_tables = build_competitive_overview(
        frame,
        candidate_name="ANA PEREZ",
        thresholds=ClassificationThresholds(dominant_share=0.30, competitive_share=0.15),
        top_n=2,
        point_limit=10,
    )

    assert total_tables == 3
    assert rivals.iloc[0]["rival_name"] == "JUAN LOPEZ"
    assert int(rivals.iloc[0]["rival_votes"]) == 68
    assert int(rivals.iloc[0]["tables_candidate_wins"]) == 1
    assert int(rivals.iloc[0]["tables_rival_wins"]) == 2
    assert "polling_place_name" in points.columns
    assert "candidate_votes" in points.columns
    assert set(points["rival_name"]) == {"JUAN LOPEZ", "LUISA DIAZ"}


def test_municipal_comparison_calculates_efficiency_and_rivals() -> None:
    frame = build_sample_frame()

    comparison, summary = build_municipal_comparison(
        frame,
        candidate_name="ANA PEREZ",
        sort_by="efficiency",
        limit=10,
    )

    assert comparison.iloc[0]["municipality_name"] == "BARRANQUILLA"
    assert round(float(comparison.iloc[0]["efficiency"]), 2) == 21.0
    assert comparison.iloc[0]["top_rival_name"] == "JUAN LOPEZ"
    assert summary["total_municipalities"] == 2
    assert summary["best_municipality"]["municipality_name"] == "BARRANQUILLA"


def test_tables_lost_by_close_margin_keeps_negative_margin_and_threshold() -> None:
    frame = build_sample_frame()
    performance = build_candidate_table_performance(
        frame,
        candidate_name="ANA PEREZ",
        thresholds=ClassificationThresholds(dominant_share=0.30, competitive_share=0.15),
    )

    lost = tables_lost_by_close_margin(performance, margin_threshold=10)

    assert len(lost.index) == 1
    assert int(lost.iloc[0]["margin_against_best_competitor"]) == -3
    assert lost.iloc[0]["best_competitor_label"] == "JUAN LOPEZ"
