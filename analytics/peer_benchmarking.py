"""Peer benchmarking: entity vs. sector-peer metrics, for the comparison chart
and for feeding the EG5 / AS4 peer-deviation detectors. Peer group = same sector.
"""

import numpy as np
import pandas as pd

from analytics.common import enrich_cases

METRICS = [
    ("escalation_rate_critical", "Critical-alert escalation rate"),
    ("mean_closure_min_critical", "Mean closure time — critical (min)"),
    ("mean_closure_min_high", "Mean closure time — high (min)"),
    ("alerts_per_asset", "Alerts per asset"),
    ("case_to_alert_ratio", "Case-to-alert ratio"),
    ("audit_coverage_ratio", "Audit log coverage ratio (audit rows / case)"),
]


def compute_entity_metrics(tables: dict) -> pd.DataFrame:
    entities = tables["entities"][["entity_id", "sector"]].copy()
    alerts = tables["alerts"]
    assets = tables["assets"]
    cases = tables["cases"]
    audit = tables["audit_logs"]

    crit = alerts[(alerts["severity"] == "critical") & (alerts["disposition"] == "true_positive")]
    esc_rate = crit.groupby("entity_id")["escalated"].mean().rename("escalation_rate_critical")

    enriched = enrich_cases(tables)
    mean_close_crit = enriched[enriched["case_severity"] == "critical"].groupby("entity_id")["duration_minutes"].mean().rename("mean_closure_min_critical")
    mean_close_high = enriched[enriched["case_severity"] == "high"].groupby("entity_id")["duration_minutes"].mean().rename("mean_closure_min_high")

    n_assets = assets.groupby("entity_id").size().rename("n_assets")
    n_alerts = alerts.groupby("entity_id").size().rename("n_alerts")
    alerts_per_asset = (n_alerts / n_assets).rename("alerts_per_asset")

    n_cases = cases.groupby("entity_id").size().rename("n_cases")
    case_to_alert = (n_cases / n_alerts).rename("case_to_alert_ratio")

    n_audit = audit.groupby("entity_id").size().rename("n_audit")
    audit_coverage = (n_audit / n_cases).rename("audit_coverage_ratio")

    df = entities.set_index("entity_id")
    for s in [esc_rate, mean_close_crit, mean_close_high, alerts_per_asset, case_to_alert, audit_coverage]:
        df = df.join(s)
    df = df.reset_index().fillna(0)
    return df


def compute_peer_zscores(metrics_df: pd.DataFrame) -> pd.DataFrame:
    df = metrics_df.copy()
    metric_cols = [m[0] for m in METRICS]
    for col in metric_cols:
        df[f"{col}_z"] = df.groupby("sector")[col].transform(
            lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else 0.0
        )
        df[f"{col}_peer_median"] = df.groupby("sector")[col].transform("median")
    return df
