from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from backend.app.config import ClassificationThresholds


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

ZONE_CONTEXT = [
    "department_name",
    "municipality_name",
    "zone_code",
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

    return (
        candidates.groupby(["candidate_name", "party_name"], dropna=False, as_index=False)
        .agg(votes=("votes", "sum"))
        .sort_values(["votes", "candidate_name"], ascending=[False, True])
        .reset_index(drop=True)
    )


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
        .rename(columns={"ballot_label": "winner_label", "option_votes": "winner_votes"})[
            ["table_id", "winner_label", "winner_votes"]
        ]
    )

    best_competitor = (
        option_votes[option_votes["ballot_label"].ne(candidate_name)]
        .drop_duplicates(subset=["table_id"])
        .rename(
            columns={
                "ballot_label": "best_competitor_label",
                "option_votes": "best_competitor_votes",
            }
        )[["table_id", "best_competitor_label", "best_competitor_votes"]]
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


def _match_code(series: pd.Series, code: str | None) -> pd.Series:
    if code is None:
        return pd.Series(True, index=series.index)
    return series.astype("string").fillna("").eq(str(code))


def _build_ballot_rankings(
    frame: pd.DataFrame,
    group_fields: list[str],
    candidate_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ballot_votes = (
        frame.groupby(group_fields + ["ballot_label"], as_index=False, dropna=False)
        .agg(ballot_votes=("votes", "sum"))
        .sort_values(
            group_fields + ["ballot_votes", "ballot_label"],
            ascending=[True] * len(group_fields) + [False, True],
        )
        .reset_index(drop=True)
    )

    if ballot_votes.empty:
        empty_group = pd.DataFrame(columns=group_fields)
        return (
            ballot_votes,
            empty_group.copy(),
            empty_group.copy(),
            empty_group.copy(),
        )

    ballot_votes["rank"] = (
        ballot_votes.groupby(group_fields, dropna=False)["ballot_votes"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    winners = ballot_votes.drop_duplicates(subset=group_fields).rename(
        columns={"ballot_label": "winner_label", "ballot_votes": "winner_votes"}
    )[group_fields + ["winner_label", "winner_votes"]]

    candidate_rank = ballot_votes[ballot_votes["ballot_label"].eq(candidate_name)].rename(
        columns={"rank": "candidate_rank"}
    )[group_fields + ["candidate_rank"]]

    second_place = ballot_votes[ballot_votes["rank"].eq(2)].rename(
        columns={"ballot_votes": "second_votes"}
    )[group_fields + ["second_votes"]]

    return ballot_votes, winners, candidate_rank, second_place


def build_zone_drilldown(
    frame: pd.DataFrame,
    candidate_name: str,
    thresholds: ClassificationThresholds,
) -> pd.DataFrame:
    performance = build_candidate_table_performance(frame, candidate_name, thresholds)
    if performance.empty:
        return pd.DataFrame(
            columns=[
                "zone_code",
                "candidate_votes",
                "total_votes",
                "candidate_pct",
                "tables_total",
                "tables_with_votes",
                "places_count",
                "rank_in_zone",
                "zone_winner",
                "zone_winner_votes",
            ]
        )

    zone_summary = (
        performance.groupby(ZONE_CONTEXT, as_index=False, dropna=False)
        .agg(
            candidate_votes=("candidate_votes", "sum"),
            total_votes=("total_table_votes", "sum"),
            tables_total=("table_id", "nunique"),
            tables_with_votes=("candidate_votes", lambda values: int(values.gt(0).sum())),
            places_count=("polling_place_id", "nunique"),
        )
        .copy()
    )
    zone_summary["candidate_pct"] = (
        zone_summary["candidate_votes"].astype("float64")
        / zone_summary["total_votes"].replace(0, pd.NA).astype("float64")
        * 100
    ).fillna(0.0)

    _, winners, candidate_rank, _ = _build_ballot_rankings(frame, ZONE_CONTEXT, candidate_name)
    zone_summary = (
        zone_summary.merge(candidate_rank, on=ZONE_CONTEXT, how="left")
        .merge(winners, on=ZONE_CONTEXT, how="left")
        .rename(columns={"winner_label": "zone_winner", "winner_votes": "zone_winner_votes"})
    )

    zone_summary["rank_in_zone"] = zone_summary["candidate_rank"].fillna(0).astype("Int64")
    zone_summary["zone_winner_votes"] = zone_summary["zone_winner_votes"].fillna(0).astype("Int64")

    return zone_summary[
        [
            "zone_code",
            "candidate_votes",
            "total_votes",
            "candidate_pct",
            "tables_total",
            "tables_with_votes",
            "places_count",
            "rank_in_zone",
            "zone_winner",
            "zone_winner_votes",
        ]
    ].sort_values(
        ["candidate_votes", "candidate_pct", "zone_code"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def build_polling_place_drilldown(
    frame: pd.DataFrame,
    candidate_name: str,
    thresholds: ClassificationThresholds,
    zone_code: str,
) -> pd.DataFrame:
    zone_frame = frame[_match_code(frame["zone_code"], zone_code)].copy()
    performance = build_candidate_table_performance(zone_frame, candidate_name, thresholds)
    if performance.empty:
        return pd.DataFrame(
            columns=[
                "polling_place_code",
                "polling_place_name",
                "candidate_votes",
                "total_votes",
                "candidate_pct",
                "tables_total",
                "tables_with_votes",
                "rank_in_place",
                "place_winner",
                "place_winner_votes",
            ]
        )

    places = (
        performance.groupby(PLACE_CONTEXT, as_index=False, dropna=False)
        .agg(
            candidate_votes=("candidate_votes", "sum"),
            total_votes=("total_table_votes", "sum"),
            tables_total=("table_id", "nunique"),
            tables_with_votes=("candidate_votes", lambda values: int(values.gt(0).sum())),
        )
        .copy()
    )
    places["candidate_pct"] = (
        places["candidate_votes"].astype("float64")
        / places["total_votes"].replace(0, pd.NA).astype("float64")
        * 100
    ).fillna(0.0)

    _, winners, candidate_rank, _ = _build_ballot_rankings(zone_frame, PLACE_CONTEXT, candidate_name)
    places = (
        places.merge(candidate_rank, on=PLACE_CONTEXT, how="left")
        .merge(winners, on=PLACE_CONTEXT, how="left")
        .rename(columns={"winner_label": "place_winner", "winner_votes": "place_winner_votes"})
    )

    places["rank_in_place"] = places["candidate_rank"].fillna(0).astype("Int64")
    places["place_winner_votes"] = places["place_winner_votes"].fillna(0).astype("Int64")

    return places[
        [
            "polling_place_code",
            "polling_place_name",
            "candidate_votes",
            "total_votes",
            "candidate_pct",
            "tables_total",
            "tables_with_votes",
            "rank_in_place",
            "place_winner",
            "place_winner_votes",
        ]
    ].sort_values(
        ["candidate_votes", "candidate_pct", "polling_place_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def build_table_drilldown(
    frame: pd.DataFrame,
    candidate_name: str,
    thresholds: ClassificationThresholds,
    zone_code: str,
    polling_place_code: str,
) -> pd.DataFrame:
    place_frame = frame[
        _match_code(frame["zone_code"], zone_code)
        & _match_code(frame["polling_place_code"], polling_place_code)
    ].copy()
    performance = build_candidate_table_performance(place_frame, candidate_name, thresholds)
    if performance.empty:
        return pd.DataFrame(
            columns=[
                "table_code",
                "candidate_votes",
                "total_votes",
                "candidate_pct",
                "rank_in_table",
                "table_winner",
                "table_winner_votes",
                "margin_vs_second",
                "top_rivals",
            ]
        )

    ballot_votes, _, candidate_rank, second_place = _build_ballot_rankings(
        place_frame, ["table_id"], candidate_name
    )

    rivals = ballot_votes[ballot_votes["ballot_label"].ne(candidate_name)].copy()
    total_votes_map = performance.set_index("table_id")["total_table_votes"].to_dict()
    top_rivals: dict[str, list[dict[str, object]]] = {}
    for table_id, group in rivals.groupby("table_id", dropna=False):
        items: list[dict[str, object]] = []
        total_table_votes = float(total_votes_map.get(table_id, 0) or 0)
        for rival in group.head(5).itertuples(index=False):
            pct = (float(rival.ballot_votes) / total_table_votes * 100) if total_table_votes else 0.0
            items.append(
                {
                    "name": rival.ballot_label,
                    "votes": int(rival.ballot_votes),
                    "pct": pct,
                }
            )
        top_rivals[str(table_id)] = items

    tables = (
        performance.merge(candidate_rank, on="table_id", how="left")
        .merge(second_place, on="table_id", how="left")
        .copy()
    )
    tables["candidate_pct"] = tables["candidate_share"] * 100
    tables["rank_in_table"] = tables["candidate_rank"].fillna(0).astype("Int64")
    tables["second_votes"] = tables["second_votes"].fillna(0).astype("Int64")
    tables["margin_vs_second"] = (tables["winner_votes"] - tables["second_votes"]).astype("Int64")
    tables["top_rivals"] = tables["table_id"].map(lambda value: top_rivals.get(str(value), []))

    return tables.rename(
        columns={
            "total_table_votes": "total_votes",
            "winner_label": "table_winner",
            "winner_votes": "table_winner_votes",
        }
    )[
        [
            "table_code",
            "candidate_votes",
            "total_votes",
            "candidate_pct",
            "rank_in_table",
            "table_winner",
            "table_winner_votes",
            "margin_vs_second",
            "top_rivals",
        ]
    ].sort_values(
        ["candidate_votes", "candidate_pct", "table_code"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def summarize_candidate_scope(frame: pd.DataFrame) -> dict[str, float | int]:
    active_tables = frame[frame["candidate_votes"].gt(0)].copy()
    average_share = (
        float(active_tables["candidate_share"].mean()) if not active_tables.empty else 0.0
    )

    total_tables = int(frame["table_id"].nunique())
    tables_with_votes = int(active_tables["table_id"].nunique())

    return {
        "total_votes": int(frame["candidate_votes"].sum()),
        "total_tables": total_tables,
        "tables_with_votes": tables_with_votes,
        "tables_without_votes": max(total_tables - tables_with_votes, 0),
        "coverage_pct": (tables_with_votes / total_tables * 100) if total_tables else 0.0,
        "avg_participation": average_share * 100,
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


def rank_zones(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "department_name",
                "municipality_name",
                "zone_code",
                "zone_label",
                "candidate_votes",
                "total_votes",
                "tables",
                "polling_places",
                "winning_tables",
                "candidate_share",
            ]
        )

    ranked = (
        frame.groupby(["department_name", "municipality_name", "zone_code"], as_index=False)
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
    ranked["zone_label"] = "Zona " + ranked["zone_code"].astype("string").fillna("S/N")
    return ranked.sort_values(["candidate_votes", "candidate_share"], ascending=[False, False])


def tables_won(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["is_winner"] & frame["candidate_votes"].gt(0)].sort_values(
        ["margin_against_best_competitor", "candidate_votes"],
        ascending=[False, False],
    )


def tables_lost_by_close_margin(frame: pd.DataFrame, margin_threshold: int = 10) -> pd.DataFrame:
    lost = frame[(~frame["is_winner"]) & frame["candidate_votes"].gt(0)].copy()
    lost = lost[lost["margin_against_best_competitor"].ge(-margin_threshold)]
    return lost.sort_values(
        ["margin_against_best_competitor", "candidate_votes"],
        ascending=[False, False],
    )


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
