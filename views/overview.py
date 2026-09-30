"""Overview — ranked entity risk table, category breakdown, and findings summary."""

import plotly.graph_objects as go
import streamlit as st

from ui_common import (APP_TITLE, APP_SUBTITLE, BAND_COLORS, CATEGORY_LABELS, CATEGORY_COLORS,
                        SEVERITY_COLORS, apply_chart_theme, load_data, page_header)

data = load_data()
scores = data["scores"]
findings = data["findings"]
trend = data["trend"]
entities = data["tables"]["entities"]

page_header(APP_TITLE, APP_SUBTITLE)

st.sidebar.header("Filters")
sectors = st.sidebar.multiselect("Sector", sorted(entities["sector"].unique()),
                                  default=sorted(entities["sector"].unique()))
sort_by = st.sidebar.selectbox(
    "Rank by",
    ["Total risk score", "Execution Gap points", "Negative Space points", "Audit Supervision points"],
)

view = scores[scores["sector"].isin(sectors)].copy()
sort_col_map = {
    "Total risk score": "total_score",
    "Execution Gap points": "execution_gap_points",
    "Negative Space points": "negative_space_points",
    "Audit Supervision points": "audit_supervision_points",
}
view = view.sort_values(sort_col_map[sort_by], ascending=False).reset_index(drop=True)
view["rank"] = view.index + 1

# ---- KPI row ----
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Entities under review", len(view))
c2.metric("Severe", int((view["band"] == "Severe").sum()))
c3.metric("Moderate", int((view["band"] == "Moderate").sum()))
c4.metric("Clean", int((view["band"] == "Clean").sum()))
c5.metric("Findings surfaced", len(findings[findings["entity_id"].isin(view["entity_id"])]))

st.markdown("---")

# ---- Ranked table with sparkline trend ----
st.subheader("Entity risk ranking")
st.caption("Composite score = transparent sum of documented rule points (see Methodology), capped at 100. "
           "Open Entity Detail in the sidebar to drill into evidence.")

trend_by_entity = {}
for entity_id, g in trend.groupby("entity_id"):
    g = g.sort_values("month")
    trend_by_entity[entity_id] = g["risk_proxy"].tolist()

table = view[["rank", "entity_id", "name", "sector", "tier", "total_score", "band",
              "execution_gap_points", "negative_space_points", "audit_supervision_points", "n_findings"]].copy()
table["trend"] = table["entity_id"].map(lambda e: trend_by_entity.get(e, [0]))

st.dataframe(
    table,
    column_config={
        "rank": st.column_config.NumberColumn("Rank", width="small"),
        "entity_id": st.column_config.TextColumn("ID", width="small"),
        "name": st.column_config.TextColumn("Entity"),
        "sector": st.column_config.TextColumn("Sector", width="small"),
        "tier": st.column_config.TextColumn("Tier", width="small"),
        "total_score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%.0f"),
        "band": st.column_config.TextColumn("Band", width="small"),
        "execution_gap_points": st.column_config.NumberColumn("Exec. Gap pts", format="%.1f"),
        "negative_space_points": st.column_config.NumberColumn("Neg. Space pts", format="%.1f"),
        "audit_supervision_points": st.column_config.NumberColumn("Audit Superv. pts", format="%.1f"),
        "n_findings": st.column_config.NumberColumn("# Findings", width="small"),
        "trend": st.column_config.LineChartColumn("Monthly risk trend", width="medium", y_min=0, y_max=100),
    },
    hide_index=True,
    width="stretch",
    height=460,
)

st.markdown("---")

col_a, col_b = st.columns([3, 2])

with col_a:
    st.subheader("Score by category")
    fig = go.Figure()
    for cat in ["execution_gap", "negative_space", "audit_supervision"]:
        fig.add_bar(
            x=view["entity_id"], y=view[f"{cat}_points"].clip(upper=100),
            name=CATEGORY_LABELS[cat], marker_color=CATEGORY_COLORS[cat],
        )
    fig.update_layout(barmode="stack", height=420,
                       legend=dict(orientation="h", yanchor="bottom", y=1.02),
                       margin=dict(l=10, r=10, t=30, b=10),
                       yaxis_title="Points (uncapped, pre-100 clip)")
    apply_chart_theme(fig)
    st.plotly_chart(fig)

with col_b:
    st.subheader("Risk band distribution")
    band_counts = view["band"].value_counts().reindex(["Severe", "Moderate", "Clean"]).fillna(0)
    fig2 = go.Figure(go.Bar(
        x=band_counts.values, y=band_counts.index, orientation="h",
        marker_color=[BAND_COLORS[b] for b in band_counts.index],
        text=band_counts.values.astype(int), textposition="outside",
    ))
    fig2.update_layout(height=420, margin=dict(l=10, r=30, t=30, b=10), xaxis_title="Entities")
    apply_chart_theme(fig2)
    st.plotly_chart(fig2)

st.markdown("---")
st.subheader("Findings by category and severity")
cat_sev = findings[findings["entity_id"].isin(view["entity_id"])].groupby(
    ["category", "severity"]).size().reset_index(name="count")
if not cat_sev.empty:
    fig3 = go.Figure()
    for sev in ["critical", "high", "medium", "low"]:
        sub = cat_sev[cat_sev["severity"] == sev]
        fig3.add_bar(x=sub["category"].map(CATEGORY_LABELS), y=sub["count"], name=sev.title(),
                     marker_color=SEVERITY_COLORS[sev])
    fig3.update_layout(barmode="stack", height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="# Findings")
    apply_chart_theme(fig3)
    st.plotly_chart(fig3)
else:
    st.info("No findings for the current filter selection.")
