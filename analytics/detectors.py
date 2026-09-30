"""Detection rules: execution gaps, negative space, audit supervision.

Each detector is an independent, composable function taking the loaded table
dict and returning a list of finding dicts (see common.make_finding). Findings
are entity-level: one finding per entity per rule, carrying the full evidence
list (raw alert_id/case_id/audit_id references) so the UI can show exactly
which records caused the flag.

Every numeric threshold used is either a documented constant below or a
statistic computed from the dataset itself (and is always echoed back in the
finding's `threshold_used` field) — nothing here is a black box.
"""

import numpy as np
import pandas as pd

from analytics.common import enrich_cases, make_finding, normalize_notes

# ---------------------------------------------------------------------------
# documented rule weights: (base_points, saturation_rate_or_count)
# base_points = points awarded when the rule is maximally triggered for an
# entity; for rate-based rules points scale linearly with how far the
# entity's rate is past a floor, saturating (capping) at `saturation`.
# ---------------------------------------------------------------------------
RULE_WEIGHTS = {
    "EG1_fast_closure_no_notes":        dict(base=20, saturation=0.40, floor=0.05),
    "EG2_critical_no_escalation":       dict(base=18, saturation=0.80, floor=0.40),
    "EG3_template_investigation":       dict(base=15, saturation=0.30, floor=0.05),
    "EG4_resolved_without_root_cause":  dict(base=12, saturation=0.70, floor=0.32),
    "EG5_escalation_rate_below_peer":   dict(base=15, saturation=1.00, floor=0.00),
    "EG6_low_alert_to_case_conversion": dict(base=10, saturation=0.95, floor=0.72),
    "NS1_telemetry_gap_asset":          dict(base=15, saturation=1.00, floor=0.00),
    "NS2_zero_escalations":             dict(base=20, saturation=1.00, floor=0.00),
    "NS3_missing_category":             dict(base=10, saturation=1.00, floor=0.00),
    "NS4_volume_flatline":              dict(base=12, saturation=1.00, floor=0.00),
    "AS1_unaccounted_activity":         dict(base=20, saturation=0.90, floor=0.35),
    "AS2_audit_timeline_gap":           dict(base=18, saturation=1.00, floor=0.00),
    "AS3_privileged_not_reviewed":      dict(base=15, saturation=0.50, floor=0.10),
    "AS4_low_audit_density_vs_peers":   dict(base=10, saturation=1.00, floor=0.00),
}


def _severity_from_rate(rate, cuts=(0.50, 0.25, 0.10)):
    if rate >= cuts[0]:
        return "critical"
    if rate >= cuts[1]:
        return "high"
    if rate >= cuts[2]:
        return "medium"
    return "low"


def _points_for_rate(rule_code, rate):
    w = RULE_WEIGHTS[rule_code]
    if rate <= w["floor"]:
        return 0.0
    scaled = (rate - w["floor"]) / max(1e-9, (w["saturation"] - w["floor"]))
    return w["base"] * min(1.0, max(0.0, scaled))


# ===========================================================================
# EXECUTION GAP DETECTORS
# ===========================================================================

def detect_fast_closure_no_notes(tables: dict) -> list:
    """EG1 — critical/high cases closed faster than a statistical floor, with no notes."""
    cases = enrich_cases(tables)
    hi = cases[cases["case_severity"].isin(["critical", "high"])].copy()

    findings = []
    thresholds = {}
    for sev in ["critical", "high"]:
        pool = hi.loc[hi["case_severity"] == sev, "duration_minutes"].dropna()
        if len(pool) < 20:
            thresholds[sev] = 30.0 if sev == "critical" else 45.0
        else:
            thresholds[sev] = float(min(30.0 if sev == "critical" else 45.0, np.percentile(pool, 5)))

    hi["threshold"] = hi["case_severity"].map(thresholds)
    flagged = hi[(hi["duration_minutes"] < hi["threshold"]) & (hi["notes_len"] < 10)]

    for entity_id, grp in hi.groupby("entity_id"):
        flg = flagged[flagged["entity_id"] == entity_id]
        rate = len(flg) / max(1, len(grp))
        if len(flg) == 0:
            continue
        pts = _points_for_rate("EG1_fast_closure_no_notes", rate)
        if pts <= 0:
            continue
        sev = _severity_from_rate(rate)
        findings.append(make_finding(
            entity_id=entity_id, category="execution_gap", rule_code="EG1_fast_closure_no_notes",
            rule_name="Critical/high alert closed abnormally fast with no investigation notes",
            severity=sev,
            rationale=(f"{len(flg)} of {len(grp)} critical/high cases ({rate:.0%}) were closed faster than "
                       f"the statistical closure-time floor for their severity (critical: "
                       f"{thresholds['critical']:.0f} min, high: {thresholds['high']:.0f} min), with fewer "
                       f"than 10 characters of investigation notes."),
            metric_value=round(rate, 4), threshold_used=f"critical<{thresholds['critical']:.0f}min, high<{thresholds['high']:.0f}min, notes<10 chars",
            evidence_type="case", evidence_ids=flg["case_id"].tolist(), points=pts,
        ))
    return findings


def detect_critical_no_escalation(tables: dict) -> list:
    """EG2 — critical alerts (true positive) closed without any escalation record."""
    alerts = tables["alerts"]
    crit_tp = alerts[(alerts["severity"] == "critical") & (alerts["disposition"] == "true_positive")
                      & alerts["closed_at"].notna()]
    findings = []
    for entity_id, grp in crit_tp.groupby("entity_id"):
        unescalated = grp[grp["escalated"] == 0]
        rate = len(unescalated) / max(1, len(grp))
        if len(unescalated) == 0:
            continue
        pts = _points_for_rate("EG2_critical_no_escalation", rate)
        if pts <= 0:
            continue
        sev = _severity_from_rate(rate)
        findings.append(make_finding(
            entity_id=entity_id, category="execution_gap", rule_code="EG2_critical_no_escalation",
            rule_name="Critical alert closed without any escalation",
            severity=sev,
            rationale=(f"{len(unescalated)} of {len(grp)} confirmed critical alerts ({rate:.0%}) were closed "
                       f"with no escalation record anywhere in the escalations log."),
            metric_value=round(rate, 4), threshold_used="0 escalations on a confirmed critical alert",
            evidence_type="alert", evidence_ids=unescalated["alert_id"].tolist(), points=pts,
        ))
    return findings


def detect_template_investigations(tables: dict) -> list:
    """EG3 — near-duplicate investigation notes reused templated text across cases."""
    cases = tables["cases"].copy()
    cases = cases[cases["investigation_notes"].fillna("").str.len() >= 10]
    cases["norm"] = cases["investigation_notes"].map(normalize_notes)

    findings = []
    for entity_id, grp in cases.groupby("entity_id"):
        dup_counts = grp.groupby("norm")["case_id"].apply(list)
        dup_groups = dup_counts[dup_counts.map(len) >= 3]
        dup_cases = [cid for lst in dup_groups for cid in lst]
        rate = len(dup_cases) / max(1, len(grp))
        if len(dup_cases) == 0:
            continue
        pts = _points_for_rate("EG3_template_investigation", rate)
        if pts <= 0:
            continue
        sev = _severity_from_rate(rate, cuts=(0.30, 0.15, 0.05))
        findings.append(make_finding(
            entity_id=entity_id, category="execution_gap", rule_code="EG3_template_investigation",
            rule_name="Template / copy-paste investigation notes across cases",
            severity=sev,
            rationale=(f"{len(dup_cases)} of {len(grp)} cases ({rate:.0%}) share near-identical investigation "
                       f"text with at least 2 other cases (>=3-way duplicate text groups), suggesting "
                       f"copy-paste rather than individual investigation."),
            metric_value=round(rate, 4), threshold_used=">=3 cases sharing normalized note text",
            evidence_type="case", evidence_ids=dup_cases, points=pts,
        ))
    return findings


def detect_resolved_without_root_cause(tables: dict) -> list:
    """EG4 — high/critical alerts marked resolved without root_cause_identified."""
    cases = enrich_cases(tables)
    hi = cases[cases["case_severity"].isin(["critical", "high"]) & cases["closed_at"].notna()]
    findings = []
    for entity_id, grp in hi.groupby("entity_id"):
        no_rc = grp[grp["root_cause_identified"] == 0]
        rate = len(no_rc) / max(1, len(grp))
        if len(no_rc) == 0:
            continue
        pts = _points_for_rate("EG4_resolved_without_root_cause", rate)
        if pts <= 0:
            continue
        sev = _severity_from_rate(rate, cuts=(0.60, 0.40, 0.20))
        findings.append(make_finding(
            entity_id=entity_id, category="execution_gap", rule_code="EG4_resolved_without_root_cause",
            rule_name="High/critical case resolved without root cause identified",
            severity=sev,
            rationale=(f"{len(no_rc)} of {len(grp)} closed high/critical cases ({rate:.0%}) were resolved "
                       f"without root_cause_identified being set."),
            metric_value=round(rate, 4), threshold_used="root_cause_identified = false on a closed high/critical case",
            evidence_type="case", evidence_ids=no_rc["case_id"].tolist(), points=pts,
        ))
    return findings


def detect_escalation_rate_below_peer(tables: dict) -> list:
    """EG5 — critical-alert escalation rate significantly below sector peer median."""
    alerts = tables["alerts"]
    entities = tables["entities"]
    crit = alerts[(alerts["severity"] == "critical") & (alerts["disposition"] == "true_positive")]
    rate_by_entity = crit.groupby("entity_id")["escalated"].mean().rename("esc_rate")
    counts = crit.groupby("entity_id")["escalated"].size().rename("n_critical")
    df = rate_by_entity.to_frame().join(counts).reset_index().merge(entities[["entity_id", "sector"]], on="entity_id")

    findings = []
    for sector, grp in df.groupby("sector"):
        median = grp["esc_rate"].median()
        std = grp["esc_rate"].std(ddof=0)
        for _, row in grp.iterrows():
            if row["n_critical"] < 5:
                continue
            deviation = (median - row["esc_rate"]) / std if std > 0 else 0
            if row["esc_rate"] >= median - 1.5 * std and not (deviation > 1.5):
                continue
            gap = max(0.0, median - row["esc_rate"])
            pts = _points_for_rate("EG5_escalation_rate_below_peer", min(1.0, gap / max(0.01, median)))
            if pts <= 0:
                continue
            sev = "critical" if row["esc_rate"] < median * 0.25 else ("high" if row["esc_rate"] < median * 0.5 else "medium")
            evidence_ids = crit[(crit["entity_id"] == row["entity_id"]) & (crit["escalated"] == 0)]["alert_id"].tolist()
            findings.append(make_finding(
                entity_id=row["entity_id"], category="execution_gap", rule_code="EG5_escalation_rate_below_peer",
                rule_name="Critical-alert escalation rate far below sector peer median",
                severity=sev,
                rationale=(f"Critical-alert escalation rate is {row['esc_rate']:.0%}, vs. a {sector} sector peer "
                           f"median of {median:.0%} ({deviation:.1f} std devs below peer mean)."),
                metric_value=round(row["esc_rate"], 4), threshold_used=f"sector median {median:.0%}, flagged at >1.5 std dev below",
                evidence_type="alert", evidence_ids=evidence_ids, points=pts,
            ))
    return findings


def detect_low_alert_to_case_conversion(tables: dict) -> list:
    """EG6 — high/critical alerts acknowledged but rarely turned into a formal case."""
    alerts = tables["alerts"]
    case_alerts = tables["case_alerts"]
    hi = alerts[alerts["severity"].isin(["critical", "high"]) & alerts["acknowledged_at"].notna()].copy()
    cased_alert_ids = set(case_alerts["alert_id"])
    hi["has_case"] = hi["alert_id"].isin(cased_alert_ids)

    findings = []
    for entity_id, grp in hi.groupby("entity_id"):
        no_case = grp[~grp["has_case"]]
        rate = len(no_case) / max(1, len(grp))
        if len(no_case) == 0:
            continue
        pts = _points_for_rate("EG6_low_alert_to_case_conversion", rate)
        if pts <= 0:
            continue
        sev = _severity_from_rate(rate, cuts=(0.70, 0.50, 0.30))
        findings.append(make_finding(
            entity_id=entity_id, category="execution_gap", rule_code="EG6_low_alert_to_case_conversion",
            rule_name="High/critical alerts rarely converted into a formal case",
            severity=sev,
            rationale=(f"{len(no_case)} of {len(grp)} acknowledged high/critical alerts ({rate:.0%}) never "
                       f"became a case — no investigation record exists."),
            metric_value=round(rate, 4), threshold_used="acknowledged high/critical alert with zero linked cases",
            evidence_type="alert", evidence_ids=no_case["alert_id"].tolist(), points=pts,
        ))
    return findings


# ===========================================================================
# NEGATIVE SPACE DETECTORS
# ===========================================================================

def detect_telemetry_gap_asset(tables: dict) -> list:
    """NS1 — critical-tier assets with alert volume in the bottom percentile of peers."""
    assets = tables["assets"]
    alerts = tables["alerts"]
    crit_assets = assets[assets["criticality"] == "critical"]
    counts = alerts.groupby("asset_id").size().rename("n_alerts")
    df = crit_assets.merge(counts, on="asset_id", how="left").fillna({"n_alerts": 0})

    findings = []
    for entity_id, grp in df.groupby("entity_id"):
        if len(grp) < 3:
            continue
        p10 = np.percentile(grp["n_alerts"], 10)
        peer_median = grp["n_alerts"].median()
        gap_assets = grp[(grp["n_alerts"] <= max(2, p10)) & (grp["n_alerts"] < 0.1 * peer_median)]
        if len(gap_assets) == 0:
            continue
        pts = _points_for_rate("NS1_telemetry_gap_asset", 1.0)
        for _, row in gap_assets.iterrows():
            findings.append(make_finding(
                entity_id=entity_id, category="negative_space", rule_code="NS1_telemetry_gap_asset",
                rule_name="Critical asset with near-zero alert volume (telemetry gap)",
                severity="critical",
                rationale=(f"Critical asset '{row['name']}' generated {int(row['n_alerts'])} alerts over the "
                           f"whole period vs. a peer median of {peer_median:.0f} among this entity's other "
                           f"critical assets — likely a monitoring blind spot."),
                metric_value=int(row["n_alerts"]), threshold_used=f"<=10th pct of peer critical-asset volume ({p10:.1f}) and <10% of peer median",
                evidence_type="asset", evidence_ids=[row["asset_id"]], points=pts / max(1, len(gap_assets)),
            ))
    return findings


def detect_zero_escalations(tables: dict) -> list:
    """NS2 — entity with zero escalations across the entire period despite critical alerts."""
    alerts = tables["alerts"]
    escalations = tables["escalations"]
    cases = tables["cases"]
    entities = tables["entities"]

    esc_entities = set(cases.merge(escalations, on="case_id")["entity_id"])
    crit_counts = alerts[alerts["severity"] == "critical"].groupby("entity_id").size()

    findings = []
    for entity_id in entities["entity_id"]:
        n_crit = crit_counts.get(entity_id, 0)
        if n_crit == 0 or entity_id in esc_entities:
            continue
        crit_ids = alerts[(alerts["entity_id"] == entity_id) & (alerts["severity"] == "critical")]["alert_id"].tolist()
        pts = _points_for_rate("NS2_zero_escalations", 1.0)
        findings.append(make_finding(
            entity_id=entity_id, category="negative_space", rule_code="NS2_zero_escalations",
            rule_name="Zero escalations despite critical alerts",
            severity="critical",
            rationale=(f"{n_crit} critical alerts were recorded for this entity, but the escalations log has "
                       f"zero entries for the entire {len(crit_ids)}-critical-alert period."),
            metric_value=0, threshold_used="0 escalations with >=1 critical alert present",
            evidence_type="alert", evidence_ids=crit_ids, points=pts,
        ))
    return findings


def detect_missing_category(tables: dict) -> list:
    """NS3 — alert category present across sector peers but entirely absent for this entity."""
    alerts = tables["alerts"]
    entities = tables["entities"]
    df = alerts.merge(entities[["entity_id", "sector"]], on="entity_id")

    findings = []
    for sector, sgrp in df.groupby("sector"):
        sector_entities = entities[entities["sector"] == sector]["entity_id"].tolist()
        all_categories = set(sgrp["category"].unique())
        for entity_id in sector_entities:
            present = set(sgrp[sgrp["entity_id"] == entity_id]["category"].unique())
            missing = all_categories - present
            # only flag a category if it's common across most OTHER peers (not a one-off)
            for cat in missing:
                peers_with_cat = sgrp[(sgrp["category"] == cat) & (sgrp["entity_id"] != entity_id)]["entity_id"].nunique()
                if peers_with_cat >= max(2, len(sector_entities) - 1):
                    evidence = df[(df["category"] == cat) & (df["entity_id"] != entity_id) & (df["sector"] == sector)]["alert_id"].tolist()[:20]
                    pts = _points_for_rate("NS3_missing_category", 1.0)
                    findings.append(make_finding(
                        entity_id=entity_id, category="negative_space", rule_code="NS3_missing_category",
                        rule_name="Expected alert category never observed",
                        severity="high",
                        rationale=(f"'{cat}' alerts appear for {peers_with_cat} of {len(sector_entities)-1} other "
                                   f"{sector} peers but never once for this entity across the full period."),
                        metric_value=0, threshold_used=f"category present in >={max(2, len(sector_entities)-1)} sector peers",
                        evidence_type="alert", evidence_ids=evidence, points=pts,
                    ))
    return findings


def detect_volume_flatline(tables: dict) -> list:
    """NS4 — sudden drop / flatline in weekly alert volume (possible monitoring outage)."""
    alerts = tables["alerts"].copy()
    alerts["week"] = alerts["created_at"].dt.to_period("W")

    findings = []
    for entity_id, grp in alerts.groupby("entity_id"):
        weekly = grp.groupby("week").size()
        full_index = pd.period_range(weekly.index.min(), weekly.index.max(), freq="W")
        weekly = weekly.reindex(full_index, fill_value=0)
        baseline = weekly.median()
        if baseline == 0:
            continue
        low_weeks = weekly[weekly < 0.15 * baseline]
        # collapse consecutive low weeks into runs of >=3
        if low_weeks.empty:
            continue
        weeks_sorted = sorted(low_weeks.index)
        runs, cur = [], [weeks_sorted[0]]
        for w in weeks_sorted[1:]:
            if (w.start_time - cur[-1].start_time).days <= 8:
                cur.append(w)
            else:
                runs.append(cur)
                cur = [w]
        runs.append(cur)
        for run in runs:
            if len(run) < 3:
                continue
            start, end = run[0].start_time, run[-1].end_time
            evidence = grp[(grp["created_at"] >= start) & (grp["created_at"] <= end)]["alert_id"].tolist()
            avg_in_window = weekly.loc[run].mean()
            pts = _points_for_rate("NS4_volume_flatline", 1.0)
            findings.append(make_finding(
                entity_id=entity_id, category="negative_space", rule_code="NS4_volume_flatline",
                rule_name="Multi-week flatline in alert volume (possible monitoring outage)",
                severity="high",
                rationale=(f"Weekly alert volume dropped to {avg_in_window:.1f}/week (vs. a {baseline:.0f}/week "
                           f"baseline) for {len(run)} consecutive weeks starting {start.date()} — consistent "
                           f"with a monitoring blind spot rather than genuinely quiet operations."),
                metric_value=round(avg_in_window, 1), threshold_used=f"<15% of {baseline:.0f}/week baseline for >=3 consecutive weeks",
                evidence_type="alert", evidence_ids=evidence, points=pts,
            ))
    return findings


# ===========================================================================
# AUDIT LOG SUPERVISION DETECTORS
# ===========================================================================

def detect_unaccounted_activity(tables: dict) -> list:
    """AS1 — case/escalation activity with no matching audit_logs entry."""
    cases = tables["cases"]
    audit = tables["audit_logs"]
    audited_case_ids = set(audit.loc[audit["action_type"] == "case_update", "target_id"].dropna())

    findings = []
    for entity_id, grp in cases.groupby("entity_id"):
        unaccounted = grp[~grp["case_id"].isin(audited_case_ids)]
        rate = len(unaccounted) / max(1, len(grp))
        if len(unaccounted) == 0:
            continue
        pts = _points_for_rate("AS1_unaccounted_activity", rate)
        if pts <= 0:
            continue
        sev = _severity_from_rate(rate, cuts=(0.85, 0.50, 0.20))
        findings.append(make_finding(
            entity_id=entity_id, category="audit_supervision", rule_code="AS1_unaccounted_activity",
            rule_name="Case activity with no matching audit log entry",
            severity=sev,
            rationale=(f"{len(unaccounted)} of {len(grp)} cases ({rate:.0%}) have no corresponding audit_logs "
                       f"entry anywhere — there is no record of who performed this work."),
            metric_value=round(rate, 4), threshold_used="no audit_logs row with target_id = this case_id",
            evidence_type="case", evidence_ids=unaccounted["case_id"].tolist(), points=pts,
        ))
    return findings


def detect_audit_timeline_gap(tables: dict) -> list:
    """AS2 — a period with expected alert/case activity but zero audit_logs rows."""
    alerts = tables["alerts"].copy()
    audit = tables["audit_logs"].copy()
    alerts["week"] = alerts["created_at"].dt.to_period("W")
    audit["week"] = audit["timestamp"].dt.to_period("W")

    findings = []
    for entity_id, agrp in alerts.groupby("entity_id"):
        if agrp.empty:
            continue
        full_index = pd.period_range(agrp["week"].min(), agrp["week"].max(), freq="W")
        activity = agrp.groupby("week").size().reindex(full_index, fill_value=0)
        audit_grp = audit[audit["entity_id"] == entity_id]
        audit_weekly = audit_grp.groupby("week").size().reindex(full_index, fill_value=0)

        if audit_weekly.sum() == 0:
            continue  # AS1/AS handled implicitly; total absence isn't a "gap", it's total absence

        gap_weeks = activity[(activity > activity.median() * 0.3) & (audit_weekly == 0)]
        if gap_weeks.empty:
            continue
        weeks_sorted = sorted(gap_weeks.index)
        runs, cur = [], [weeks_sorted[0]]
        for w in weeks_sorted[1:]:
            if (w.start_time - cur[-1].start_time).days <= 8:
                cur.append(w)
            else:
                runs.append(cur)
                cur = [w]
        runs.append(cur)
        for run in runs:
            if len(run) < 3:
                continue
            start, end = run[0].start_time, run[-1].end_time
            evidence = agrp[(agrp["created_at"] >= start) & (agrp["created_at"] <= end)]["alert_id"].tolist()
            pts = _points_for_rate("AS2_audit_timeline_gap", 1.0)
            findings.append(make_finding(
                entity_id=entity_id, category="audit_supervision", rule_code="AS2_audit_timeline_gap",
                rule_name="Gap in the audit log timeline during active operations",
                severity="critical",
                rationale=(f"{len(run)} consecutive weeks starting {start.date()} have zero audit_logs entries "
                           f"even though {activity.loc[run].sum():.0f} alerts were generated in that window — "
                           f"oversight logging appears to have been switched off."),
                metric_value=len(run), threshold_used=">=3 consecutive weeks of 0 audit rows during active alert volume",
                evidence_type="alert", evidence_ids=evidence, points=pts,
            ))
    return findings


def detect_privileged_not_reviewed(tables: dict) -> list:
    """AS3 — privileged actions (config_change, access_grant) never marked reviewed_by_supervisor."""
    audit = tables["audit_logs"]
    priv = audit[audit["action_type"].isin(["config_change", "access_grant"])]

    findings = []
    for entity_id, grp in priv.groupby("entity_id"):
        unreviewed = grp[grp["reviewed_by_supervisor"] == 0]
        rate = len(unreviewed) / max(1, len(grp))
        if len(unreviewed) == 0:
            continue
        pts = _points_for_rate("AS3_privileged_not_reviewed", rate)
        if pts <= 0:
            continue
        sev = _severity_from_rate(rate, cuts=(0.80, 0.50, 0.20))
        findings.append(make_finding(
            entity_id=entity_id, category="audit_supervision", rule_code="AS3_privileged_not_reviewed",
            rule_name="Privileged action never reviewed by a supervisor",
            severity=sev,
            rationale=(f"{len(unreviewed)} of {len(grp)} privileged actions ({rate:.0%}) — config changes and "
                       f"access grants — were never marked reviewed_by_supervisor. The oversight control exists "
                       f"on paper but isn't being used."),
            metric_value=round(rate, 4), threshold_used="reviewed_by_supervisor = false on config_change/access_grant",
            evidence_type="audit", evidence_ids=unreviewed["audit_id"].tolist(), points=pts,
        ))
    return findings


def detect_low_audit_density_vs_peers(tables: dict) -> list:
    """AS4 (optional) — ratio of audit-logged actions to alert/case volume, benchmarked against sector peers."""
    audit = tables["audit_logs"]
    cases = tables["cases"]
    entities = tables["entities"]

    audit_counts = audit.groupby("entity_id").size().rename("n_audit")
    case_counts = cases.groupby("entity_id").size().rename("n_cases")
    df = entities[["entity_id", "sector"]].merge(audit_counts, on="entity_id", how="left") \
        .merge(case_counts, on="entity_id", how="left").fillna(0)
    df["density"] = df["n_audit"] / df["n_cases"].replace(0, np.nan)
    df["density"] = df["density"].fillna(0)

    findings = []
    for sector, grp in df.groupby("sector"):
        median = grp["density"].median()
        std = grp["density"].std(ddof=0)
        for _, row in grp.iterrows():
            if std == 0:
                continue
            deviation = (median - row["density"]) / std
            if deviation <= 1.5:
                continue
            gap = max(0.0, median - row["density"])
            pts = _points_for_rate("AS4_low_audit_density_vs_peers", min(1.0, gap / max(0.1, median)))
            if pts <= 0:
                continue
            sev = "high" if deviation > 2.5 else "medium"
            findings.append(make_finding(
                entity_id=row["entity_id"], category="audit_supervision", rule_code="AS4_low_audit_density_vs_peers",
                rule_name="Audit-log density far below sector peers",
                severity=sev,
                rationale=(f"Audit log entries per case are {row['density']:.2f}, vs. a {sector} sector peer "
                           f"median of {median:.2f} ({deviation:.1f} std devs below peer mean) — this entity "
                           f"reports SOC activity with disproportionately little logged oversight."),
                metric_value=round(row["density"], 3), threshold_used=f"sector median {median:.2f}, flagged at >1.5 std dev below",
                evidence_type="audit", evidence_ids=[], points=pts,
            ))
    return findings


ALL_DETECTORS = [
    detect_fast_closure_no_notes,
    detect_critical_no_escalation,
    detect_template_investigations,
    detect_resolved_without_root_cause,
    detect_escalation_rate_below_peer,
    detect_low_alert_to_case_conversion,
    detect_telemetry_gap_asset,
    detect_zero_escalations,
    detect_missing_category,
    detect_volume_flatline,
    detect_unaccounted_activity,
    detect_audit_timeline_gap,
    detect_privileged_not_reviewed,
    detect_low_audit_density_vs_peers,
]


def run_all_detectors(tables: dict) -> pd.DataFrame:
    rows = []
    for fn in ALL_DETECTORS:
        rows.extend(fn(tables))
    if not rows:
        return pd.DataFrame(columns=["entity_id", "category", "rule_code", "rule_name", "severity",
                                      "rationale", "metric_value", "threshold_used", "evidence_type",
                                      "evidence_ids", "n_evidence", "points", "priority_score"])
    df = pd.DataFrame(rows)
    df.insert(0, "finding_id", [f"FND-{i+1:05d}" for i in range(len(df))])
    return df
