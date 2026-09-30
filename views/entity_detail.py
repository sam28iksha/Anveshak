"""Entity Detail — score breakdown, full findings list with evidence drill-down,
and peer comparison against sector benchmarks."""

import plotly.graph_objects as go
import streamlit as st

from analytics.peer_benchmarking import METRICS
from ui_common import (CATEGORY_COLORS, CATEGORY_LABELS, apply_chart_theme, band_badge,
                        evidence_table, load_data, page_header, severity_badge)

data = load_data()
scores = data["scores"]
findings = data["findings"]
metrics = data["metrics"]
tables = data["tables"]

st.sidebar.header("Select entity")
scores_sorted = scores.sort_values("total_score", ascending=False)
options = scores_sorted["entity_id"] + " — " + scores_sorted["name"] + f" (score " + \
          scores_sorted["total_score"].round(0).astype(int).astype(str) + ")"
default_idx = 0
choice = st.sidebar.radio("Entity", options.tolist(), index=default_idx, label_visibility="collapsed")
entity_id = choice.split(" — ")[0]

row = scores[scores["entity_id"] == entity_id].iloc[0]
ent_findings = findings[findings["entity_id"] == entity_id].sort_values("points", ascending=False)

page_header(row["name"], f"{row['sector']} · {row['tier']} · Rank #{int(row['rank'])} of {len(scores)}")

h2, h3, h4 = st.columns(3)
with h2:
    st.metric("Risk score", f"{row['total_score']:.0f} / 100")
    if row["raw_score"] > 100:
        st.caption(f"Uncapped sum of this entity's finding points: **{row['raw_score']:.1f}** "
                    f"— capped at 100 for display (see Methodology).")
    else:
        st.caption(f"= sum of this entity's finding points below, uncapped.")
with h3:
    st.markdown("Band")
    st.markdown(band_badge(row['band']), unsafe_allow_html=True)
h4.metric("Findings", int(row["n_findings"]))

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Score breakdown by category")
    cats = ["execution_gap_points", "negative_space_points", "audit_supervision_points"]
    labels = [CATEGORY_LABELS["execution_gap"], CATEGORY_LABELS["negative_space"], CATEGORY_LABELS["audit_supervision"]]
    colors = [CATEGORY_COLORS["execution_gap"], CATEGORY_COLORS["negative_space"], CATEGORY_COLORS["audit_supervision"]]
    fig = go.Figure(go.Bar(x=labels, y=[row[c] for c in cats], marker_color=colors,
                            text=[f"{row[c]:.1f}" for c in cats], textposition="outside"))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Points contributed")
    apply_chart_theme(fig)
    st.plotly_chart(fig)

with col2:
    st.subheader("Peer comparison (sector z-score)")
    st.caption("How many standard deviations this entity sits from its sector peer mean. "
               "Bars past ±1.5 are flagged as significant deviations.")
    m = metrics[metrics["entity_id"] == entity_id].iloc[0]
    metric_codes = [mc for mc, _ in METRICS]
    metric_names = [mn for _, mn in METRICS]
    zvals = [m[f"{c}_z"] for c in metric_codes]
    bar_colors = ["#C4324D" if abs(z) > 1.5 else "#A4B5C4" for z in zvals]
    fig2 = go.Figure(go.Bar(x=zvals, y=metric_names, orientation="h", marker_color=bar_colors))
    fig2.add_vline(x=1.5, line_dash="dash", line_color="#A4B5C4")
    fig2.add_vline(x=-1.5, line_dash="dash", line_color="#A4B5C4")
    fig2.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                        xaxis_title="Std deviations from sector peer mean")
    apply_chart_theme(fig2)
    st.plotly_chart(fig2)

    with st.expander("Show raw metric values vs. peer median"):
        for code, name in METRICS:
            st.write(f"**{name}:** {m[code]:.3f}  (sector peer median: {m[f'{code}_peer_median']:.3f})")

st.markdown("---")
st.subheader(f"All findings for {row['name']} ({len(ent_findings)})")

if ent_findings.empty:
    st.success("No findings triggered for this entity — clean across all detectors.")
else:
    category_filter = st.multiselect(
        "Filter by category", ["execution_gap", "negative_space", "audit_supervision"],
        default=["execution_gap", "negative_space", "audit_supervision"],
        format_func=lambda c: CATEGORY_LABELS[c],
    )
    shown = ent_findings[ent_findings["category"].isin(category_filter)]

    for _, f in shown.iterrows():
        header = f"{f['rule_name']}  —  {f['points']:.1f} pts"
        with st.expander(header):
            st.markdown(f"{severity_badge(f['severity'])} &nbsp; **Rule code:** `{f['rule_code']}`",
                        unsafe_allow_html=True)
            st.write(f"**Rationale:** {f['rationale']}")
            mc1, mc2 = st.columns(2)
            mc1.write(f"**Metric value:** {f['metric_value']}")
            mc2.write(f"**Threshold used:** {f['threshold_used']}")
            st.write(f"**Evidence:** {f['n_evidence']} {f['evidence_type']} record(s)")
            ev_df = evidence_table(tables, f["evidence_type"], f["evidence_ids"])
            if not ev_df.empty:
                st.dataframe(ev_df.head(200), width="stretch", height=220)
            else:
                st.caption("No individually-linked raw records for this rule (entity-level statistical finding).")
