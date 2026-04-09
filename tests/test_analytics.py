from __future__ import annotations

import pandas as pd

from app.analytics.electoral import (
    build_candidate_table_performance,
    classification_distribution,
    rank_municipalities,
    tables_lost_by_close_margin,
)
from app.config import ClassificationThresholds


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
                "candidate_name": pd.NA,
                "party_name": "PARTIDO A",
                "ballot_label": "PARTIDO A",
                "votes": 2,
                "row_kind": "list",
            },
        ]
    )


def test_candidate_table_performance_calculates_margin_and_share() -> None:
    frame = build_sample_frame()

    performance = build_candidate_table_performance(
        frame,
        candidate_name="ANA PEREZ",
        thresholds=ClassificationThresholds(dominant_share=0.30, competitive_share=0.15),
    )

    top_row = performance.iloc[0]
    second_row = performance.iloc[1]

    assert int(top_row["candidate_votes"]) == 30
    assert round(float(top_row["candidate_share"]), 4) == round(30 / 52, 4)
    assert bool(top_row["is_winner"]) is True
    assert int(second_row["margin_against_best_competitor"]) == -3


def test_rankings_and_classification_distribution_are_generated() -> None:
    frame = build_sample_frame()
    performance = build_candidate_table_performance(
        frame,
        candidate_name="ANA PEREZ",
        thresholds=ClassificationThresholds(dominant_share=0.45, competitive_share=0.15),
    )

    municipalities = rank_municipalities(performance)
    distribution = classification_distribution(performance)
    close_losses = tables_lost_by_close_margin(performance)

    assert municipalities.iloc[0]["municipality_name"] == "BARRANQUILLA"
    assert set(distribution["classification"].astype(str)) == {"dominante", "competitivo"}
    assert int(close_losses.iloc[0]["loss_margin"]) == 3
