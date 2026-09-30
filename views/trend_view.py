"""Trend View — risk trajectory over time across entities, for spotting emerging
patterns rather than only point-in-time snapshots."""

import plotly.graph_objects as go
import streamlit as st

from ui_common import SECTOR_COLORS, apply_chart_theme, load_data, page_header

data = load_data()
trend = data["trend"]
scores = data["scores"]
entities = data["tables"]["entities"]

page_header("Trend View", "Monthly risk proxy — a lightweight blend of fast-closure rate, "
            "no-escalation rate, and audit-unaccounted rate for that month (see Methodology for "
            "the formula). Use this to spot whether a problem is a one-off spike or a sustained pattern.")

st.sidebar.header("Entities to plot")
default_entities = scores.sort_values("total_score", ascending=False)["entity_id"].head(5).tolist()
selected = st.sidebar.multiselect("Entity", sorted(entities["entity_id"].unique()), default=default_entities)

if not selected:
    st.info("Select at least one entity from the sidebar.")
    st.stop()

months = sorted(trend["month"].unique())
name_map = entities.set_index("entity_id")["name"].to_dict()
sector_map = entities.set_index("entity_id")["sector"].to_dict()

st.subheader("Monthly risk proxy over time")
fig = go.Figure()
for eid in selected:
    g = trend[trend["entity_id"] == eid].sort_values("month")
    fig.add_scatter(x=g["month"], y=g["risk_proxy"], mode="lines+markers",
                     name=f"{eid} — {name_map.get(eid, '')}",
                     line=dict(color=SECTOR_COLORS.get(sector_map.get(eid), "#A4B5C4")))
fig.update_layout(height=440, margin=dict(l=10, r=10, t=10, b=10),
                   yaxis_title="Monthly risk proxy (0-100)", xaxis_title="Month",
                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
apply_chart_theme(fig)
st.plotly_chart(fig)

st.markdown("---")
st.subheader("All entities — risk-proxy heatmap")
st.caption("Every entity, every month, at a glance. Darker navy = higher monthly risk proxy that month.")

pivot = trend.pivot_table(index="entity_id", columns="month", values="risk_proxy", fill_value=0)
pivot = pivot.reindex(scores.sort_values("total_score", ascending=False)["entity_id"])
fig2 = go.Figure(go.Heatmap(
    z=pivot.values, x=pivot.columns, y=pivot.index,
    colorscale=[[0, "#F7F2EA"], [0.5, "#A68868"], [1, "#071739"]],
    colorbar=dict(title="Risk"),
))
fig2.update_layout(height=480, margin=dict(l=10, r=10, t=10, b=10))
apply_chart_theme(fig2)
st.plotly_chart(fig2)
