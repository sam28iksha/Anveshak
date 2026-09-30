"""Shared helpers: severity ranking, case enrichment, finding construction."""

import pandas as pd
import numpy as np

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
SEVERITY_ORDER = ["critical", "high", "medium", "low"]


def enrich_cases(tables: dict) -> pd.DataFrame:
    """Attach worst linked-alert severity, category, asset criticality, entity to each case."""
    cases = tables["cases"].copy()
    case_alerts = tables["case_alerts"]
    alerts = tables["alerts"][["alert_id", "asset_id", "severity", "category", "disposition", "escalated"]]
    assets = tables["assets"][["asset_id", "criticality"]].rename(columns={"criticality": "asset_criticality"})

    joined = case_alerts.merge(alerts, on="alert_id").merge(assets, on="asset_id")
    joined["severity_rank"] = joined["severity"].map(SEVERITY_RANK)

    # worst (highest severity_rank) alert per case represents the case's severity
    idx = joined.groupby("case_id")["severity_rank"].idxmax()
    primary = joined.loc[idx, ["case_id", "alert_id", "severity", "category", "disposition",
                               "escalated", "asset_criticality"]].rename(
        columns={"alert_id": "primary_alert_id", "severity": "case_severity"}
    )

    any_escalated = joined.groupby("case_id")["escalated"].max().rename("any_alert_escalated")

    cases = cases.merge(primary, on="case_id", how="left").merge(any_escalated, on="case_id", how="left")
    cases["duration_minutes"] = (cases["closed_at"] - cases["opened_at"]).dt.total_seconds() / 60.0
    cases["notes_len"] = cases["investigation_notes"].fillna("").str.len()
    return cases


def make_finding(entity_id, category, rule_code, rule_name, severity, rationale,
                  metric_value, threshold_used, evidence_type, evidence_ids, points=0.0):
    return dict(
        entity_id=entity_id,
        category=category,
        rule_code=rule_code,
        rule_name=rule_name,
        severity=severity,
        rationale=rationale,
        metric_value=metric_value,
        threshold_used=threshold_used,
        evidence_type=evidence_type,
        evidence_ids=list(evidence_ids),
        n_evidence=len(evidence_ids),
        points=round(points, 2),
        priority_score=round(SEVERITY_RANK.get(severity, 1) * 10 + min(9, len(evidence_ids) / 10), 2),
    )


def normalize_notes(text: str) -> str:
    if not text:
        return ""
    t = text.lower().strip()
    t = " ".join(t.split())
    return t


def zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std
