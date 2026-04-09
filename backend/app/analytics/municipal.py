from __future__ import annotations

import pandas as pd

from backend.app.analytics.candidate import MUNICIPALITY_CONTEXT


def build_municipal_comparison(
    frame: pd.DataFrame,
    candidate_name: str,
    sort_by: str = "votes",
    limit: int = 30,
) -> tuple[pd.DataFrame, dict[str, object]]:
    municipality_scope = (
        frame.groupby(MUNICIPALITY_CONTEXT, as_index=False)
        .agg(total_tables=("table_id", "nunique"))
        .copy()
    )

    candidate_rows = frame[frame["candidate_name"].eq(candidate_name)].copy()
    if candidate_rows.empty:
        summary = {
            "total_municipalities": 0,
            "total_municipalities_available": int(municipality_scope["municipality_id"].nunique()),
            "best_municipality": None,
            "most_efficient_municipality": None,
        }
        return (
            pd.DataFrame(
                columns=[
                    "municipality_name",
                    "department_name",
                    "total_votes",
                    "total_tables",
                    "tables_with_votes",
                    "coverage_pct",
                    "efficiency",
                    "rank_in_department",
                    "top_rival_name",
                    "top_rival_votes",
                ]
            ),
            summary,
        )

    candidate_summary = (
        candidate_rows.groupby(MUNICIPALITY_CONTEXT, as_index=False)
        .agg(
            total_votes=("votes", "sum"),
            tables_with_votes=("table_id", "nunique"),
        )
        .copy()
    )

    municipality_votes = (
        frame[frame["row_kind"].eq("candidate")]
        .groupby(MUNICIPALITY_CONTEXT + ["candidate_name"], as_index=False)
        .agg(candidate_votes=("votes", "sum"))
    )

    municipality_votes = municipality_votes.sort_values(
        ["municipality_id", "candidate_votes", "candidate_name"],
        ascending=[True, False, True],
    )
    municipality_votes["rank_in_department"] = (
        municipality_votes.groupby("municipality_id")["candidate_votes"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    candidate_rank = municipality_votes[
        municipality_votes["candidate_name"].eq(candidate_name)
    ][["municipality_id", "rank_in_department"]]

    rivals = municipality_votes[municipality_votes["candidate_name"].ne(candidate_name)].copy()
    top_rivals = (
        rivals.groupby("municipality_id", as_index=False)
        .first()[["municipality_id", "candidate_name", "candidate_votes"]]
        .rename(
            columns={
                "candidate_name": "top_rival_name",
                "candidate_votes": "top_rival_votes",
            }
        )
    )

    comparison = (
        municipality_scope.merge(candidate_summary, on=MUNICIPALITY_CONTEXT, how="left")
        .merge(candidate_rank, on="municipality_id", how="left")
        .merge(top_rivals, on="municipality_id", how="left")
    )

    comparison["total_votes"] = comparison["total_votes"].fillna(0).astype("Int64")
    comparison["tables_with_votes"] = comparison["tables_with_votes"].fillna(0).astype("Int64")
    comparison["rank_in_department"] = comparison["rank_in_department"].fillna(0).astype("Int64")
    comparison["top_rival_votes"] = comparison["top_rival_votes"].fillna(0).astype("Int64")
    comparison["coverage_pct"] = (
        comparison["tables_with_votes"].astype("float64")
        / comparison["total_tables"].replace(0, pd.NA).astype("float64")
        * 100
    ).fillna(0.0)
    comparison["efficiency"] = (
        comparison["total_votes"].astype("float64")
        / comparison["tables_with_votes"].replace(0, pd.NA).astype("float64")
    ).fillna(0.0)

    active = comparison[comparison["total_votes"].gt(0)].copy()
    sort_columns = {
        "votes": ["total_votes", "efficiency", "coverage_pct"],
        "efficiency": ["efficiency", "total_votes", "coverage_pct"],
        "coverage": ["coverage_pct", "total_votes", "efficiency"],
    }.get(sort_by, ["total_votes", "efficiency", "coverage_pct"])

    active = active.sort_values(sort_columns, ascending=[False, False, False]).head(limit)

    best = None
    if not active.empty:
        best_row = active.sort_values(["total_votes", "efficiency"], ascending=[False, False]).iloc[0]
        best = {
            "municipality_name": best_row["municipality_name"],
            "department_name": best_row["department_name"],
            "value": int(best_row["total_votes"]),
        }

    most_efficient = None
    if not active.empty:
        efficient_row = active.sort_values(["efficiency", "total_votes"], ascending=[False, False]).iloc[0]
        most_efficient = {
            "municipality_name": efficient_row["municipality_name"],
            "department_name": efficient_row["department_name"],
            "value": float(efficient_row["efficiency"]),
        }

    summary = {
        "total_municipalities": int(comparison["total_votes"].gt(0).sum()),
        "total_municipalities_available": int(comparison["municipality_id"].nunique()),
        "best_municipality": best,
        "most_efficient_municipality": most_efficient,
    }

    return active.reset_index(drop=True), summary
