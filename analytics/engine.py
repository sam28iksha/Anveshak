"""Orchestration layer: load data -> run detectors -> score -> build review queue.
This is the single entry point the Streamlit app calls.
"""

import pandas as pd
import streamlit as st

from analytics import db
from analytics.detectors import run_all_detectors
from analytics.scoring import compute_composite_scores, compute_monthly_trend
from analytics.peer_benchmarking import compute_entity_metrics, compute_peer_zscores


@st.cache_data(show_spinner=False)
def load_dataset(db_path: str):
    return db.load_all(db_path)


@st.cache_data(show_spinner=False)
def build_analytics(db_path: str):
    tables = db.load_all(db_path)
    findings_df = run_all_detectors(tables)
    scores_df = compute_composite_scores(findings_df, tables["entities"])
    metrics_df = compute_entity_metrics(tables)
    metrics_z_df = compute_peer_zscores(metrics_df)
    trend_df = compute_monthly_trend(tables)
    review_queue_df = build_review_queue(findings_df)
    return dict(
        tables=tables,
        findings=findings_df,
        scores=scores_df,
        metrics=metrics_z_df,
        trend=trend_df,
        review_queue=review_queue_df,
    )


def build_review_queue(findings_df: pd.DataFrame) -> pd.DataFrame:
    """Flatten each finding's evidence list into individual review-queue rows,
    each inheriting the parent finding's rationale/severity so a supervisor can
    work a prioritized list of specific alerts/cases/audit rows."""
    if findings_df.empty:
        return pd.DataFrame(columns=["entity_id", "evidence_type", "evidence_id", "rule_name",
                                      "category", "severity", "rationale", "priority_score", "finding_id"])
    rows = []
    for _, f in findings_df.iterrows():
        ids = f["evidence_ids"][:200]  # cap per-finding to keep the queue usable
        for eid in ids:
            rows.append(dict(
                entity_id=f["entity_id"], evidence_type=f["evidence_type"], evidence_id=eid,
                rule_name=f["rule_name"], category=f["category"], severity=f["severity"],
                rationale=f["rationale"], priority_score=f["priority_score"], finding_id=f["finding_id"],
            ))
    df = pd.DataFrame(rows)
    return df.sort_values("priority_score", ascending=False).reset_index(drop=True)
