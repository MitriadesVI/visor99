from __future__ import annotations

import sys
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.analytics.electoral import (
    apply_scope_filters,
    build_candidate_table_performance,
    candidate_vote_options,
    rank_municipalities,
    rank_polling_places,
    rank_tables,
    summarize_candidate_scope,
    tables_lost_by_close_margin,
    tables_won,
)
from app.config import APP_SETTINGS
from app.services.catalog import discover_datasets, get_dataset_spec
from app.services.loader import build_download_name, load_dataset_bundle
from app.ui.components import build_bar_chart, build_share_chart, render_chart
from app.ui.formatters import format_int, format_pct


st.set_page_config(
    page_title="Visor 99",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Cargando dataset...")
def cached_load_dataset(dataset_id: str):
    spec = get_dataset_spec(dataset_id)
    return load_dataset_bundle(spec)


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


def build_polling_place_catalog(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["polling_place_id", "zone_code", "polling_place_name", "label"])

    catalog = (
        frame[["polling_place_id", "zone_code", "polling_place_name"]]
        .dropna(subset=["polling_place_id"])
        .drop_duplicates(subset=["polling_place_id"])
        .sort_values(["zone_code", "polling_place_name"], ascending=[True, True])
        .copy()
    )
    catalog["label"] = (
        "Zona "
        + catalog["zone_code"].astype("string").fillna("S/N")
        + " · "
        + catalog["polling_place_name"].astype("string").fillna("Sin nombre")
    )
    return catalog


def build_table_catalog(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=["table_id", "zone_code", "polling_place_name", "table_code", "label"]
        )

    catalog = (
        frame[["table_id", "zone_code", "polling_place_name", "table_code"]]
        .dropna(subset=["table_id"])
        .drop_duplicates(subset=["table_id"])
        .sort_values(["zone_code", "polling_place_name", "table_code"], ascending=[True, True, True])
        .copy()
    )
    catalog["label"] = (
        "Zona "
        + catalog["zone_code"].astype("string").fillna("S/N")
        + " · "
        + catalog["polling_place_name"].astype("string").fillna("Sin nombre")
        + " · Mesa "
        + catalog["table_code"].astype("string").fillna("S/N")
    )
    return catalog


def build_table_candidate_breakdown(frame: pd.DataFrame) -> pd.DataFrame:
    candidates = frame[frame["row_kind"].eq("candidate")].copy()
    if candidates.empty:
        return pd.DataFrame(columns=["candidate_name", "candidate_votes", "candidate_share"])

    breakdown = (
        candidates.groupby("candidate_name", as_index=False)
        .agg(candidate_votes=("votes", "sum"))
        .sort_values(["candidate_votes", "candidate_name"], ascending=[False, True])
        .reset_index(drop=True)
    )
    total_votes = float(breakdown["candidate_votes"].sum())
    breakdown["candidate_share"] = (
        breakdown["candidate_votes"].astype("float64") / total_votes if total_votes else 0.0
    )
    return breakdown


def render_top_territory_cards(
    frame: pd.DataFrame,
    title: str,
    name_column: str,
    empty_message: str,
) -> None:
    if frame.empty:
        st.info(empty_message)
        return

    top_items = frame.sort_values(
        ["candidate_votes", "candidate_share"],
        ascending=[False, False],
    ).head(4)

    st.markdown(f"### {title}")
    cols = st.columns(len(top_items), gap="small")
    for column, (_, row) in zip(cols, top_items.iterrows()):
        share_pct = float(row.get("candidate_share", 0.0)) * 100
        label = str(row.get(name_column, "Sin etiqueta"))
        subtitle_parts: list[str] = []
        if "tables" in row and pd.notna(row["tables"]):
            subtitle_parts.append(f"{int(row['tables']):,} mesas".replace(",", "."))
        if "polling_places" in row and pd.notna(row["polling_places"]):
            subtitle_parts.append(f"{int(row['polling_places']):,} puestos".replace(",", "."))

        with column:
            st.markdown(
                f"""
<div class="territory-card">
    <div class="territory-card__label">{escape(label)}</div>
    <div class="territory-card__value">{format_int(row['candidate_votes'])} votos</div>
    <div class="territory-card__meta">Participacion: {share_pct:.1f}%</div>
    <div class="territory-card__sub">{' · '.join(subtitle_parts) if subtitle_parts else '&nbsp;'}</div>
</div>
""",
                unsafe_allow_html=True,
            )


def build_coverage_frame(summary: dict[str, float | int], total_tables: int) -> pd.DataFrame:
    tables_with_votes = int(summary["tables_with_votes"])
    winning_tables = int(summary["winning_tables"])
    tables_without_votes = max(total_tables - tables_with_votes, 0)
    return pd.DataFrame(
        {
            "segment": ["Mesas con votos", "Mesas ganadas", "Mesas sin votos"],
            "tables": [tables_with_votes, winning_tables, tables_without_votes],
        }
    ).sort_values("tables", ascending=False)


def main() -> None:
    st.markdown(
        """
<style>
    .stApp { background-color: #f8f9fb; }
    .block-container {
        padding-top: 0.75rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    [data-testid="stHorizontalBlock"] { gap: 0.75rem; align-items: stretch; }
    div[data-testid="stVerticalBlock"] { gap: 0.55rem; }
    hr { margin: 0.8rem 0 1rem 0; }

    [data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
        border: 1px solid #dbe4f0;
        border-radius: 14px;
        padding: 14px 18px;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.65rem !important;
        font-weight: 700 !important;
        color: #1a1a2e !important;
    }
    [data-testid="stMetric"] svg { color: #335caa !important; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #eef0f4;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 600;
    }

    [data-testid="stSidebar"] { background-color: #f1f3f8; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #374151;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    h1 { color: #1a1a2e !important; font-weight: 800 !important; margin-bottom: 0.15rem !important; }
    h3 { color: #2d3748 !important; border-bottom: 2px solid #e2e6ed; padding-bottom: 6px; margin-bottom: 0.35rem !important; }
    p { margin-bottom: 0.3rem; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }

    .summary-shell {
        background: linear-gradient(135deg, #f9fbff 0%, #f1f5ff 100%);
        border: 1px solid #dbe4f0;
        border-radius: 16px;
        padding: 14px 16px 10px 16px;
        margin: 0.2rem 0 0.7rem 0;
    }
    .summary-shell__eyebrow {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #335caa;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .summary-shell__title {
        font-size: 1.2rem;
        font-weight: 800;
        color: #122033;
        margin-bottom: 0.1rem;
    }
    .summary-shell__text {
        font-size: 0.9rem;
        color: #4b5563;
    }
    .territory-card {
        background: #ffffff;
        border: 1px solid #dbe4f0;
        border-radius: 14px;
        padding: 16px 16px 14px 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        min-height: 124px;
    }
    .territory-card__label {
        font-size: 0.78rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.45rem;
        font-weight: 700;
    }
    .territory-card__value {
        font-size: 1.3rem;
        font-weight: 800;
        color: #172033;
        margin-bottom: 0.3rem;
    }
    .territory-card__meta {
        font-size: 0.88rem;
        color: #335caa;
        font-weight: 700;
        margin-bottom: 0.28rem;
    }
    .territory-card__sub {
        font-size: 0.82rem;
        color: #6b7280;
    }
    @media (max-width: 900px) {
        .block-container {
            padding-left: 0.7rem;
            padding-right: 0.7rem;
            padding-top: 0.45rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.35rem !important;
        }
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
            gap: 0.55rem;
        }
        .summary-shell {
            padding: 12px 12px 8px 12px;
            border-radius: 14px;
        }
        .territory-card {
            min-height: auto;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 12px;
            font-size: 0.88rem;
        }
    }
</style>
""",
        unsafe_allow_html=True,
    )

    st.title("Visor 99")
    st.caption(
        "Tablero territorial para seguimiento del senador: municipio, zona, puesto y mesa desde un mismo flujo de analisis."
    )

    specs = discover_datasets()
    if not specs:
        st.error("No se encontraron datasets CSV en la carpeta datos/.")
        return

    default_dataset_index = next(
        (
            index
            for index, spec in enumerate(specs)
            if spec.display_name == APP_SETTINGS.default_dataset_filename
        ),
        0,
    )

    selected_spec = st.sidebar.selectbox(
        "Dataset disponible",
        options=specs,
        index=default_dataset_index,
        format_func=lambda spec: spec.display_name,
    )

    bundle = cached_load_dataset(selected_spec.dataset_id)

    st.sidebar.markdown("### Alcance")
    contest_options = list(bundle.profile.available_contests)
    default_contest_index = (
        contest_options.index(APP_SETTINGS.default_contest_name)
        if APP_SETTINGS.default_contest_name in contest_options
        else 0
    )
    selected_contest = st.sidebar.selectbox(
        "Concurso",
        options=contest_options,
        index=default_contest_index,
    )

    contest_frame = apply_scope_filters(bundle.data, contest_name=selected_contest)

    department_options = ["Todos"] + sorted(
        contest_frame["department_name"].dropna().astype("string").unique().tolist()
    )
    selected_department = st.sidebar.selectbox("Departamento", options=department_options)

    municipality_source = apply_scope_filters(
        contest_frame,
        department_name=selected_department,
    )
    municipality_options = ["Todos"] + sorted(
        municipality_source["municipality_name"]
        .dropna()
        .astype("string")
        .unique()
        .tolist()
    )

    st.sidebar.markdown("### ⚡ Atajos")
    if st.sidebar.button("📍 BARRANQUILLA", use_container_width=True):
        st.session_state["selected_municipality"] = "BARRANQUILLA"
        st.rerun()
    if st.sidebar.button("📍 SOLEDAD", use_container_width=True):
        st.session_state["selected_municipality"] = "SOLEDAD"
        st.rerun()
    if st.sidebar.button("📍 MALAMBO", use_container_width=True):
        st.session_state["selected_municipality"] = "MALAMBO"
        st.rerun()

    municipality_search = st.sidebar.text_input(
        "Buscar municipio",
        key="municipality_search",
        placeholder="Escriba para filtrar...",
    )

    matched_municipalities = municipality_options[1:]
    if municipality_search.strip():
        search_upper = municipality_search.strip().upper()
        matched_municipalities = [
            municipality
            for municipality in municipality_options[1:]
            if search_upper in municipality.upper()
        ]
        exact_match = next(
            (
                municipality
                for municipality in municipality_options[1:]
                if municipality.upper() == search_upper
            ),
            None,
        )
        if exact_match and st.session_state.get("selected_municipality") != exact_match:
            st.session_state["selected_municipality"] = exact_match
            st.rerun()
        if len(matched_municipalities) == 1 and (
            st.session_state.get("selected_municipality") != matched_municipalities[0]
        ):
            st.session_state["selected_municipality"] = matched_municipalities[0]
            st.rerun()
        filtered_municipalities = ["Todos"] + matched_municipalities
    else:
        filtered_municipalities = municipality_options

    if "selected_municipality" not in st.session_state:
        st.session_state["selected_municipality"] = "Todos"

    if municipality_search.strip():
        if matched_municipalities:
            st.sidebar.caption(f"{len(matched_municipalities)} coincidencias encontradas.")
        else:
            st.sidebar.caption("Sin coincidencias. Ajusta el texto de busqueda.")

    current_municipality = st.session_state.get("selected_municipality", "Todos")
    if current_municipality in filtered_municipalities:
        default_municipality_index = filtered_municipalities.index(current_municipality)
    else:
        default_municipality_index = 0

    selected_municipality = st.sidebar.selectbox(
        "Municipio",
        options=filtered_municipalities,
        index=default_municipality_index,
        key="selected_municipality",
    )

    party_source = apply_scope_filters(
        contest_frame,
        department_name=selected_department,
        municipality_name=selected_municipality,
    )
    party_options = ["Todos"] + sorted(
        party_source["party_name"].dropna().astype("string").unique().tolist()
    )
    selected_party = st.sidebar.selectbox("Partido / lista", options=party_options)

    analysis_frame = apply_scope_filters(
        contest_frame,
        department_name=selected_department,
        municipality_name=selected_municipality,
    )
    candidate_source = apply_scope_filters(
        analysis_frame,
        party_name=selected_party,
    )

    candidate_options = candidate_vote_options(candidate_source)
    if candidate_options.empty:
        st.warning("No hay candidatos disponibles con los filtros seleccionados.")
        return

    candidate_names = candidate_options["candidate_name"].astype("string").tolist()
    default_candidate_name = APP_SETTINGS.default_candidate_name
    default_candidate_index = (
        candidate_names.index(default_candidate_name)
        if default_candidate_name in candidate_names
        else 0
    )

    selected_candidate = st.sidebar.selectbox(
        "Candidato",
        options=candidate_names,
        index=default_candidate_index,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Comparacion")
    comparison_placeholder = "Sin comparacion"
    compare_candidates = [comparison_placeholder] + [
        candidate_name
        for candidate_name in candidate_names
        if candidate_name != selected_candidate
    ]
    compare_selection = st.sidebar.selectbox(
        "Comparar con",
        options=compare_candidates,
    )

    selected_candidate_row = candidate_options[
        candidate_options["candidate_name"].eq(selected_candidate)
    ].iloc[0]
    selected_candidate_party = selected_candidate_row["party_name"]
    if pd.isna(selected_candidate_party) or not str(selected_candidate_party).strip():
        selected_candidate_party = "Sin partido/lista"

    territory_label = (
        selected_municipality if selected_municipality != "Todos" else "Cobertura general"
    )
    territory_summary_title = (
        "Lectura general del departamento"
        if selected_municipality == "Todos"
        else f"Operacion focalizada en {selected_municipality}"
    )
    st.markdown(
        f"""
<div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white; padding: 22px 28px; border-radius: 16px; margin-bottom: 10px; box-shadow: 0 18px 40px rgba(15,23,42,0.18);">
    <h2 style="margin:0; color:white; border:none; font-size:1.5rem;">{escape(str(selected_candidate))}</h2>
    <p style="margin:4px 0 0; opacity:0.86; font-size:0.92rem;">
        {escape(str(selected_candidate_party))} · {escape(str(selected_contest))} · {escape(str(territory_label))}
    </p>
    <p style="margin:2px 0 0; opacity:0.62; font-size:0.82rem;">
        Dataset: {escape(bundle.spec.display_name)}
    </p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
<div class="summary-shell">
    <div class="summary-shell__eyebrow">Resumen ejecutivo</div>
    <div class="summary-shell__title">{escape(territory_summary_title)}</div>
    <div class="summary-shell__text">Primero mira votos y participacion; despues baja a municipio, zona, puesto o mesa para tomar decisiones de operacion del senador.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    analysis_scope_frame = analysis_frame.copy()
    analysis_mode = "Resumen general"
    zone_placeholder = "Todas"
    place_placeholder = "Todos los puestos"
    table_placeholder = "Todas las mesas"
    selected_zone_code = zone_placeholder
    selected_polling_place_id = place_placeholder
    selected_table_id = table_placeholder
    selected_polling_place_label = place_placeholder
    selected_table_label = table_placeholder

    if st.session_state.get("_last_drilldown_municipality") != selected_municipality:
        st.session_state["_last_drilldown_municipality"] = selected_municipality
        st.session_state["analysis_mode"] = (
            "Resumen municipal" if selected_municipality != "Todos" else "Resumen general"
        )
        st.session_state["selected_zone_code"] = zone_placeholder
        st.session_state["selected_polling_place_id"] = place_placeholder
        st.session_state["selected_table_id"] = table_placeholder

    if selected_municipality != "Todos":
        st.markdown("### Centro de mando territorial")
        st.caption(
            "Escoge el nivel de lectura del municipio para bajar rapido a zona, puesto o mesa sin perder el contexto del senador."
        )
        analysis_mode = st.radio(
            "Modo de analisis",
            options=[
                "Resumen municipal",
                "Analisis por zona",
                "Analisis por puesto",
                "Analisis de mesa",
            ],
            horizontal=True,
            key="analysis_mode",
            label_visibility="collapsed",
        )

        zone_options = [zone_placeholder] + sorted(
            analysis_frame["zone_code"].dropna().astype("string").unique().tolist()
        )
        if st.session_state.get("selected_zone_code") not in zone_options:
            st.session_state["selected_zone_code"] = zone_placeholder

        place_source_frame = analysis_frame.copy()
        if st.session_state["selected_zone_code"] != zone_placeholder:
            place_source_frame = place_source_frame[
                place_source_frame["zone_code"].eq(st.session_state["selected_zone_code"])
            ]

        place_catalog = build_polling_place_catalog(place_source_frame)
        place_options = [place_placeholder] + place_catalog["polling_place_id"].tolist()
        place_label_map = {
            place_placeholder: place_placeholder,
            **dict(zip(place_catalog["polling_place_id"], place_catalog["label"])),
        }
        if st.session_state.get("selected_polling_place_id") not in place_options:
            st.session_state["selected_polling_place_id"] = place_placeholder

        table_source_frame = place_source_frame.copy()
        if st.session_state["selected_polling_place_id"] != place_placeholder:
            table_source_frame = table_source_frame[
                table_source_frame["polling_place_id"].eq(st.session_state["selected_polling_place_id"])
            ]

        table_catalog = build_table_catalog(table_source_frame)
        table_options = [table_placeholder] + table_catalog["table_id"].tolist()
        table_label_map = {
            table_placeholder: table_placeholder,
            **dict(zip(table_catalog["table_id"], table_catalog["label"])),
        }
        if st.session_state.get("selected_table_id") not in table_options:
            st.session_state["selected_table_id"] = table_placeholder

        control_cols = st.columns([1.15, 1.15, 1.55, 1.85], gap="small")
        with control_cols[0]:
            st.markdown(
                f"""
<div style="background:#ffffff;border:1px solid #e2e6ed;border-radius:10px;padding:14px 16px;min-height:86px;">
    <div style="font-size:0.74rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">Municipio activo</div>
    <div style="font-size:1.1rem;font-weight:700;color:#1a1a2e;margin-top:6px;">{escape(selected_municipality)}</div>
    <div style="font-size:0.82rem;color:#64748b;margin-top:4px;">Modo: {escape(analysis_mode)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with control_cols[1]:
            st.selectbox(
                "Zona",
                options=zone_options,
                key="selected_zone_code",
                label_visibility="visible",
            )
            selected_zone_code = st.session_state["selected_zone_code"]
        with control_cols[2]:
            if analysis_mode in {"Analisis por puesto", "Analisis de mesa"}:
                st.selectbox(
                    "Puesto",
                    options=place_options,
                    key="selected_polling_place_id",
                    format_func=lambda value: place_label_map.get(value, value),
                )
                selected_polling_place_id = st.session_state["selected_polling_place_id"]
                selected_polling_place_label = place_label_map.get(
                    selected_polling_place_id,
                    place_placeholder,
                )
            else:
                st.markdown(
                    f"""
<div style="background:#ffffff;border:1px solid #e2e6ed;border-radius:10px;padding:14px 16px;min-height:86px;">
    <div style="font-size:0.74rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">Puestos disponibles</div>
    <div style="font-size:1.1rem;font-weight:700;color:#1a1a2e;margin-top:6px;">{len(place_catalog):,}</div>
    <div style="font-size:0.82rem;color:#64748b;margin-top:4px;">Activa "Analisis por puesto" para bajar un nivel.</div>
</div>
""",
                    unsafe_allow_html=True,
                )
        with control_cols[3]:
            if analysis_mode == "Analisis de mesa":
                st.selectbox(
                    "Mesa",
                    options=table_options,
                    key="selected_table_id",
                    format_func=lambda value: table_label_map.get(value, value),
                )
                selected_table_id = st.session_state["selected_table_id"]
                selected_table_label = table_label_map.get(selected_table_id, table_placeholder)
            else:
                st.markdown(
                    f"""
<div style="background:#ffffff;border:1px solid #e2e6ed;border-radius:10px;padding:14px 16px;min-height:86px;">
    <div style="font-size:0.74rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;">Mesas visibles</div>
    <div style="font-size:1.1rem;font-weight:700;color:#1a1a2e;margin-top:6px;">{table_source_frame['table_id'].nunique():,}</div>
    <div style="font-size:0.82rem;color:#64748b;margin-top:4px;">Filtra zona o puesto para acercarte a la operacion.</div>
</div>
""",
                    unsafe_allow_html=True,
                )

        if analysis_mode in {"Analisis por zona", "Analisis por puesto", "Analisis de mesa"}:
            if selected_zone_code != zone_placeholder:
                analysis_scope_frame = analysis_scope_frame[
                    analysis_scope_frame["zone_code"].eq(selected_zone_code)
                ]
        if analysis_mode in {"Analisis por puesto", "Analisis de mesa"}:
            selected_polling_place_id = st.session_state.get(
                "selected_polling_place_id",
                place_placeholder,
            )
            selected_polling_place_label = place_label_map.get(
                selected_polling_place_id,
                place_placeholder,
            )
            if selected_polling_place_id != place_placeholder:
                analysis_scope_frame = analysis_scope_frame[
                    analysis_scope_frame["polling_place_id"].eq(selected_polling_place_id)
                ]
        if analysis_mode == "Analisis de mesa":
            selected_table_id = st.session_state.get("selected_table_id", table_placeholder)
            selected_table_label = table_label_map.get(selected_table_id, table_placeholder)
            if selected_table_id != table_placeholder:
                analysis_scope_frame = analysis_scope_frame[
                    analysis_scope_frame["table_id"].eq(selected_table_id)
                ]

        active_scope_parts = [selected_municipality]
        if selected_zone_code != zone_placeholder:
            active_scope_parts.append(f"Zona {selected_zone_code}")
        if selected_polling_place_id != place_placeholder:
            active_scope_parts.append(selected_polling_place_label)
        if selected_table_id != table_placeholder:
            active_scope_parts.append(selected_table_label)
        st.caption("Territorio activo: " + " -> ".join(active_scope_parts))

    candidate_performance = build_candidate_table_performance(
        analysis_scope_frame,
        candidate_name=selected_candidate,
        thresholds=APP_SETTINGS.classification,
    )
    summary = summarize_candidate_scope(candidate_performance)
    table_rankings = rank_tables(candidate_performance)
    place_rankings = rank_polling_places(candidate_performance)
    municipality_rankings = rank_municipalities(candidate_performance)
    zone_rankings = rank_zones(candidate_performance)
    top_tables = table_rankings.head(50)
    top_places = place_rankings.head(30)
    top_municipalities = municipality_rankings.head(30)
    top_zones = zone_rankings.head(30)
    close_losses = tables_lost_by_close_margin(candidate_performance).head(50)
    won_tables_df = tables_won(candidate_performance).head(50)
    total_scope_tables = int(candidate_performance["table_id"].nunique())
    coverage_frame = build_coverage_frame(summary, total_scope_tables)

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.metric(
            "Votos totales",
            format_int(summary["total_votes"]),
            help="Suma total de votos del candidato en el alcance territorial actual.",
        )
    with kpi_cols[1]:
        st.metric(
            "Mesas con votos",
            format_int(summary["tables_with_votes"]),
            help="Cantidad de mesas donde el candidato obtuvo al menos un voto.",
        )
    with kpi_cols[2]:
        st.metric(
            "Participacion prom.",
            format_pct(summary["average_share"]),
            help=(
                "Promedio del porcentaje del candidato por mesa activa. "
                "En cada mesa se calcula votos del candidato / total de votos de esa mesa, "
                "y luego se promedia solo en las mesas donde obtuvo votos."
            ),
        )
    with kpi_cols[3]:
        st.metric(
            "Municipios activos",
            format_int(summary["municipalities_with_votes"]),
            help="Municipios del alcance actual donde el candidato registra votos.",
        )
    with kpi_cols[4]:
        st.metric(
            "Mesas ganadas",
            format_int(summary["winning_tables"]),
            help="Mesas en las que el candidato fue la opcion con mas votos.",
        )

    if candidate_performance.empty:
        st.warning("No hay datos para el alcance territorial seleccionado.")
        return

    if selected_municipality == "Todos":
        render_top_territory_cards(
            municipality_rankings,
            title="Municipios con mas votos",
            name_column="municipality_name",
            empty_message="No hay municipios para mostrar.",
        )
    else:
        render_top_territory_cards(
            zone_rankings,
            title="Zonas con mas votos",
            name_column="zone_label",
            empty_message="No hay zonas para mostrar.",
        )

    if selected_municipality == "Todos":
        chart_votes_frame = municipality_rankings.sort_values(
            ["candidate_votes", "candidate_share"],
            ascending=[False, False],
        ).head(8)
        chart_share_frame = municipality_rankings.sort_values(
            ["candidate_share", "candidate_votes"],
            ascending=[False, False],
        ).head(8)
        chart_category_column = "municipality_name"
        chart_category_title = "Municipio"
        votes_chart_title = "Municipios con mas votos"
        share_chart_title = "Top municipios por participacion"
    else:
        chart_votes_frame = zone_rankings.sort_values(
            ["candidate_votes", "candidate_share"],
            ascending=[False, False],
        ).head(8)
        chart_share_frame = zone_rankings.sort_values(
            ["candidate_share", "candidate_votes"],
            ascending=[False, False],
        ).head(8)
        chart_category_column = "zone_label"
        chart_category_title = "Zona"
        votes_chart_title = "Top zonas por votos"
        share_chart_title = "Top zonas por participacion"

        if analysis_mode == "Analisis por zona" and selected_zone_code != zone_placeholder:
            chart_votes_frame = place_rankings.sort_values(
                ["candidate_votes", "candidate_share"],
                ascending=[False, False],
            ).head(8)
            chart_share_frame = place_rankings.sort_values(
                ["candidate_share", "candidate_votes"],
                ascending=[False, False],
            ).head(8)
            chart_category_column = "polling_place_name"
            chart_category_title = "Puesto"
            votes_chart_title = "Top puestos por votos en la zona"
            share_chart_title = "Top puestos por participacion en la zona"

        if analysis_mode == "Analisis por puesto":
            if selected_polling_place_id != place_placeholder:
                table_chart_frame = table_rankings.copy()
                table_chart_frame["table_label"] = (
                    "Mesa " + table_chart_frame["table_code"].astype("string")
                )
                chart_votes_frame = table_chart_frame.sort_values(
                    ["candidate_votes", "candidate_share"],
                    ascending=[False, False],
                ).head(8)
                chart_share_frame = table_chart_frame.sort_values(
                    ["candidate_share", "candidate_votes"],
                    ascending=[False, False],
                ).head(8)
                chart_category_column = "table_label"
                chart_category_title = "Mesa"
                votes_chart_title = "Top mesas por votos en el puesto"
                share_chart_title = "Top mesas por participacion en el puesto"
            else:
                chart_votes_frame = place_rankings.sort_values(
                    ["candidate_votes", "candidate_share"],
                    ascending=[False, False],
                ).head(8)
                chart_share_frame = place_rankings.sort_values(
                    ["candidate_share", "candidate_votes"],
                    ascending=[False, False],
                ).head(8)
                chart_category_column = "polling_place_name"
                chart_category_title = "Puesto"
                votes_chart_title = "Top puestos por votos"
                share_chart_title = "Top puestos por participacion"

        if analysis_mode == "Analisis de mesa":
            if selected_table_id != table_placeholder:
                mesa_breakdown = build_table_candidate_breakdown(analysis_scope_frame).head(8)
                chart_votes_frame = mesa_breakdown
                chart_share_frame = mesa_breakdown
                chart_category_column = "candidate_name"
                chart_category_title = "Candidato"
                votes_chart_title = "Votos por candidato en la mesa"
                share_chart_title = "Participacion por candidato en la mesa"
            elif selected_polling_place_id != place_placeholder:
                table_chart_frame = table_rankings.copy()
                table_chart_frame["table_label"] = (
                    "Mesa " + table_chart_frame["table_code"].astype("string")
                )
                chart_votes_frame = table_chart_frame.sort_values(
                    ["candidate_votes", "candidate_share"],
                    ascending=[False, False],
                ).head(8)
                chart_share_frame = table_chart_frame.sort_values(
                    ["candidate_share", "candidate_votes"],
                    ascending=[False, False],
                ).head(8)
                chart_category_column = "table_label"
                chart_category_title = "Mesa"
                votes_chart_title = "Top mesas por votos"
                share_chart_title = "Top mesas por participacion"
            else:
                chart_votes_frame = place_rankings.sort_values(
                    ["candidate_votes", "candidate_share"],
                    ascending=[False, False],
                ).head(8)
                chart_share_frame = place_rankings.sort_values(
                    ["candidate_share", "candidate_votes"],
                    ascending=[False, False],
                ).head(8)
                chart_category_column = "polling_place_name"
                chart_category_title = "Puesto"
                votes_chart_title = "Top puestos por votos"
                share_chart_title = "Top puestos por participacion"

    st.divider()

    chart_votes_tab, chart_share_tab = st.tabs(["📊 Votos", "📈 Participacion"])
    with chart_votes_tab:
        render_chart(
            build_bar_chart(
                chart_votes_frame,
                category_column=chart_category_column,
                value_column="candidate_votes",
                title=votes_chart_title,
                value_title="Votos",
                category_title=chart_category_title,
            )
        )
    with chart_share_tab:
        render_chart(
            build_share_chart(
                chart_share_frame,
                category_column=chart_category_column,
                title=share_chart_title,
                category_title=chart_category_title,
            )
        )

    coverage_cols = st.columns(3, gap="small")
    with coverage_cols[0]:
        st.metric(
            "Mesas observadas",
            format_int(total_scope_tables),
            help="Total de mesas dentro del alcance territorial actual.",
        )
    with coverage_cols[1]:
        st.metric(
            "Mesas sin votos",
            format_int(max(total_scope_tables - int(summary["tables_with_votes"]), 0)),
            help="Mesas del alcance donde el candidato no registro votos.",
        )
    with coverage_cols[2]:
        coverage_pct = (
            int(summary["tables_with_votes"]) / total_scope_tables if total_scope_tables else 0.0
        )
        st.metric(
            "Cobertura de mesas",
            format_pct(coverage_pct),
            help="Porcentaje de mesas del alcance donde el candidato si obtuvo votos.",
        )

    st.markdown("### Cobertura de mesas")
    render_chart(
        build_bar_chart(
            coverage_frame,
            category_column="segment",
            value_column="tables",
            title="Resumen de presencia territorial",
            value_title="Mesas",
            category_title="Indicador",
        )
    )

    st.divider()

    if compare_selection != comparison_placeholder:
        compare_performance = build_candidate_table_performance(
            analysis_scope_frame,
            candidate_name=compare_selection,
            thresholds=APP_SETTINGS.classification,
        )

        comparison = candidate_performance[
            [
                "table_id",
                "municipality_name",
                "polling_place_name",
                "table_code",
                "candidate_votes",
                "candidate_share",
                "is_winner",
            ]
        ].merge(
            compare_performance[
                ["table_id", "candidate_votes", "candidate_share", "is_winner"]
            ],
            on="table_id",
            suffixes=("_foco", "_rival"),
            how="outer",
        )

        comparison["candidate_votes_foco"] = (
            comparison["candidate_votes_foco"].fillna(0).astype("Int64")
        )
        comparison["candidate_votes_rival"] = (
            comparison["candidate_votes_rival"].fillna(0).astype("Int64")
        )
        comparison["candidate_share_foco"] = comparison["candidate_share_foco"].fillna(0.0)
        comparison["candidate_share_rival"] = comparison["candidate_share_rival"].fillna(0.0)
        comparison["diferencia"] = (
            comparison["candidate_votes_foco"] - comparison["candidate_votes_rival"]
        ).astype("Int64")
        comparison["share_foco_pct"] = comparison["candidate_share_foco"] * 100
        comparison["share_rival_pct"] = comparison["candidate_share_rival"] * 100
        comparison = comparison.sort_values("diferencia", ascending=False)

        selected_candidate_label = selected_candidate.split()[0]
        compare_candidate_label = compare_selection.split()[0]

        st.markdown("### Comparacion con rival")
        st.dataframe(
            comparison[
                [
                    "municipality_name",
                    "polling_place_name",
                    "table_code",
                    "candidate_votes_foco",
                    "share_foco_pct",
                    "candidate_votes_rival",
                    "share_rival_pct",
                    "diferencia",
                ]
            ].head(100),
            use_container_width=True,
            column_config={
                "municipality_name": "Municipio",
                "polling_place_name": "Puesto",
                "table_code": "Mesa",
                "candidate_votes_foco": st.column_config.NumberColumn(
                    f"Votos {selected_candidate_label}",
                    format="%d",
                ),
                "share_foco_pct": st.column_config.NumberColumn(
                    f"% {selected_candidate_label}",
                    format="%.1f%%",
                ),
                "candidate_votes_rival": st.column_config.NumberColumn(
                    f"Votos {compare_candidate_label}",
                    format="%d",
                ),
                "share_rival_pct": st.column_config.NumberColumn(
                    f"% {compare_candidate_label}",
                    format="%.1f%%",
                ),
                "diferencia": st.column_config.NumberColumn("Diferencia", format="%d"),
            },
        )
        st.divider()

    if selected_municipality == "Todos":
        tab_mesas, tab_puestos, tab_munis, tab_margenes = st.tabs(
            ["🏅 Top mesas", "📍 Top puestos", "🏘️ Top municipios", "⚔️ Margenes"]
        )

        with tab_mesas:
            display_top_tables = top_tables.copy()
            display_top_tables["candidate_share"] = display_top_tables["candidate_share"] * 100
            st.dataframe(
                display_top_tables[
                    [
                        "department_name",
                        "municipality_name",
                        "zone_code",
                        "polling_place_name",
                        "table_code",
                        "candidate_votes",
                        "total_table_votes",
                        "candidate_share",
                        "margin_against_best_competitor",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "department_name": "Departamento",
                    "municipality_name": "Municipio",
                    "zone_code": "Zona",
                    "polling_place_name": "Puesto",
                    "table_code": "Mesa",
                    "candidate_votes": st.column_config.NumberColumn("Votos candidato", format="%d"),
                    "total_table_votes": st.column_config.NumberColumn("Total mesa", format="%d"),
                    "candidate_share": st.column_config.NumberColumn(
                        "% candidato",
                        format="%.1f%%",
                        help="Porcentaje del candidato en la mesa",
                    ),
                    "margin_against_best_competitor": st.column_config.NumberColumn(
                        "Margen vs mejor competidor",
                        format="%d",
                    ),
                },
            )

        with tab_puestos:
            display_top_places = top_places.copy()
            display_top_places["candidate_share"] = display_top_places["candidate_share"] * 100
            st.dataframe(
                display_top_places[
                    [
                        "department_name",
                        "municipality_name",
                        "zone_code",
                        "polling_place_name",
                        "candidate_votes",
                        "total_votes",
                        "candidate_share",
                        "tables_with_votes",
                        "winning_tables",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "department_name": "Departamento",
                    "municipality_name": "Municipio",
                    "zone_code": "Zona",
                    "polling_place_name": "Puesto",
                    "candidate_votes": st.column_config.NumberColumn("Votos candidato", format="%d"),
                    "total_votes": st.column_config.NumberColumn("Votos del puesto", format="%d"),
                    "candidate_share": st.column_config.NumberColumn(
                        "Participacion %",
                        format="%.1f%%",
                    ),
                    "tables_with_votes": st.column_config.NumberColumn(
                        "Mesas con votos",
                        format="%d",
                    ),
                    "winning_tables": st.column_config.NumberColumn("Mesas ganadas", format="%d"),
                },
            )

        with tab_munis:
            display_top_municipalities = top_municipalities.copy()
            display_top_municipalities["candidate_share"] = (
                display_top_municipalities["candidate_share"] * 100
            )
            st.dataframe(
                display_top_municipalities[
                    [
                        "department_name",
                        "municipality_name",
                        "candidate_votes",
                        "total_votes",
                        "candidate_share",
                        "polling_places",
                        "winning_tables",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "department_name": "Departamento",
                    "municipality_name": "Municipio",
                    "candidate_votes": st.column_config.NumberColumn("Votos candidato", format="%d"),
                    "total_votes": st.column_config.NumberColumn(
                        "Votos del municipio",
                        format="%d",
                    ),
                    "candidate_share": st.column_config.NumberColumn(
                        "Participacion %",
                        format="%.1f%%",
                    ),
                    "polling_places": st.column_config.NumberColumn("Puestos", format="%d"),
                    "winning_tables": st.column_config.NumberColumn("Mesas ganadas", format="%d"),
                },
            )
    else:
        tab_zonas, tab_puestos, tab_mesas, tab_margenes = st.tabs(
            ["🧭 Zonas", "📍 Puestos", "🗳️ Mesas", "⚔️ Margenes"]
        )

        with tab_zonas:
            display_top_zones = top_zones.copy()
            display_top_zones["candidate_share"] = display_top_zones["candidate_share"] * 100
            st.dataframe(
                display_top_zones[
                    [
                        "department_name",
                        "municipality_name",
                        "zone_code",
                        "candidate_votes",
                        "total_votes",
                        "candidate_share",
                        "polling_places",
                        "tables",
                        "winning_tables",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "department_name": "Departamento",
                    "municipality_name": "Municipio",
                    "zone_code": "Zona",
                    "candidate_votes": st.column_config.NumberColumn("Votos candidato", format="%d"),
                    "total_votes": st.column_config.NumberColumn("Votos de la zona", format="%d"),
                    "candidate_share": st.column_config.NumberColumn(
                        "Participacion %",
                        format="%.1f%%",
                    ),
                    "polling_places": st.column_config.NumberColumn("Puestos", format="%d"),
                    "tables": st.column_config.NumberColumn("Mesas", format="%d"),
                    "winning_tables": st.column_config.NumberColumn("Mesas ganadas", format="%d"),
                },
            )

        with tab_puestos:
            display_top_places = top_places.copy()
            display_top_places["candidate_share"] = display_top_places["candidate_share"] * 100
            st.dataframe(
                display_top_places[
                    [
                        "department_name",
                        "municipality_name",
                        "zone_code",
                        "polling_place_name",
                        "candidate_votes",
                        "total_votes",
                        "candidate_share",
                        "tables_with_votes",
                        "winning_tables",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "department_name": "Departamento",
                    "municipality_name": "Municipio",
                    "zone_code": "Zona",
                    "polling_place_name": "Puesto",
                    "candidate_votes": st.column_config.NumberColumn("Votos candidato", format="%d"),
                    "total_votes": st.column_config.NumberColumn("Votos del puesto", format="%d"),
                    "candidate_share": st.column_config.NumberColumn(
                        "Participacion %",
                        format="%.1f%%",
                    ),
                    "tables_with_votes": st.column_config.NumberColumn(
                        "Mesas con votos",
                        format="%d",
                    ),
                    "winning_tables": st.column_config.NumberColumn("Mesas ganadas", format="%d"),
                },
            )

        with tab_mesas:
            display_top_tables = top_tables.copy()
            display_top_tables["candidate_share"] = display_top_tables["candidate_share"] * 100
            st.dataframe(
                display_top_tables[
                    [
                        "department_name",
                        "municipality_name",
                        "zone_code",
                        "polling_place_name",
                        "table_code",
                        "candidate_votes",
                        "total_table_votes",
                        "candidate_share",
                        "margin_against_best_competitor",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "department_name": "Departamento",
                    "municipality_name": "Municipio",
                    "zone_code": "Zona",
                    "polling_place_name": "Puesto",
                    "table_code": "Mesa",
                    "candidate_votes": st.column_config.NumberColumn("Votos candidato", format="%d"),
                    "total_table_votes": st.column_config.NumberColumn("Total mesa", format="%d"),
                    "candidate_share": st.column_config.NumberColumn(
                        "% candidato",
                        format="%.1f%%",
                    ),
                    "margin_against_best_competitor": st.column_config.NumberColumn(
                        "Margen vs mejor competidor",
                        format="%d",
                    ),
                },
            )

    with tab_margenes:
        losses_col, wins_col = st.columns(2)
        with losses_col:
            st.markdown("##### Mesas perdidas por poco margen")
            losses_display = close_losses.copy()
            losses_display["margen_pct"] = (
                losses_display["loss_margin"]
                / losses_display["total_table_votes"].replace(0, pd.NA)
                * 100
            ).fillna(0.0)
            st.dataframe(
                losses_display[
                    [
                        "municipality_name",
                        "polling_place_name",
                        "table_code",
                        "candidate_votes",
                        "winner_label",
                        "winner_votes",
                        "loss_margin",
                        "margen_pct",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "municipality_name": "Municipio",
                    "polling_place_name": "Puesto",
                    "table_code": "Mesa",
                    "candidate_votes": st.column_config.NumberColumn(
                        "Votos candidato",
                        format="%d",
                    ),
                    "winner_label": "Ganador de la mesa",
                    "winner_votes": st.column_config.NumberColumn(
                        "Votos ganador",
                        format="%d",
                    ),
                    "loss_margin": st.column_config.NumberColumn(
                        "Margen de derrota",
                        format="%d",
                    ),
                    "margen_pct": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
                },
            )

        with wins_col:
            st.markdown("##### Mesas ganadas")
            won_display = won_tables_df.copy()
            won_display["margen_pct"] = (
                won_display["margin_against_best_competitor"]
                / won_display["total_table_votes"].replace(0, pd.NA)
                * 100
            ).fillna(0.0)
            st.dataframe(
                won_display[
                    [
                        "municipality_name",
                        "polling_place_name",
                        "table_code",
                        "candidate_votes",
                        "best_competitor_votes",
                        "margin_against_best_competitor",
                        "margen_pct",
                    ]
                ],
                use_container_width=True,
                column_config={
                    "municipality_name": "Municipio",
                    "polling_place_name": "Puesto",
                    "table_code": "Mesa",
                    "candidate_votes": st.column_config.NumberColumn(
                        "Votos candidato",
                        format="%d",
                    ),
                    "best_competitor_votes": st.column_config.NumberColumn(
                        "Mejor competidor",
                        format="%d",
                    ),
                    "margin_against_best_competitor": st.column_config.NumberColumn(
                        "Margen de victoria",
                        format="%d",
                    ),
                    "margen_pct": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
                },
            )

    st.divider()

    verification_title = (
        "Ver todos los candidatos en el alcance actual (verificacion)"
        if selected_municipality != "Todos"
        else "Ver todos los candidatos por mesa (verificacion)"
    )
    with st.expander(verification_title):
        all_candidates_by_scope = analysis_scope_frame[
            analysis_scope_frame["row_kind"].eq("candidate")
        ].copy()

        if all_candidates_by_scope.empty:
            st.info("No hay datos de candidatos para el filtro seleccionado.")
        else:
            pivot = (
                all_candidates_by_scope.groupby(
                    [
                        "municipality_name",
                        "polling_place_name",
                        "table_code",
                        "candidate_name",
                    ],
                    as_index=False,
                ).agg(votos=("votes", "sum"))
            )
            pivot["votos_mesa"] = pivot.groupby(
                ["municipality_name", "polling_place_name", "table_code"]
            )["votos"].transform("sum")
            pivot["porcentaje"] = (
                pivot["votos"] / pivot["votos_mesa"].replace(0, pd.NA) * 100
            ).fillna(0.0)

            st.dataframe(
                pivot.sort_values(
                    ["municipality_name", "polling_place_name", "table_code", "votos"],
                    ascending=[True, True, True, False],
                ),
                use_container_width=True,
                column_config={
                    "municipality_name": "Municipio",
                    "polling_place_name": "Puesto",
                    "table_code": "Mesa",
                    "candidate_name": "Candidato",
                    "votos": st.column_config.NumberColumn("Votos", format="%d"),
                    "votos_mesa": st.column_config.NumberColumn("Total mesa", format="%d"),
                    "porcentaje": st.column_config.NumberColumn("% en mesa", format="%.1f%%"),
                },
            )

    with st.expander("Informacion tecnica del dataset"):
        tech_col1, tech_col2 = st.columns(2)
        with tech_col1:
            st.markdown("##### Dataset y normalizacion")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Propiedad": [
                            "Archivo",
                            "Filas",
                            "Delimitador",
                            "Codificacion",
                            "Columnas detectadas",
                            "Columnas sin mapear",
                        ],
                        "Valor": [
                            bundle.spec.display_name,
                            bundle.profile.row_count,
                            bundle.csv_format.delimiter,
                            bundle.csv_format.encoding,
                            len(bundle.mapping.canonical_to_raw),
                            len(bundle.mapping.unresolved_raw),
                        ],
                    }
                ),
                use_container_width=True,
            )
        with tech_col2:
            st.markdown("##### Alcance del tablero")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Indicador": [
                            "Mesas observadas",
                            "Mesas con votos",
                            "Participacion promedio",
                        ],
                        "Detalle": [
                            format_int(total_scope_tables),
                            format_int(summary["tables_with_votes"]),
                            format_pct(summary["average_share"]),
                        ],
                    }
                ),
                use_container_width=True,
            )

        st.markdown("##### Columnas normalizadas")
        mapping_frame = pd.DataFrame(
            {
                "Canonica": list(bundle.mapping.canonical_to_raw.keys()),
                "Columna origen": list(bundle.mapping.canonical_to_raw.values()),
            }
        )
        st.dataframe(mapping_frame, use_container_width=True)
        if bundle.mapping.unresolved_raw:
            st.caption("Columnas sin mapear: " + ", ".join(bundle.mapping.unresolved_raw))

    st.download_button(
        "Descargar mesas filtradas a CSV",
        data=candidate_performance.to_csv(index=False).encode("utf-8"),
        file_name=build_download_name(bundle.spec.display_name, selected_candidate),
        mime="text/csv",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
