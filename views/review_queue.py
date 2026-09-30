"""Review Queue — a single prioritized worklist of specific alerts, cases and
audit-log entries flagged for manual supervisory review, sorted by severity."""

import streamlit as st

from ui_common import CATEGORY_LABELS, evidence_table, load_data, page_header, severity_badge

data = load_data()
rq = data["review_queue"]
tables = data["tables"]
entities = tables["entities"]

page_header("Review Queue", "Every piece of evidence behind every finding, flattened into one "
            "worklist and sorted by severity. Work top to bottom.")

st.sidebar.header("Filters")
entity_filter = st.sidebar.multiselect("Entity", sorted(rq["entity_id"].unique()))
severity_filter = st.sidebar.multiselect("Severity", ["critical", "high", "medium", "low"],
                                          default=["critical", "high"])
category_filter = st.sidebar.multiselect(
    "Category", ["execution_gap", "negative_space", "audit_supervision"],
    format_func=lambda c: CATEGORY_LABELS[c],
)
evidence_type_filter = st.sidebar.multiselect("Evidence type", sorted(rq["evidence_type"].unique()))

view = rq.copy()
if entity_filter:
    view = view[view["entity_id"].isin(entity_filter)]
if severity_filter:
    view = view[view["severity"].isin(severity_filter)]
if category_filter:
    view = view[view["category"].isin(category_filter)]
if evidence_type_filter:
    view = view[view["evidence_type"].isin(evidence_type_filter)]

st.metric("Items in queue", len(view))

display_cols = ["entity_id", "severity", "category", "evidence_type", "evidence_id", "rule_name",
                 "rationale", "priority_score"]
event = st.dataframe(
    view[display_cols],
    column_config={
        "entity_id": st.column_config.TextColumn("Entity", width="small"),
        "severity": st.column_config.TextColumn("Severity", width="small"),
        "category": st.column_config.TextColumn("Category"),
        "evidence_type": st.column_config.TextColumn("Type", width="small"),
        "evidence_id": st.column_config.TextColumn("Evidence ID"),
        "rule_name": st.column_config.TextColumn("Rule"),
        "rationale": st.column_config.TextColumn("Rationale", width="large"),
        "priority_score": st.column_config.NumberColumn("Priority", format="%.1f"),
    },
    hide_index=True,
    width="stretch",
    height=500,
    on_select="rerun",
    selection_mode="single-row",
)

st.markdown("---")
st.subheader("Selected item detail")

sel = event.selection.rows if event and event.selection else []
if not sel:
    st.info("Select a row above to see the raw underlying record.")
else:
    item = view.iloc[sel[0]]
    st.markdown(f"{severity_badge(item['severity'])} &nbsp; **{item['rule_name']}**", unsafe_allow_html=True)
    st.write(f"**Entity:** {item['entity_id']}  |  **Evidence:** {item['evidence_type']} `{item['evidence_id']}`")
    st.write(f"**Rationale:** {item['rationale']}")
    ev_df = evidence_table(tables, item["evidence_type"], [item["evidence_id"]])
    if not ev_df.empty:
        st.dataframe(ev_df, width="stretch")
    st.caption(f"Full finding reference: `{item['finding_id']}` — see Entity Detail page for the complete "
               f"rule context (metric value, threshold, full evidence set).")
