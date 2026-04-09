from __future__ import annotations

import pandas as pd

from backend.app.analytics.candidate import build_candidate_table_performance
from backend.app.config import ClassificationThresholds


def build_competitive_overview(
    frame: pd.DataFrame,
    candidate_name: str,
    thresholds: ClassificationThresholds,
    top_n: int = 5,
    point_limit: int = 500,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    performance = build_candidate_table_performance(frame, candidate_name, thresholds)
    candidate_tables = performance[performance["candidate_votes"].gt(0)].copy()
    total_candidate_tables = int(candidate_tables["table_id"].nunique())

    if candidate_tables.empty:
        empty_rivals = pd.DataFrame(
            columns=[
                "rival_name",
                "rival_party",
                "rival_votes",
                "candidate_votes",
                "tables_candidate_wins",
                "tables_rival_wins",
                "tables_tied",
                "avg_rival_participation",
                "avg_candidate_participation",
            ]
        )
        empty_points = pd.DataFrame(
            columns=[
                "table_key",
                "municipality_name",
                "zone_code",
                "polling_place_code",
                "polling_place_name",
                "table_code",
                "candidate_votes",
                "rival_votes",
                "vote_difference",
                "winner_name",
                "candidate_pct",
                "rival_pct",
                "rival_name",
            ]
        )
        return empty_rivals, empty_points, total_candidate_tables

    shared_tables = frame[frame["table_id"].isin(candidate_tables["table_id"])].copy()
    rival_votes = shared_tables[
        shared_tables["row_kind"].eq("candidate")
        & shared_tables["candidate_name"].notna()
        & shared_tables["candidate_name"].ne(candidate_name)
    ].copy()

    if rival_votes.empty:
        return (
            pd.DataFrame(
                columns=[
                    "rival_name",
                    "rival_party",
                    "rival_votes",
                    "candidate_votes",
                    "tables_candidate_wins",
                    "tables_rival_wins",
                    "tables_tied",
                    "avg_rival_participation",
                    "avg_candidate_participation",
                ]
            ),
            pd.DataFrame(
                columns=[
                    "table_key",
                    "municipality_name",
                    "zone_code",
                    "polling_place_code",
                    "polling_place_name",
                    "table_code",
                    "candidate_votes",
                    "rival_votes",
                    "vote_difference",
                    "winner_name",
                    "candidate_pct",
                    "rival_pct",
                    "rival_name",
                ]
            ),
            total_candidate_tables,
        )

    top_rivals = (
        rival_votes.groupby(["candidate_name", "party_name"], dropna=False, as_index=False)
        .agg(rival_votes=("votes", "sum"))
        .sort_values(["rival_votes", "candidate_name"], ascending=[False, True])
        .head(top_n)
        .rename(columns={"candidate_name": "rival_name", "party_name": "rival_party"})
        .reset_index(drop=True)
    )

    context = candidate_tables[
        [
            "table_id",
            "municipality_name",
            "zone_code",
            "polling_place_code",
            "polling_place_name",
            "table_code",
            "candidate_votes",
            "candidate_share",
            "total_table_votes",
        ]
    ].copy()

    rival_rows: list[dict[str, object]] = []
    head_to_head_frames: list[pd.DataFrame] = []

    for row in top_rivals.itertuples(index=False):
        rival_table_votes = (
            rival_votes[rival_votes["candidate_name"].eq(row.rival_name)]
            .groupby("table_id", as_index=False)
            .agg(rival_votes=("votes", "sum"))
        )

        merged = context.merge(rival_table_votes, on="table_id", how="left")
        merged["rival_votes"] = merged["rival_votes"].fillna(0).astype("Int64")
        merged["rival_share"] = (
            merged["rival_votes"].astype("float64")
            / merged["total_table_votes"].replace(0, pd.NA).astype("float64")
        ).fillna(0.0)

        rival_rows.append(
            {
                "rival_name": row.rival_name,
                "rival_party": row.rival_party,
                "rival_votes": int(row.rival_votes),
                "candidate_votes": int(merged["candidate_votes"].sum()),
                "tables_candidate_wins": int(merged["candidate_votes"].gt(merged["rival_votes"]).sum()),
                "tables_rival_wins": int(merged["rival_votes"].gt(merged["candidate_votes"]).sum()),
                "tables_tied": int(merged["rival_votes"].eq(merged["candidate_votes"]).sum()),
                "avg_rival_participation": float(merged["rival_share"].mean() * 100),
                "avg_candidate_participation": float(merged["candidate_share"].mean() * 100),
            }
        )

        scatter = merged.copy()
        scatter["table_key"] = scatter["table_id"]
        scatter["candidate_pct"] = scatter["candidate_share"] * 100
        scatter["rival_pct"] = scatter["rival_share"] * 100
        scatter["rival_name"] = row.rival_name
        scatter["vote_difference"] = (
            scatter["candidate_votes"].astype("Int64") - scatter["rival_votes"].astype("Int64")
        )
        scatter["winner_name"] = row.rival_name
        scatter.loc[scatter["candidate_votes"].gt(scatter["rival_votes"]), "winner_name"] = candidate_name
        scatter.loc[scatter["candidate_votes"].eq(scatter["rival_votes"]), "winner_name"] = "Empate"
        scatter = scatter.sort_values(
            ["vote_difference", "candidate_votes", "rival_votes"],
            ascending=[True, False, False],
        ).head(point_limit)
        head_to_head_frames.append(
            scatter[
                [
                    "table_key",
                    "municipality_name",
                    "zone_code",
                    "polling_place_code",
                    "polling_place_name",
                    "table_code",
                    "candidate_votes",
                    "rival_votes",
                    "vote_difference",
                    "winner_name",
                    "candidate_pct",
                    "rival_pct",
                    "rival_name",
                ]
            ]
        )

    rivals_frame = pd.DataFrame.from_records(rival_rows)
    head_to_head = (
        pd.concat(head_to_head_frames, ignore_index=True)
        if head_to_head_frames
        else pd.DataFrame(
            columns=[
                "table_key",
                "municipality_name",
                "zone_code",
                "polling_place_code",
                "polling_place_name",
                "table_code",
                "candidate_votes",
                "rival_votes",
                "vote_difference",
                "winner_name",
                "candidate_pct",
                "rival_pct",
                "rival_name",
            ]
        )
    )

    return rivals_frame, head_to_head, total_candidate_tables
