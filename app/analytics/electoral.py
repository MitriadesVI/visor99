from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from app.config import ClassificationThresholds


TABLE_CONTEXT = [
    "table_id",
    "department_name",
    "municipality_name",
    "zone_code",
    "polling_place_code",
    "polling_place_name",
    "table_code",
    "municipality_id",
    "polling_place_id",
]

PLACE_CONTEXT = [
    "polling_place_id",
    "department_name",
    "municipality_name",
    "zone_code",
    "polling_place_code",
    "polling_place_name",
]

MUNICIPALITY_CONTEXT = [
    "municipality_id",
    "department_name",
    "municipality_name",
]


def apply_scope_filters(
    frame: pd.DataFrame,
    contest_name: str | None = None,
    department_name: str | None = None,
    municipality_name: str | None = None,
    party_name: str | None = None,
) -> pd.DataFrame:
    filtered = frame

    if contest_name:
        filtered = filtered[filtered["contest_name"].eq(contest_name)]
    if department_name and department_name != "Todos":
        filtered = filtered[filtered["department_name"].eq(department_name)]
    if municipality_name and municipality_name != "Todos":
        filtered = filtered[filtered["municipality_name"].eq(municipality_name)]
    if party_name and party_name != "Todos":
        filtered = filtered[filtered["party_name"].eq(party_name)]

    return filtered.copy()


def candidate_vote_options(frame: pd.DataFrame) -> pd.DataFrame:
    candidates = frame[frame["row_kind"].eq("candidate")].copy()
    if candidates.empty:
        return pd.DataFrame(columns=["candidate_name", "party_name", "votes"])

    options = (
        candidates.groupby(["candidate_name", "party_name"], dropna=False, as_index=False)
        .agg(votes=("votes", "sum"))
        .sort_values(["votes", "candidate_name"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return options


def build_candidate_table_performance(
    frame: pd.DataFrame,
    candidate_name: str,
    thresholds: ClassificationThresholds,
) -> pd.DataFrame:
    table_context = (
        frame.groupby("table_id", as_index=False)
        .agg(
            department_name=("department_name", "first"),
            municipality_name=("municipality_name", "first"),
            zone_code=("zone_code", "first"),
            polling_place_code=("polling_place_code", "first"),
            polling_place_name=("polling_place_name", "first"),
            table_code=("table_code", "first"),
            municipality_id=("municipality_id", "first"),
            polling_place_id=("polling_place_id", "first"),
            total_table_votes=("votes", "sum"),
        )
        .copy()
    )

    candidate_votes = (
        frame[frame["candidate_name"].eq(candidate_name)]
        .groupby("table_id", as_index=False)
        .agg(candidate_votes=("votes", "sum"))
    )

    option_votes = (
        frame.groupby(["table_id", "ballot_label"], as_index=False)
        .agg(option_votes=("votes", "sum"))
        .sort_values(["table_id", "option_votes", "ballot_label"], ascending=[True, False, True])
    )

    winners = (
        option_votes.drop_duplicates(subset=["table_id"])
        .rename(
            columns={
                "ballot_label": "winner_label",
                "option_votes": "winner_votes",
            }
        )[["table_id", "winner_label", "winner_votes"]]
    )

    best_competitor = (
        option_votes[option_votes["ballot_label"].ne(candidate_name)]
        .groupby("table_id", as_index=False)
        .agg(best_competitor_votes=("option_votes", "max"))
    )

    performance = (
        table_context.merge(candidate_votes, on="table_id", how="left")
        .merge(winners, on="table_id", how="left")
        .merge(best_competitor, on="table_id", how="left")
    )

    performance["candidate_votes"] = performance["candidate_votes"].fillna(0).astype("Int64")
    performance["winner_votes"] = performance["winner_votes"].fillna(0).astype("Int64")
    performance["best_competitor_votes"] = (
        performance["best_competitor_votes"].fillna(0).astype("Int64")
    )
    performance["candidate_share"] = (
        performance["candidate_votes"].astype("float64")
        / performance["total_table_votes"].replace(0, pd.NA).astype("float64")
    ).fillna(0.0)
    performance["margin_against_best_competitor"] = (
        performance["candidate_votes"] - performance["best_competitor_votes"]
    ).astype("Int64")
    performance["is_winner"] = performance["winner_label"].eq(candidate_name)
    performance["classification"] = performance["candidate_share"].map(
        lambda share: classify_share(share, thresholds)
    )

    return performance.sort_values(
        ["candidate_votes", "candidate_share", "table_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def summarize_candidate_scope(frame: pd.DataFrame) -> dict[str, float | int]:
    active_tables = frame[frame["candidate_votes"].gt(0)].copy()
    average_share = (
        float(active_tables["candidate_share"].mean()) if not active_tables.empty else 0.0
    )

    return {
        "total_votes": int(frame["candidate_votes"].sum()),
        "tables_with_votes": int(active_tables["table_id"].nunique()),
        "average_share": average_share,
        "municipalities_with_votes": int(active_tables["municipality_id"].nunique()),
        "winning_tables": int(frame["is_winner"].sum()),
    }


def rank_tables(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["candidate_votes"].gt(0)].sort_values(
        ["candidate_votes", "candidate_share"],
        ascending=[False, False],
    )


def rank_polling_places(frame: pd.DataFrame) -> pd.DataFrame:
    ranked = (
        frame.groupby(PLACE_CONTEXT, as_index=False)
        .agg(
            candidate_votes=("candidate_votes", "sum"),
            total_votes=("total_table_votes", "sum"),
            tables=("table_id", "nunique"),
            tables_with_votes=("candidate_votes", lambda values: int(values.gt(0).sum())),
            winning_tables=("is_winner", "sum"),
        )
        .copy()
    )
    ranked["candidate_share"] = (
        ranked["candidate_votes"].astype("float64")
        / ranked["total_votes"].replace(0, pd.NA).astype("float64")
    ).fillna(0.0)
    return ranked.sort_values(["candidate_votes", "candidate_share"], ascending=[False, False])


def rank_municipalities(frame: pd.DataFrame) -> pd.DataFrame:
    ranked = (
        frame.groupby(MUNICIPALITY_CONTEXT, as_index=False)
        .agg(
            candidate_votes=("candidate_votes", "sum"),
            total_votes=("total_table_votes", "sum"),
            tables=("table_id", "nunique"),
            polling_places=("polling_place_id", "nunique"),
            winning_tables=("is_winner", "sum"),
        )
        .copy()
    )
    ranked["candidate_share"] = (
        ranked["candidate_votes"].astype("float64")
        / ranked["total_votes"].replace(0, pd.NA).astype("float64")
    ).fillna(0.0)
    return ranked.sort_values(["candidate_share", "candidate_votes"], ascending=[False, False])


def tables_won(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["is_winner"] & frame["candidate_votes"].gt(0)].sort_values(
        ["margin_against_best_competitor", "candidate_votes"],
        ascending=[False, False],
    )


def tables_lost_by_close_margin(frame: pd.DataFrame) -> pd.DataFrame:
    lost = frame[(~frame["is_winner"]) & frame["candidate_votes"].gt(0)].copy()
    lost["loss_margin"] = (-lost["margin_against_best_competitor"]).astype("Int64")
    return lost.sort_values(["loss_margin", "candidate_votes"], ascending=[True, False])


def classification_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    distribution = (
        frame[frame["candidate_votes"].gt(0)]
        .groupby("classification", as_index=False)
        .agg(tables=("table_id", "nunique"))
    )
    order = ["dominante", "competitivo", "debil"]
    distribution["classification"] = pd.Categorical(
        distribution["classification"], categories=order, ordered=True
    )
    return distribution.sort_values("classification")


def classify_share(share: float, thresholds: ClassificationThresholds) -> str:
    if share >= thresholds.dominant_share:
        return "dominante"
    if share >= thresholds.competitive_share:
        return "competitivo"
    return "debil"


def thresholds_as_dict(thresholds: ClassificationThresholds) -> dict[str, float]:
    return asdict(thresholds)

