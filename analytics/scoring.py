"""Composite risk scoring: aggregates detector findings into a single, transparent
0-100 supervisory risk score per entity, plus a lightweight monthly trend proxy
for the Trend view.

Scoring is a straight sum of each finding's `points` (already computed by the
detector using the documented RULE_WEIGHTS table in detectors.py), capped at 100.
No hidden weighting, no ML — the score for any entity can be fully reconstructed
by summing the `points` column of that entity's rows in the findings table.
"""

import pandas as pd

from analytics.common import enrich_cases

CATEGORY_LABELS = {
    "execution_gap": "Execution Gaps",
    "negative_space": "Negative Space",
    "audit_supervision": "Audit Supervision",
}

BAND_THRESHOLDS = [(45, "Severe"), (18, "Moderate"), (0, "Clean")]


def band_for_score(score: float) -> str:
    for threshold, label in BAND_THRESHOLDS:
        if score >= threshold:
            return label
    return "Clean"


def compute_composite_scores(findings_df: pd.DataFrame, entities_df: pd.DataFrame) -> pd.DataFrame:
    base = entities_df[["entity_id", "name", "sector", "tier"]].copy()

    if findings_df.empty:
        base["total_score"] = 0.0
        for cat in CATEGORY_LABELS:
            base[f"{cat}_points"] = 0.0
        base["n_findings"] = 0
        base["band"] = "Clean"
        base["rank"] = base["total_score"].rank(ascending=False, method="min").astype(int)
        return base.sort_values("total_score", ascending=False).reset_index(drop=True)

    by_cat = findings_df.pivot_table(index="entity_id", columns="category", values="points",
                                      aggfunc="sum", fill_value=0.0)
    for cat in CATEGORY_LABELS:
        if cat not in by_cat.columns:
            by_cat[cat] = 0.0
    by_cat = by_cat.rename(columns={cat: f"{cat}_points" for cat in CATEGORY_LABELS})

    raw_total = findings_df.groupby("entity_id")["points"].sum().rename("raw_score")
    n_findings = findings_df.groupby("entity_id").size().rename("n_findings")

    df = base.merge(by_cat, on="entity_id", how="left").merge(raw_total, on="entity_id", how="left") \
        .merge(n_findings, on="entity_id", how="left")
    for cat in CATEGORY_LABELS:
        df[f"{cat}_points"] = df[f"{cat}_points"].fillna(0.0)
    df["raw_score"] = df["raw_score"].fillna(0.0)
    df["n_findings"] = df["n_findings"].fillna(0).astype(int)

    df["total_score"] = df["raw_score"].clip(upper=100).round(1)
    df["band"] = df["total_score"].map(band_for_score)
    df["rank"] = df["total_score"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("total_score", ascending=False).reset_index(drop=True)


def entity_score_breakdown(findings_df: pd.DataFrame, entity_id: str) -> pd.DataFrame:
    sub = findings_df[findings_df["entity_id"] == entity_id]
    return sub.sort_values("points", ascending=False)


def compute_monthly_trend(tables: dict) -> pd.DataFrame:
    """Lightweight monthly risk proxy (0-100) per entity, for the trend view.

    Recomputes three cheap, month-scoped indicators — fast-closure rate,
    no-escalation rate, and audit-unaccounted rate — and blends them with
    fixed weights (40/30/30). This is intentionally simpler than the full
    detector suite (which scores over the whole period) so it stays fast to
    recompute per month; it exists to show trajectory, not to replace the
    composite score.
    """
    cases = enrich_cases(tables)
    cases["month"] = cases["opened_at"].dt.to_period("M").astype(str)
    audit = tables["audit_logs"].copy()
    audited_case_ids = set(audit.loc[audit["action_type"] == "case_update", "target_id"].dropna())

    rows = []
    for (entity_id, month), grp in cases.groupby(["entity_id", "month"]):
        hi = grp[grp["case_severity"].isin(["critical", "high"])]
        fast_rate = 0.0
        if len(hi) > 0:
            fast_rate = ((hi["duration_minutes"] < 30) & (hi["notes_len"] < 10)).mean()

        crit_alerts_count = hi[hi["case_severity"] == "critical"].shape[0]
        no_esc_rate = 0.0
        if crit_alerts_count > 0:
            no_esc_rate = (hi[hi["case_severity"] == "critical"]["any_alert_escalated"].fillna(0) == 0).mean()

        unaccounted_rate = (~grp["case_id"].isin(audited_case_ids)).mean()

        proxy = 100 * (0.40 * fast_rate + 0.30 * no_esc_rate + 0.30 * unaccounted_rate)
        rows.append(dict(entity_id=entity_id, month=month, risk_proxy=round(proxy, 1),
                          n_cases=len(grp)))
    return pd.DataFrame(rows)
