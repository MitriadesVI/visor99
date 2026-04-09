from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.dataset_loader import CSVFormat, DatasetBundle, DatasetProfile, DatasetSpec
from backend.app.services.normalizer import ColumnMappingResult


def build_sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "1",
                "party_name": "PARTIDO A",
                "candidate_name": "ANA PEREZ",
                "votes": 30,
                "contest_name": "SENADO",
                "candidate_code": "001",
                "row_kind": "candidate",
                "ballot_label": "ANA PEREZ",
                "table_id": "1|1|1|1|1",
                "polling_place_id": "1|1|1|1",
                "municipality_id": "1|1",
            },
            {
                "department_name": "ATLANTICO",
                "municipality_name": "BARRANQUILLA",
                "zone_code": "1",
                "polling_place_code": "1",
                "polling_place_name": "COLEGIO A",
                "table_code": "1",
                "party_name": "PARTIDO B",
                "candidate_name": "JUAN LOPEZ",
                "votes": 18,
                "contest_name": "SENADO",
                "candidate_code": "002",
                "row_kind": "candidate",
                "ballot_label": "JUAN LOPEZ",
                "table_id": "1|1|1|1|1",
                "polling_place_id": "1|1|1|1",
                "municipality_id": "1|1",
            },
            {
                "department_name": "ATLANTICO",
                "municipality_name": "SOLEDAD",
                "zone_code": "2",
                "polling_place_code": "2",
                "polling_place_name": "COLEGIO B",
                "table_code": "1",
                "party_name": "PARTIDO A",
                "candidate_name": "ANA PEREZ",
                "votes": 12,
                "contest_name": "SENADO",
                "candidate_code": "001",
                "row_kind": "candidate",
                "ballot_label": "ANA PEREZ",
                "table_id": "1|2|2|2|1",
                "polling_place_id": "1|2|2|2",
                "municipality_id": "1|2",
            },
            {
                "department_name": "ATLANTICO",
                "municipality_name": "SOLEDAD",
                "zone_code": "2",
                "polling_place_code": "2",
                "polling_place_name": "COLEGIO B",
                "table_code": "1",
                "party_name": "PARTIDO B",
                "candidate_name": "JUAN LOPEZ",
                "votes": 15,
                "contest_name": "SENADO",
                "candidate_code": "002",
                "row_kind": "candidate",
                "ballot_label": "JUAN LOPEZ",
                "table_id": "1|2|2|2|1",
                "polling_place_id": "1|2|2|2",
                "municipality_id": "1|2",
            },
        ]
    )


class FakeStore:
    def __init__(self) -> None:
        frame = build_sample_frame()
        spec = DatasetSpec(
            dataset_id="demo",
            display_name="demo.parquet",
            path=Path("demo.parquet"),
            file_format="parquet",
            row_count=len(frame.index),
        )
        self.bundle = DatasetBundle(
            spec=spec,
            csv_format=CSVFormat(delimiter="parquet", encoding="binary"),
            mapping=ColumnMappingResult(
                canonical_to_raw={},
                raw_to_canonical={},
                unresolved_raw=(),
                missing_required=(),
            ),
            profile=DatasetProfile(
                row_count=len(frame.index),
                available_contests=("SENADO",),
                available_departments=("ATLANTICO",),
                column_names=tuple(frame.columns),
            ),
            data=frame,
        )

    def warm_default_dataset(self) -> None:
        return None

    def list_specs(self) -> list[DatasetSpec]:
        return [self.bundle.spec]

    def get_bundle(self, dataset_ref: str | None = None) -> DatasetBundle:
        return self.bundle


def test_api_endpoints_return_expected_shapes(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.main.DatasetStore", FakeStore)

    with TestClient(app) as client:
        datasets_response = client.get("/api/datasets")
        filters_response = client.get("/api/filters")
        candidate_response = client.get(
            "/api/candidate/summary",
            params={"candidate": "ANA PEREZ", "contest": "SENADO"},
        )
        competitive_response = client.get(
            "/api/competitive/rivals",
            params={"candidate": "ANA PEREZ", "contest": "SENADO"},
        )
        drilldown_zone_response = client.get(
            "/api/candidate/drilldown",
            params={
                "candidate": "ANA PEREZ",
                "contest": "SENADO",
                "municipality": "BARRANQUILLA",
                "level": "zone",
            },
        )
        drilldown_place_response = client.get(
            "/api/candidate/drilldown",
            params={
                "candidate": "ANA PEREZ",
                "contest": "SENADO",
                "municipality": "BARRANQUILLA",
                "level": "polling_place",
                "zone_code": "1",
            },
        )
        drilldown_table_response = client.get(
            "/api/candidate/drilldown",
            params={
                "candidate": "ANA PEREZ",
                "contest": "SENADO",
                "municipality": "BARRANQUILLA",
                "level": "table",
                "zone_code": "1",
                "polling_place_code": "1",
            },
        )
        municipal_response = client.get(
            "/api/municipal/comparison",
            params={"candidate": "ANA PEREZ", "contest": "SENADO"},
        )

    assert datasets_response.status_code == 200
    assert datasets_response.json()[0]["path"] == "demo.parquet"

    assert filters_response.status_code == 200
    assert filters_response.json()["candidates"] == ["ANA PEREZ", "JUAN LOPEZ"]

    assert candidate_response.status_code == 200
    candidate_payload = candidate_response.json()
    assert candidate_payload["candidate"]["name"] == "ANA PEREZ"
    assert candidate_payload["stats"]["total_votes"] == 42
    assert len(candidate_payload["top_tables"]) == 2
    assert candidate_payload["top_tables"][0]["rival_name"] == "JUAN LOPEZ"
    assert candidate_payload["top_tables"][0]["total_table_votes"] == 48
    assert candidate_payload["tables_lost_narrow"][0]["margin"] == -3
    assert candidate_payload["stats"]["narrow_loss_tables"] == 1
    assert candidate_payload["stats"]["narrow_loss_margin_threshold"] == 10

    assert competitive_response.status_code == 200
    competitive_payload = competitive_response.json()
    assert competitive_payload["rivals"][0]["rival_name"] == "JUAN LOPEZ"
    assert competitive_payload["total_candidate_tables"] == 2
    assert "polling_place_name" in competitive_payload["head_to_head"][0]
    assert "candidate_votes" in competitive_payload["head_to_head"][0]

    assert drilldown_zone_response.status_code == 200
    zone_payload = drilldown_zone_response.json()
    assert zone_payload["level"] == "zone"
    assert zone_payload["items"][0]["zone_code"] == "1"

    assert drilldown_place_response.status_code == 200
    place_payload = drilldown_place_response.json()
    assert place_payload["level"] == "polling_place"
    assert place_payload["items"][0]["polling_place_name"] == "COLEGIO A"

    assert drilldown_table_response.status_code == 200
    table_payload = drilldown_table_response.json()
    assert table_payload["level"] == "table"
    assert table_payload["items"][0]["top_rivals"][0]["name"] == "JUAN LOPEZ"

    assert municipal_response.status_code == 200
    municipal_payload = municipal_response.json()
    assert municipal_payload["summary"]["total_municipalities"] == 2
    assert len(municipal_payload["municipalities"]) == 2
