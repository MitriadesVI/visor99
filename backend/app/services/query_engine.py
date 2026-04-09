"""DuckDB query engine – reads parquet/CSV from disk without bulk RAM loading."""
from __future__ import annotations

import duckdb
import pandas as pd


# ---------------------------------------------------------------------------
# SQL helpers for the enrichment columns that analytics expects
# ---------------------------------------------------------------------------

def _compound_key(columns: list[str]) -> str:
    parts = [f"COALESCE(CAST({c} AS VARCHAR), 'NA')" for c in columns]
    return " || '|' || ".join(parts)


_TABLE_KEY = _compound_key(
    ["department_code", "municipality_code", "zone_code", "polling_place_code", "table_code"]
)
_PLACE_KEY = _compound_key(
    ["department_code", "municipality_code", "zone_code", "polling_place_code"]
)
_MUNICIPALITY_KEY = _compound_key(["department_code", "municipality_code"])

_ENRICHMENT = f""",
    {_TABLE_KEY} AS table_id,
    {_PLACE_KEY} AS polling_place_id,
    {_MUNICIPALITY_KEY} AS municipality_id,
    CASE WHEN COALESCE(CAST(candidate_code AS VARCHAR), '0') = '0'
         THEN 'list' ELSE 'candidate' END AS row_kind,
    CASE
      WHEN COALESCE(CAST(candidate_code AS VARCHAR), '0') != '0'
      THEN COALESCE(
             NULLIF(TRIM(CAST(candidate_name AS VARCHAR)), ''),
             NULLIF(TRIM(CAST(party_name AS VARCHAR)), ''),
             'SIN_ETIQUETA')
      ELSE COALESCE(
             NULLIF(TRIM(CAST(party_name AS VARCHAR)), ''),
             NULLIF(TRIM(CAST(candidate_name AS VARCHAR)), ''),
             'SIN_ETIQUETA')
    END AS ballot_label
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _scope_where(
    contest: str | None,
    department: str | None,
    municipality: str | None,
    party: str | None,
) -> tuple[str, list[str]]:
    """Build a WHERE clause + parameter list from scope filters."""
    clauses: list[str] = []
    params: list[str] = []
    if contest:
        clauses.append("contest_name = ?")
        params.append(contest)
    if department and department != "Todos":
        clauses.append("department_name = ?")
        params.append(department)
    if municipality and municipality != "Todos":
        clauses.append("municipality_name = ?")
        params.append(municipality)
    if party and party != "Todos":
        clauses.append("party_name = ?")
        params.append(party)
    return (" AND ".join(clauses) or "TRUE"), params


def _distinct(
    con: duckdb.DuckDBPyConnection,
    source: str,
    column: str,
    where: list[str],
    params: list[str] | None = None,
) -> list[str]:
    w = " AND ".join(where) if where else "TRUE"
    sql = (
        f"SELECT DISTINCT {column} FROM ({source}) "
        f"WHERE {w} AND {column} IS NOT NULL "
        f"AND TRIM(CAST({column} AS VARCHAR)) != '' "
        f"ORDER BY {column}"
    )
    return con.execute(sql, params or []).fetchdf()[column].tolist()


def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure column dtypes match what the pandas analytics layer expects."""
    if df.empty:
        return df
    if "votes" in df.columns:
        df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype("Int64")
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype("string")
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def query_scope(
    source_sql: str,
    contest: str | None = None,
    department: str | None = None,
    municipality: str | None = None,
    party: str | None = None,
) -> pd.DataFrame:
    """Run *source_sql* through DuckDB adding enrichment columns and scope
    filters, returning a pandas DataFrame ready for the analytics layer."""
    where, params = _scope_where(contest, department, municipality, party)
    sql = f"SELECT src.* {_ENRICHMENT} FROM ({source_sql}) AS src WHERE {where}"
    con = duckdb.connect()
    try:
        df = con.execute(sql, params).fetchdf()
    finally:
        con.close()
    return _coerce(df)


def query_filter_options(
    source_sql: str,
    contest: str | None = None,
    department: str | None = None,
    municipality: str | None = None,
    party: str | None = None,
) -> dict[str, list[str]]:
    """Return cascading filter-option lists using lightweight DISTINCT queries."""
    con = duckdb.connect()
    try:
        # All contests (unfiltered)
        contests = _distinct(con, source_sql, "contest_name", [])

        # Departments – filtered by contest
        dept_w: list[str] = []
        dept_p: list[str] = []
        if contest:
            dept_w.append("contest_name = ?")
            dept_p.append(contest)
        departments = _distinct(con, source_sql, "department_name", dept_w, dept_p)

        # Municipalities – filtered by contest + department
        mun_w, mun_p = list(dept_w), list(dept_p)
        if department and department != "Todos":
            mun_w.append("department_name = ?")
            mun_p.append(department)
        municipalities = _distinct(con, source_sql, "municipality_name", mun_w, mun_p)

        # Parties – filtered by contest + department + municipality
        pty_w, pty_p = list(mun_w), list(mun_p)
        if municipality and municipality != "Todos":
            pty_w.append("municipality_name = ?")
            pty_p.append(municipality)
        parties = _distinct(con, source_sql, "party_name", pty_w, pty_p)

        # Candidates – filtered by all above + party, ordered by total votes desc
        cand_w, cand_p = list(pty_w), list(pty_p)
        if party and party != "Todos":
            cand_w.append("party_name = ?")
            cand_p.append(party)
        cand_w.append("COALESCE(CAST(candidate_code AS VARCHAR), '0') != '0'")
        cand_where = " AND ".join(cand_w)
        cand_sql = (
            f"SELECT candidate_name, SUM(CAST(votes AS BIGINT)) AS total "
            f"FROM ({source_sql}) "
            f"WHERE {cand_where} AND candidate_name IS NOT NULL "
            f"AND TRIM(CAST(candidate_name AS VARCHAR)) != '' "
            f"GROUP BY candidate_name "
            f"ORDER BY total DESC, candidate_name"
        )
        candidates = con.execute(cand_sql, cand_p).fetchdf()["candidate_name"].tolist()
    finally:
        con.close()

    return {
        "contests": contests,
        "departments": departments,
        "municipalities": municipalities,
        "parties": parties,
        "candidates": candidates,
    }
