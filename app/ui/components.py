from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from app.ui.formatters import format_int, format_pct


def render_summary_metrics(summary: dict[str, float | int]) -> None:
    columns = st.columns(5)
    columns[0].metric("Votos del candidato", format_int(summary["total_votes"]))
    columns[1].metric("Mesas con votos", format_int(summary["tables_with_votes"]))
    columns[2].metric("Promedio sobre mesa", format_pct(float(summary["average_share"])))
    columns[3].metric(
        "Municipios donde compite",
        format_int(summary["municipalities_with_votes"]),
    )
    columns[4].metric("Mesas ganadas", format_int(summary["winning_tables"]))


def build_bar_chart(
    frame: pd.DataFrame,
    category_column: str,
    value_column: str,
    title: str,
    value_title: str,
    category_title: str | None = None,
) -> alt.Chart | None:
    if frame.empty:
        return None

    chart_data = frame.copy()
    tooltip = [
        alt.Tooltip(
            f"{category_column}:N",
            title=category_title or category_column.replace("_", " ").title(),
        ),
        alt.Tooltip(f"{value_column}:Q", title=value_title, format=",.0f"),
    ]

    if "candidate_share" in chart_data.columns:
        chart_data["share_pct"] = chart_data["candidate_share"] * 100
        tooltip.append(
            alt.Tooltip("share_pct:Q", title="Participacion %", format=".1f")
        )

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X(
                f"{value_column}:Q",
                title=value_title,
                axis=alt.Axis(format=",d"),
            ),
            y=alt.Y(
                f"{category_column}:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=200),
            ),
            tooltip=tooltip,
        )
        .properties(title=title, height=280)
        .configure_view(strokeOpacity=0)
    )


def build_share_chart(
    frame: pd.DataFrame,
    category_column: str,
    title: str,
    category_title: str | None = None,
) -> alt.Chart | None:
    if frame.empty:
        return None

    chart_data = frame.copy()
    chart_data["share_pct"] = chart_data["candidate_share"] * 100

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#0B5FFF")
        .encode(
            x=alt.X(
                "share_pct:Q",
                title="Participacion %",
                axis=alt.Axis(format=".0f", labelExpr="datum.value + '%'"),
            ),
            y=alt.Y(
                f"{category_column}:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=200),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{category_column}:N",
                    title=category_title or category_column.replace("_", " ").title(),
                ),
                alt.Tooltip("candidate_votes:Q", title="Votos", format=",.0f"),
                alt.Tooltip("share_pct:Q", title="Participacion %", format=".1f"),
            ],
        )
        .properties(title=title, height=280)
        .configure_view(strokeOpacity=0)
    )


def render_chart(chart: alt.Chart | None, use_container_width: bool = True) -> None:
    if chart is None:
        st.info("No hay datos suficientes para esta grafica.")
        return
    st.altair_chart(chart, use_container_width=use_container_width)
