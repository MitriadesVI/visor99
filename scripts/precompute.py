#!/usr/bin/env python3
"""Pre-compute all JSON files from the parquet so the backend becomes a static file server."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "datos"
DEFAULT_PARQUET = DATA_DIR / "elecciones 2026" / "nacional.parquet"
OUTPUT_DIR = PROJECT_ROOT / "precomputed"

DEFAULT_CANDIDATE = "GONZALO DIMAS BAUTE GONZALEZ"
DEFAULT_CONTEST = "SENADO"

# Thresholds (must match config.py)
DOMINANT_SHARE = 0.20
COMPETITIVE_SHARE = 0.08
NARROW_LOSS_MARGIN = 10

# Limits
TOP_TABLES_LIMIT = 50
TABLES_WON_LIMIT = 50
TABLES_LOST_LIMIT = 50
TOP_ZONES_LIMIT = 8
TOP_RIVALS = 15
HEAD_TO_HEAD_LIMIT = 500
MUNICIPAL_LIMIT = 30

# ---------------------------------------------------------------------------
# Filename sanitisation
# ---------------------------------------------------------------------------
_SANITIZE_RE = re.compile(r"[^A-Z0-9_]")


def sanitize(name: str) -> str:
    """Turn a display name into a safe filename component."""
    return _SANITIZE_RE.sub("_", name.upper().strip()).strip("_") or "UNKNOWN"


# ---------------------------------------------------------------------------
# Enrichment (mirrors query_engine.py)
# ---------------------------------------------------------------------------

def _compound_key(row: pd.Series, cols: list[str]) -> str:
    return "|".join(str(row.get(c, "NA") or "NA") for c in cols)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed columns like the DuckDB query_engine does."""
    df = df.copy()
    df["table_id"] = df.apply(
        lambda r: _compound_key(r, ["department_code", "municipality_code", "zone_code", "polling_place_code", "table_code"]),
        axis=1,
    )
    df["polling_place_id"] = df.apply(
        lambda r: _compound_key(r, ["department_code", "municipality_code", "zone_code", "polling_place_code"]),
        axis=1,
    )
    df["municipality_id"] = df.apply(
        lambda r: _compound_key(r, ["department_code", "municipality_code"]),
        axis=1,
    )
    ccode = df["candidate_code"].astype(str).fillna("0")
    df["row_kind"] = "candidate"
    df.loc[ccode.eq("0") | ccode.eq(""), "row_kind"] = "list"

    cname = df["candidate_name"].astype(str).fillna("").str.strip()
    pname = df["party_name"].astype(str).fillna("").str.strip()

    ballot = pd.Series("SIN_ETIQUETA", index=df.index)
    # For candidates: prefer candidate_name, then party_name
    is_cand = df["row_kind"].eq("candidate")
    ballot[is_cand] = cname.where(cname.ne(""), pname).where(cname.ne("") | pname.ne(""), "SIN_ETIQUETA")
    # For lists: prefer party_name, then candidate_name
    is_list = ~is_cand
    ballot[is_list] = pname.where(pname.ne(""), cname).where(pname.ne("") | cname.ne(""), "SIN_ETIQUETA")

    df["ballot_label"] = ballot
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype("int64")
    return df


# ---------------------------------------------------------------------------
# Analytics helpers (mirrors analytics/*.py)
# ---------------------------------------------------------------------------

def classify_share(share: float) -> str:
    if share >= DOMINANT_SHARE:
        return "dominante"
    if share >= COMPETITIVE_SHARE:
        return "competitivo"
    return "debil"


def build_table_performance(frame: pd.DataFrame, candidate_name: str) -> pd.DataFrame:
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
        .rename(columns={"ballot_label": "best_competitor_label", "option_votes": "best_competitor_votes"})[
            ["table_id", "best_competitor_label", "best_competitor_votes"]
        ]
    )

    perf = (
        table_context.merge(candidate_votes, on="table_id", how="left")
        .merge(winners, on="table_id", how="left")
        .merge(best_competitor, on="table_id", how="left")
    )
    perf["candidate_votes"] = perf["candidate_votes"].fillna(0).astype("int64")
    perf["winner_votes"] = perf["winner_votes"].fillna(0).astype("int64")
    perf["best_competitor_votes"] = perf["best_competitor_votes"].fillna(0).astype("int64")
    perf["candidate_share"] = (
        perf["candidate_votes"] / perf["total_table_votes"].replace(0, pd.NA)
    ).fillna(0.0)
    perf["margin_against_best_competitor"] = perf["candidate_votes"] - perf["best_competitor_votes"]
    perf["is_winner"] = perf["winner_label"].eq(candidate_name)
    perf["classification"] = perf["candidate_share"].map(classify_share)
    return perf.sort_values(["candidate_votes", "candidate_share", "table_id"], ascending=[False, False, True]).reset_index(drop=True)


def _ballot_rankings(frame: pd.DataFrame, group_fields: list[str], candidate_name: str):
    ballot_votes = (
        frame.groupby(group_fields + ["ballot_label"], as_index=False, dropna=False)
        .agg(ballot_votes=("votes", "sum"))
        .sort_values(group_fields + ["ballot_votes", "ballot_label"],
                     ascending=[True] * len(group_fields) + [False, True])
        .reset_index(drop=True)
    )
    if ballot_votes.empty:
        empty_group = pd.DataFrame(columns=group_fields)
        return ballot_votes, empty_group.copy(), empty_group.copy(), empty_group.copy()

    ballot_votes["rank"] = (
        ballot_votes.groupby(group_fields, dropna=False)["ballot_votes"]
        .rank(method="dense", ascending=False).astype(int)
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


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------

def _clean(obj):
    """Make object JSON-serializable: convert numpy/pandas types."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    if isinstance(obj, float):
        if pd.isna(obj):
            return None
        return round(obj, 4)
    if hasattr(obj, "item"):  # numpy scalar
        return obj.item()
    if pd.isna(obj):
        return None
    return obj


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_clean(data), f, ensure_ascii=False, separators=(",", ":"))


def records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    cleaned = df.astype(object).where(pd.notna(df), None)
    return [_clean(row) for row in cleaned.to_dict(orient="records")]


# ---------------------------------------------------------------------------
# Precompute: datasets.json
# ---------------------------------------------------------------------------

def precompute_datasets(parquet_path: Path) -> dict:
    row_count = pq.ParquetFile(parquet_path).metadata.num_rows
    rel = parquet_path.relative_to(DATA_DIR)
    item = {
        "name": parquet_path.name,
        "path": rel.as_posix(),
        "format": "parquet",
        "row_count": row_count,
    }
    write_json(OUTPUT_DIR / "datasets.json", [item])
    return item


# ---------------------------------------------------------------------------
# Precompute: filters
# ---------------------------------------------------------------------------

def precompute_filters(df: pd.DataFrame):
    """Write filters/all.json and filters/{DEPT}.json for each department."""
    contest_df = df[df["contest_name"].eq(DEFAULT_CONTEST)]

    contests = sorted(df["contest_name"].dropna().unique().tolist())
    departments = sorted(contest_df["department_name"].dropna().unique().tolist())

    # Global filters
    municipalities = sorted(contest_df["municipality_name"].dropna().unique().tolist())
    parties = sorted(contest_df["party_name"].dropna().astype(str).loc[lambda s: s.str.strip().ne("")].unique().tolist())

    cand_df = contest_df[contest_df["row_kind"].eq("candidate") & contest_df["candidate_name"].notna()]
    candidates = (
        cand_df.groupby("candidate_name", as_index=False)
        .agg(total=("votes", "sum"))
        .sort_values(["total", "candidate_name"], ascending=[False, True])["candidate_name"]
        .tolist()
    )

    write_json(OUTPUT_DIR / "filters" / "all.json", {
        "contests": contests,
        "departments": departments,
        "municipalities": municipalities,
        "parties": parties,
        "candidates": candidates,
    })

    # Per-department filters
    for dept in departments:
        dept_df = contest_df[contest_df["department_name"].eq(dept)]
        munis = sorted(dept_df["municipality_name"].dropna().unique().tolist())
        pts = sorted(dept_df["party_name"].dropna().astype(str).loc[lambda s: s.str.strip().ne("")].unique().tolist())
        dept_cand = dept_df[dept_df["row_kind"].eq("candidate") & dept_df["candidate_name"].notna()]
        cands = (
            dept_cand.groupby("candidate_name", as_index=False)
            .agg(total=("votes", "sum"))
            .sort_values(["total", "candidate_name"], ascending=[False, True])["candidate_name"]
            .tolist()
        )
        write_json(OUTPUT_DIR / "filters" / f"{sanitize(dept)}.json", {
            "contests": contests,
            "departments": departments,
            "municipalities": munis,
            "parties": pts,
            "candidates": cands,
        })


# ---------------------------------------------------------------------------
# Precompute: candidate summary (per dept+muni)
# ---------------------------------------------------------------------------

DETAIL_COLUMNS = [
    "table_key", "municipality_name", "zone_code", "polling_place_name",
    "table_code", "votes", "total_table_votes", "pct", "margin",
    "rival_name", "rival_votes", "winner_label", "winner_votes",
]


def _build_candidate_summary(scope_frame: pd.DataFrame, candidate_name: str, candidate_party: str) -> dict | None:
    perf = build_table_performance(scope_frame, candidate_name)
    if perf.empty:
        return None

    active = perf[perf["candidate_votes"].gt(0)]
    avg_share = float(active["candidate_share"].mean()) if not active.empty else 0.0
    total_tables = int(perf["table_id"].nunique())
    tables_with = int(active["table_id"].nunique())

    narrow_losses = perf[(~perf["is_winner"]) & perf["candidate_votes"].gt(0)].copy()
    narrow_losses = narrow_losses[narrow_losses["margin_against_best_competitor"].ge(-NARROW_LOSS_MARGIN)]

    stats = {
        "total_votes": int(perf["candidate_votes"].sum()),
        "total_tables": total_tables,
        "tables_with_votes": tables_with,
        "tables_without_votes": max(total_tables - tables_with, 0),
        "coverage_pct": (tables_with / total_tables * 100) if total_tables else 0.0,
        "avg_participation": avg_share * 100,
        "municipalities_with_votes": int(active["municipality_id"].nunique()),
        "winning_tables": int(perf["is_winner"].sum()),
        "narrow_loss_tables": int(narrow_losses["table_id"].nunique()),
        "narrow_loss_margin_threshold": NARROW_LOSS_MARGIN,
    }

    # Top zones
    zone_context = ["department_name", "municipality_name", "zone_code"]
    zone_summary = (
        perf.groupby(zone_context, as_index=False, dropna=False)
        .agg(
            candidate_votes=("candidate_votes", "sum"),
            total_votes=("total_table_votes", "sum"),
            tables=("table_id", "nunique"),
            polling_places=("polling_place_id", "nunique"),
            winning_tables=("is_winner", "sum"),
        )
    )
    zone_summary["candidate_share"] = (
        zone_summary["candidate_votes"] / zone_summary["total_votes"].replace(0, pd.NA)
    ).fillna(0.0)
    zone_summary["zone_label"] = "Zona " + zone_summary["zone_code"].astype(str).fillna("S/N")
    zone_summary = zone_summary.sort_values(["candidate_votes", "candidate_share"], ascending=[False, False])

    top_zones = zone_summary.head(TOP_ZONES_LIMIT).rename(columns={
        "candidate_votes": "votes",
        "candidate_share": "participation",
        "polling_places": "places",
    })[["department_name", "municipality_name", "zone_code", "zone_label",
        "votes", "total_votes", "participation", "tables", "places", "winning_tables"]]
    top_zones = top_zones.copy()
    top_zones["participation"] = top_zones["participation"] * 100

    # Top tables
    ranked = perf[perf["candidate_votes"].gt(0)].sort_values(["candidate_votes", "candidate_share"], ascending=[False, False])
    top_tables = ranked.head(TOP_TABLES_LIMIT).rename(columns={
        "table_id": "table_key", "candidate_votes": "votes", "candidate_share": "pct",
        "margin_against_best_competitor": "margin",
        "best_competitor_label": "rival_name", "best_competitor_votes": "rival_votes",
    })
    top_tables = top_tables.copy()
    top_tables["pct"] = top_tables["pct"] * 100
    top_tables = top_tables[DETAIL_COLUMNS]

    # Tables won
    won = perf[perf["is_winner"] & perf["candidate_votes"].gt(0)].sort_values(
        ["margin_against_best_competitor", "candidate_votes"], ascending=[False, False]
    ).head(TABLES_WON_LIMIT).rename(columns={
        "table_id": "table_key", "candidate_votes": "votes", "candidate_share": "pct",
        "margin_against_best_competitor": "margin",
        "best_competitor_label": "rival_name", "best_competitor_votes": "rival_votes",
    })
    won = won.copy()
    won["pct"] = won["pct"] * 100
    won = won[DETAIL_COLUMNS]

    # Tables lost narrow
    lost = narrow_losses.head(TABLES_LOST_LIMIT).rename(columns={
        "table_id": "table_key", "candidate_votes": "votes", "candidate_share": "pct",
        "margin_against_best_competitor": "margin",
        "best_competitor_label": "rival_name", "best_competitor_votes": "rival_votes",
    })
    lost = lost.copy()
    lost["pct"] = lost["pct"] * 100
    lost = lost[DETAIL_COLUMNS]

    return {
        "candidate": {"name": candidate_name, "party": candidate_party, "contest": DEFAULT_CONTEST},
        "scope": {"dataset": "elecciones 2026/nacional.parquet"},
        "stats": stats,
        "top_zones": records(top_zones),
        "top_tables": records(top_tables),
        "tables_won": records(won),
        "tables_lost_narrow": records(lost),
    }


# ---------------------------------------------------------------------------
# Precompute: competitive
# ---------------------------------------------------------------------------

def _build_competitive(scope_frame: pd.DataFrame, candidate_name: str, candidate_party: str) -> dict | None:
    perf = build_table_performance(scope_frame, candidate_name)
    cand_tables = perf[perf["candidate_votes"].gt(0)]
    total_candidate_tables = int(cand_tables["table_id"].nunique())

    if cand_tables.empty:
        return None

    shared = scope_frame[scope_frame["table_id"].isin(cand_tables["table_id"])]
    rival_votes_df = shared[
        shared["row_kind"].eq("candidate")
        & shared["candidate_name"].notna()
        & shared["candidate_name"].ne(candidate_name)
    ]

    if rival_votes_df.empty:
        return None

    top_rivals = (
        rival_votes_df.groupby(["candidate_name", "party_name"], dropna=False, as_index=False)
        .agg(rival_votes=("votes", "sum"))
        .sort_values(["rival_votes", "candidate_name"], ascending=[False, True])
        .head(TOP_RIVALS)
        .rename(columns={"candidate_name": "rival_name", "party_name": "rival_party"})
        .reset_index(drop=True)
    )

    context = cand_tables[
        ["table_id", "municipality_name", "zone_code", "polling_place_code",
         "polling_place_name", "table_code", "candidate_votes", "candidate_share", "total_table_votes"]
    ]

    rival_rows = []
    h2h_frames = []

    for row in top_rivals.itertuples(index=False):
        rtv = (
            rival_votes_df[rival_votes_df["candidate_name"].eq(row.rival_name)]
            .groupby("table_id", as_index=False)
            .agg(rival_votes=("votes", "sum"))
        )
        merged = context.merge(rtv, on="table_id", how="left")
        merged["rival_votes"] = merged["rival_votes"].fillna(0).astype("int64")
        merged["rival_share"] = (merged["rival_votes"] / merged["total_table_votes"].replace(0, pd.NA)).fillna(0.0)

        rival_rows.append({
            "rival_name": row.rival_name,
            "rival_party": row.rival_party if pd.notna(row.rival_party) else None,
            "rival_votes": int(row.rival_votes),
            "candidate_votes": int(merged["candidate_votes"].sum()),
            "tables_candidate_wins": int(merged["candidate_votes"].gt(merged["rival_votes"]).sum()),
            "tables_rival_wins": int(merged["rival_votes"].gt(merged["candidate_votes"]).sum()),
            "tables_tied": int(merged["rival_votes"].eq(merged["candidate_votes"]).sum()),
            "avg_rival_participation": float(merged["rival_share"].mean() * 100),
            "avg_candidate_participation": float(merged["candidate_share"].mean() * 100),
        })

        scatter = merged.copy()
        scatter["table_key"] = scatter["table_id"]
        scatter["candidate_pct"] = scatter["candidate_share"] * 100
        scatter["rival_pct"] = scatter["rival_share"] * 100
        scatter["rival_name"] = row.rival_name
        scatter["vote_difference"] = scatter["candidate_votes"] - scatter["rival_votes"]
        scatter["winner_name"] = row.rival_name
        scatter.loc[scatter["candidate_votes"].gt(scatter["rival_votes"]), "winner_name"] = candidate_name
        scatter.loc[scatter["candidate_votes"].eq(scatter["rival_votes"]), "winner_name"] = "Empate"
        scatter = scatter.sort_values(["vote_difference", "candidate_votes", "rival_votes"], ascending=[True, False, False]).head(HEAD_TO_HEAD_LIMIT)
        h2h_frames.append(scatter[
            ["table_key", "municipality_name", "zone_code", "polling_place_code",
             "polling_place_name", "table_code", "candidate_votes", "rival_votes",
             "vote_difference", "winner_name", "candidate_pct", "rival_pct", "rival_name"]
        ])

    h2h = pd.concat(h2h_frames, ignore_index=True) if h2h_frames else pd.DataFrame()

    return {
        "candidate": {"name": candidate_name, "party": candidate_party, "contest": DEFAULT_CONTEST},
        "scope": {"dataset": "elecciones 2026/nacional.parquet"},
        "total_candidate_tables": total_candidate_tables,
        "rivals": rival_rows,
        "head_to_head": records(h2h),
    }


# ---------------------------------------------------------------------------
# Precompute: municipal comparison
# ---------------------------------------------------------------------------

MUNICIPALITY_CONTEXT = ["municipality_id", "department_name", "municipality_name"]


def _build_municipal(scope_frame: pd.DataFrame, candidate_name: str, candidate_party: str) -> dict | None:
    muni_scope = (
        scope_frame.groupby(MUNICIPALITY_CONTEXT, as_index=False)
        .agg(total_tables=("table_id", "nunique"))
    )
    cand_rows = scope_frame[scope_frame["candidate_name"].eq(candidate_name)]
    if cand_rows.empty:
        return None

    cand_summary = (
        cand_rows.groupby(MUNICIPALITY_CONTEXT, as_index=False)
        .agg(total_votes=("votes", "sum"), tables_with_votes=("table_id", "nunique"))
    )

    muni_votes = (
        scope_frame[scope_frame["row_kind"].eq("candidate")]
        .groupby(MUNICIPALITY_CONTEXT + ["candidate_name"], as_index=False)
        .agg(candidate_votes=("votes", "sum"))
    )
    muni_votes = muni_votes.sort_values(
        ["municipality_id", "candidate_votes", "candidate_name"], ascending=[True, False, True]
    )
    muni_votes["rank_in_department"] = (
        muni_votes.groupby("municipality_id")["candidate_votes"]
        .rank(method="dense", ascending=False).astype(int)
    )
    cand_rank = muni_votes[muni_votes["candidate_name"].eq(candidate_name)][["municipality_id", "rank_in_department"]]

    rivals = muni_votes[muni_votes["candidate_name"].ne(candidate_name)]
    top_rivals = (
        rivals.groupby("municipality_id", as_index=False)
        .first()[["municipality_id", "candidate_name", "candidate_votes"]]
        .rename(columns={"candidate_name": "top_rival_name", "candidate_votes": "top_rival_votes"})
    )

    comp = (
        muni_scope.merge(cand_summary, on=MUNICIPALITY_CONTEXT, how="left")
        .merge(cand_rank, on="municipality_id", how="left")
        .merge(top_rivals, on="municipality_id", how="left")
    )
    comp["total_votes"] = comp["total_votes"].fillna(0).astype("int64")
    comp["tables_with_votes"] = comp["tables_with_votes"].fillna(0).astype("int64")
    comp["rank_in_department"] = comp["rank_in_department"].fillna(0).astype("int64")
    comp["top_rival_votes"] = comp["top_rival_votes"].fillna(0).astype("int64")
    comp["coverage_pct"] = (comp["tables_with_votes"] / comp["total_tables"].replace(0, pd.NA) * 100).fillna(0.0)
    comp["efficiency"] = (comp["total_votes"] / comp["tables_with_votes"].replace(0, pd.NA)).fillna(0.0)

    active = comp[comp["total_votes"].gt(0)].sort_values(
        ["total_votes", "efficiency", "coverage_pct"], ascending=[False, False, False]
    ).head(MUNICIPAL_LIMIT)

    best = None
    if not active.empty:
        br = active.sort_values(["total_votes", "efficiency"], ascending=[False, False]).iloc[0]
        best = {"municipality_name": br["municipality_name"], "department_name": br["department_name"], "value": int(br["total_votes"])}

    most_efficient = None
    if not active.empty:
        er = active.sort_values(["efficiency", "total_votes"], ascending=[False, False]).iloc[0]
        most_efficient = {"municipality_name": er["municipality_name"], "department_name": er["department_name"], "value": float(er["efficiency"])}

    summary = {
        "total_municipalities": int(comp["total_votes"].gt(0).sum()),
        "total_municipalities_available": int(comp["municipality_id"].nunique()),
        "best_municipality": best,
        "most_efficient_municipality": most_efficient,
    }

    result_cols = ["municipality_name", "department_name", "total_votes", "total_tables",
                   "tables_with_votes", "coverage_pct", "efficiency", "rank_in_department",
                   "top_rival_name", "top_rival_votes"]

    return {
        "candidate": {"name": candidate_name, "party": candidate_party, "contest": DEFAULT_CONTEST},
        "scope": {"dataset": "elecciones 2026/nacional.parquet"},
        "summary": summary,
        "municipalities": records(active[result_cols].reset_index(drop=True)),
    }


# ---------------------------------------------------------------------------
# Precompute: drilldown (zones → places → tables)
# ---------------------------------------------------------------------------

ZONE_CONTEXT = ["department_name", "municipality_name", "zone_code"]
PLACE_CONTEXT = ["polling_place_id", "department_name", "municipality_name", "zone_code", "polling_place_code", "polling_place_name"]


def _build_zone_drilldown(scope_frame: pd.DataFrame, candidate_name: str) -> list[dict]:
    perf = build_table_performance(scope_frame, candidate_name)
    if perf.empty:
        return []

    zone_summary = (
        perf.groupby(ZONE_CONTEXT, as_index=False, dropna=False)
        .agg(
            candidate_votes=("candidate_votes", "sum"),
            total_votes=("total_table_votes", "sum"),
            tables_total=("table_id", "nunique"),
            tables_with_votes=("candidate_votes", lambda v: int(v.gt(0).sum())),
            places_count=("polling_place_id", "nunique"),
        )
    )
    zone_summary["candidate_pct"] = (
        zone_summary["candidate_votes"] / zone_summary["total_votes"].replace(0, pd.NA) * 100
    ).fillna(0.0)

    _, winners, cand_rank, _ = _ballot_rankings(scope_frame, ZONE_CONTEXT, candidate_name)
    zone_summary = (
        zone_summary.merge(cand_rank, on=ZONE_CONTEXT, how="left")
        .merge(winners, on=ZONE_CONTEXT, how="left")
        .rename(columns={"winner_label": "zone_winner", "winner_votes": "zone_winner_votes"})
    )
    zone_summary["rank_in_zone"] = zone_summary["candidate_rank"].fillna(0).astype("int64")
    zone_summary["zone_winner_votes"] = zone_summary["zone_winner_votes"].fillna(0).astype("int64")

    result = zone_summary[[
        "zone_code", "candidate_votes", "total_votes", "candidate_pct",
        "tables_total", "tables_with_votes", "places_count",
        "rank_in_zone", "zone_winner", "zone_winner_votes",
    ]].sort_values(["candidate_votes", "candidate_pct", "zone_code"], ascending=[False, False, True])

    return records(result.reset_index(drop=True))


def _build_place_drilldown(zone_frame: pd.DataFrame, candidate_name: str) -> list[dict]:
    perf = build_table_performance(zone_frame, candidate_name)
    if perf.empty:
        return []

    places = (
        perf.groupby(PLACE_CONTEXT, as_index=False, dropna=False)
        .agg(
            candidate_votes=("candidate_votes", "sum"),
            total_votes=("total_table_votes", "sum"),
            tables_total=("table_id", "nunique"),
            tables_with_votes=("candidate_votes", lambda v: int(v.gt(0).sum())),
        )
    )
    places["candidate_pct"] = (places["candidate_votes"] / places["total_votes"].replace(0, pd.NA) * 100).fillna(0.0)

    _, winners, cand_rank, _ = _ballot_rankings(zone_frame, PLACE_CONTEXT, candidate_name)
    places = (
        places.merge(cand_rank, on=PLACE_CONTEXT, how="left")
        .merge(winners, on=PLACE_CONTEXT, how="left")
        .rename(columns={"winner_label": "place_winner", "winner_votes": "place_winner_votes"})
    )
    places["rank_in_place"] = places["candidate_rank"].fillna(0).astype("int64")
    places["place_winner_votes"] = places["place_winner_votes"].fillna(0).astype("int64")

    result = places[[
        "polling_place_code", "polling_place_name",
        "candidate_votes", "total_votes", "candidate_pct",
        "tables_total", "tables_with_votes",
        "rank_in_place", "place_winner", "place_winner_votes",
    ]].sort_values(["candidate_votes", "candidate_pct", "polling_place_name"], ascending=[False, False, True])

    return records(result.reset_index(drop=True))


def _build_table_drilldown(place_frame: pd.DataFrame, candidate_name: str) -> list[dict]:
    perf = build_table_performance(place_frame, candidate_name)
    if perf.empty:
        return []

    ballot_votes, _, cand_rank, second = _ballot_rankings(place_frame, ["table_id"], candidate_name)

    rivals = ballot_votes[ballot_votes["ballot_label"].ne(candidate_name)]
    total_map = perf.set_index("table_id")["total_table_votes"].to_dict()
    top_rivals: dict[str, list] = {}
    for tid, grp in rivals.groupby("table_id", dropna=False):
        items = []
        ttv = float(total_map.get(tid, 0) or 0)
        for r in grp.head(5).itertuples(index=False):
            pct = (float(r.ballot_votes) / ttv * 100) if ttv else 0.0
            items.append({"name": r.ballot_label, "votes": int(r.ballot_votes), "pct": round(pct, 4)})
        top_rivals[str(tid)] = items

    tables = perf.merge(cand_rank, on="table_id", how="left").merge(second, on="table_id", how="left")
    tables["candidate_pct"] = tables["candidate_share"] * 100
    tables["rank_in_table"] = tables["candidate_rank"].fillna(0).astype("int64")
    tables["second_votes"] = tables["second_votes"].fillna(0).astype("int64")
    tables["margin_vs_second"] = (tables["winner_votes"] - tables["second_votes"]).astype("int64")
    tables["top_rivals"] = tables["table_id"].map(lambda v: top_rivals.get(str(v), []))
    tables = tables.rename(columns={
        "total_table_votes": "total_votes",
        "winner_label": "table_winner",
        "winner_votes": "table_winner_votes",
    })

    result = tables[[
        "table_code", "candidate_votes", "total_votes", "candidate_pct",
        "rank_in_table", "table_winner", "table_winner_votes",
        "margin_vs_second", "top_rivals",
    ]].sort_values(["candidate_votes", "candidate_pct", "table_code"], ascending=[False, False, True])

    return records(result.reset_index(drop=True))


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pre-compute JSON files from parquet")
    parser.add_argument("--candidate", default=DEFAULT_CANDIDATE)
    parser.add_argument("--parquet", default=str(DEFAULT_PARQUET))
    args = parser.parse_args()

    candidate_name = args.candidate
    parquet_path = Path(args.parquet)

    if not parquet_path.exists():
        print(f"ERROR: Parquet not found: {parquet_path}")
        sys.exit(1)

    t0 = time.time()
    print(f"Candidate: {candidate_name}")
    print(f"Parquet:   {parquet_path}")
    print(f"Output:    {OUTPUT_DIR}")
    print()

    # 1. datasets.json
    print("[1/6] datasets.json ...")
    precompute_datasets(parquet_path)
    print("  done")

    # 2. Load contest data
    print("[2/6] Loading parquet for contest={DEFAULT_CONTEST}...")
    df_raw = pd.read_parquet(parquet_path, filters=[("contest_name", "==", DEFAULT_CONTEST)])
    df = enrich(df_raw)
    print(f"  {len(df):,} rows loaded")

    # Resolve candidate party
    cand_opts = df[df["row_kind"].eq("candidate") & df["candidate_name"].eq(candidate_name)]
    if cand_opts.empty:
        print(f"ERROR: Candidate '{candidate_name}' not found in data")
        sys.exit(1)
    candidate_party = str(cand_opts["party_name"].iloc[0])
    print(f"  Party: {candidate_party}")

    # 3. Filters
    print("[3/6] filters/ ...")
    # Need full parquet for contest list
    all_contests = pd.read_parquet(parquet_path, columns=["contest_name"])["contest_name"].dropna().unique().tolist()
    # But use contest-filtered df for the rest
    precompute_filters(df)
    # Patch the global filters to include all contests
    global_filter_path = OUTPUT_DIR / "filters" / "all.json"
    gf = json.loads(global_filter_path.read_text())
    gf["contests"] = sorted(all_contests)
    write_json(global_filter_path, gf)
    print("  done")

    # Get unique departments + municipalities
    departments = sorted(df["department_name"].dropna().unique().tolist())

    # 4. Per-department processing
    print(f"[4/6] Processing {len(departments)} departments ...")
    file_count = 0

    for dept in departments:
        dept_key = sanitize(dept)
        dept_df = df[df["department_name"].eq(dept)]
        municipalities = sorted(dept_df["municipality_name"].dropna().unique().tolist())

        # Department-level candidate summary
        dept_summary = _build_candidate_summary(dept_df, candidate_name, candidate_party)
        if dept_summary:
            dept_summary["scope"]["department"] = dept
            write_json(OUTPUT_DIR / "candidate" / dept_key / "_summary.json", dept_summary)
            file_count += 1

        # Department-level competitive
        dept_competitive = _build_competitive(dept_df, candidate_name, candidate_party)
        if dept_competitive:
            dept_competitive["scope"]["department"] = dept
            write_json(OUTPUT_DIR / "competitive" / dept_key / "_rivals.json", dept_competitive)
            file_count += 1

        # Department-level municipal
        dept_municipal = _build_municipal(dept_df, candidate_name, candidate_party)
        if dept_municipal:
            dept_municipal["scope"]["department"] = dept
            write_json(OUTPUT_DIR / "municipal" / f"{dept_key}.json", dept_municipal)
            file_count += 1

        for muni in municipalities:
            muni_key = sanitize(muni)
            muni_df = dept_df[dept_df["municipality_name"].eq(muni)]

            # Candidate summary per municipality
            muni_summary = _build_candidate_summary(muni_df, candidate_name, candidate_party)
            if muni_summary:
                muni_summary["scope"]["department"] = dept
                muni_summary["scope"]["municipality"] = muni
                write_json(OUTPUT_DIR / "candidate" / dept_key / f"{muni_key}.json", muni_summary)
                file_count += 1

            # Competitive per municipality
            muni_competitive = _build_competitive(muni_df, candidate_name, candidate_party)
            if muni_competitive:
                muni_competitive["scope"]["department"] = dept
                muni_competitive["scope"]["municipality"] = muni
                write_json(OUTPUT_DIR / "competitive" / dept_key / f"{muni_key}.json", muni_competitive)
                file_count += 1

            # Drilldown: zones
            zone_items = _build_zone_drilldown(muni_df, candidate_name)
            first_muni_name = muni
            write_json(OUTPUT_DIR / "drilldown" / dept_key / muni_key / "zones.json", {
                "level": "zone",
                "context": {"municipality": first_muni_name},
                "items": zone_items,
            })
            file_count += 1

            # Drilldown: places per zone
            zones = sorted(muni_df["zone_code"].dropna().unique().tolist(), key=str)
            for zc in zones:
                zc_str = str(zc)
                zone_key = sanitize(f"ZONE_{zc_str}")
                zone_df = muni_df[muni_df["zone_code"].astype(str).eq(zc_str)]

                place_items = _build_place_drilldown(zone_df, candidate_name)
                write_json(OUTPUT_DIR / "drilldown" / dept_key / muni_key / zone_key / "places.json", {
                    "level": "polling_place",
                    "context": {"municipality": first_muni_name, "zone_code": zc_str},
                    "items": place_items,
                })
                file_count += 1

                # Drilldown: tables per place
                place_codes = sorted(zone_df["polling_place_code"].dropna().unique().tolist(), key=str)
                for pc in place_codes:
                    pc_str = str(pc)
                    place_key = sanitize(f"PLACE_{pc_str}")
                    place_df = zone_df[zone_df["polling_place_code"].astype(str).eq(pc_str)]
                    place_name = place_df["polling_place_name"].iloc[0] if not place_df.empty else None

                    table_items = _build_table_drilldown(place_df, candidate_name)
                    write_json(OUTPUT_DIR / "drilldown" / dept_key / muni_key / zone_key / f"{place_key}.json", {
                        "level": "table",
                        "context": {
                            "municipality": first_muni_name,
                            "zone_code": zc_str,
                            "polling_place_code": pc_str,
                            "polling_place_name": str(place_name) if place_name else None,
                        },
                        "items": table_items,
                    })
                    file_count += 1

        print(f"  {dept}: {len(municipalities)} municipalities")

    # 5. National-level candidate summary (all departments)
    print("[5/6] National summary ...")
    national = _build_candidate_summary(df, candidate_name, candidate_party)
    if national:
        write_json(OUTPUT_DIR / "candidate" / "_national.json", national)
        file_count += 1

    national_competitive = _build_competitive(df, candidate_name, candidate_party)
    if national_competitive:
        write_json(OUTPUT_DIR / "competitive" / "_national.json", national_competitive)
        file_count += 1

    national_municipal = _build_municipal(df, candidate_name, candidate_party)
    if national_municipal:
        write_json(OUTPUT_DIR / "municipal" / "_national.json", national_municipal)
        file_count += 1

    print("  done")

    print(f"\n[6/6] Summary")
    elapsed = time.time() - t0
    print(f"  Files written: {file_count}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
