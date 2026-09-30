"""
Anveshak — SAT-SA synthetic SOC data generator.

Generates a multi-entity, multi-sector SOC alert/case/escalation/audit-log dataset
with DELIBERATELY INJECTED failure patterns so the detection engine in analytics/
has something real to catch. Nothing here calls the network — it's pure local
random generation seeded for reproducibility.

Run:  python data_generator.py
Output: data/anveshak.db (SQLite), data/injected_issues.json (ground-truth seed sheet)
"""

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "anveshak.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
ISSUES_PATH = BASE_DIR / "data" / "injected_issues.json"

PERIOD_START = datetime(2024, 10, 1)
PERIOD_END = datetime(2025, 9, 30)
PERIOD_DAYS = (PERIOD_END - PERIOD_START).days

# ---------------------------------------------------------------------------
# Entity roster — this IS the ground truth for what the detection engine
# should find. category: bad / borderline / good.
# ---------------------------------------------------------------------------

ENTITIES = [
    dict(entity_id="PWR-01", name="Grid Power Transmission Co.", sector="Power", tier="Tier-1",
         category="bad",
         issues=["fast_close_no_notes", "no_escalation", "template_notes",
                 "telemetry_gap_asset", "audit_no_logs"]),
    dict(entity_id="PWR-02", name="Solaris Renewable Power Ltd.", sector="Power", tier="Tier-2",
         category="good", issues=[]),
    dict(entity_id="PWR-03", name="Continental Power Distribution", sector="Power", tier="Tier-1",
         category="good", issues=[]),
    dict(entity_id="PWR-04", name="Highland Power Utilities", sector="Power", tier="Tier-2",
         category="borderline",
         issues=["low_escalation_rate", "audit_gap_window", "volume_flatline"]),

    dict(entity_id="BNK-01", name="Meridian National Bank", sector="Banking", tier="Tier-1",
         category="bad",
         issues=["low_alert_volume", "no_escalation", "audit_gap_window"]),
    dict(entity_id="BNK-02", name="Coastal Trust Bank", sector="Banking", tier="Tier-1",
         category="bad",
         issues=["fast_close_no_notes", "template_notes", "audit_no_logs"]),
    dict(entity_id="BNK-03", name="Zenith Cooperative Bank", sector="Banking", tier="Tier-2",
         category="good", issues=[]),
    dict(entity_id="BNK-04", name="Unity Regional Bank", sector="Banking", tier="Tier-2",
         category="good", issues=[]),

    dict(entity_id="TEL-01", name="Airwave Telecom Networks", sector="Telecom", tier="Tier-1",
         category="bad",
         issues=["missing_category", "no_root_cause", "audit_no_logs"]),
    dict(entity_id="TEL-02", name="Nexline Communications", sector="Telecom", tier="Tier-2",
         category="borderline",
         issues=["low_escalation_rate", "low_conversion_rate", "audit_privileged_not_reviewed"]),
    dict(entity_id="TEL-03", name="Skyline Mobile Services", sector="Telecom", tier="Tier-2",
         category="borderline",
         issues=["telemetry_gap_asset", "audit_privileged_not_reviewed"]),
    dict(entity_id="TEL-04", name="Horizon Telecom Ltd.", sector="Telecom", tier="Tier-1",
         category="good", issues=[]),
]

ISSUE_DESCRIPTIONS = {
    "fast_close_no_notes": "Critical/high alerts closed in under 15 minutes with no investigation notes.",
    "no_escalation": "Zero escalations recorded across the entire period despite critical alerts.",
    "template_notes": "Investigation notes are near-identical templated text copy-pasted across cases.",
    "telemetry_gap_asset": "A critical-tier asset generates almost zero alerts (monitoring/telemetry gap).",
    "low_alert_volume": "Overall alert volume ~90% below sector peers with no plausible operational reason.",
    "low_escalation_rate": "Escalation rate for critical alerts well below peer median.",
    "audit_no_logs": "Alert/case activity exists with NO corresponding audit_logs entries at all.",
    "audit_gap_window": "A 3-4 week window with zero audit log entries despite alert/case activity continuing.",
    "audit_privileged_not_reviewed": "Privileged actions (config_change/access_grant) never marked reviewed_by_supervisor.",
    "missing_category": "An alert category common across sector peers (lateral_movement) never appears.",
    "no_root_cause": "High/critical alerts marked resolved without root_cause_identified.",
    "volume_flatline": "A multi-week flatline/drop in alert volume suggesting a monitoring outage.",
    "low_conversion_rate": "High/critical alerts acknowledged but rarely converted into a formal case.",
}

SECTOR_ASSET_TYPES = {
    "Power": ["SCADA-Controller", "RTU", "Substation-Gateway", "Historian-Server",
              "EMS-Workstation", "Firewall", "Domain-Controller", "HMI-Terminal"],
    "Banking": ["Core-Banking-Server", "ATM-Switch", "Payment-Gateway", "Card-Processing-Server",
                "Firewall", "Domain-Controller", "Web-Application-Server", "Database-Server"],
    "Telecom": ["BSC", "Core-Router", "OSS-Server", "Billing-System",
                "HLR-Server", "Firewall", "Domain-Controller", "Network-Management-Server"],
}

CRITICALITY_WEIGHTS = [("critical", 0.15), ("high", 0.30), ("medium", 0.35), ("low", 0.20)]

CATEGORIES = ["brute_force", "malware", "phishing", "lateral_movement", "data_exfiltration",
              "privilege_escalation", "dos_attempt", "unauthorized_access", "policy_violation",
              "reconnaissance", "ransomware_indicator", "c2_communication", "insider_threat",
              "misconfiguration"]

SEVERITIES = ["critical", "high", "medium", "low"]

ESCALATION_TARGETS = ["SOC Manager", "CISO", "Sector-CERT", "NCIIPC Liaison", "Incident Response Lead"]

FIRST_NAMES = ["Aditi", "Rohan", "Priya", "Vikram", "Ananya", "Karan", "Meera", "Arjun", "Divya",
               "Sanjay", "Neha", "Rahul", "Pooja", "Amit", "Kavya", "Suresh", "Ritu", "Manoj",
               "Shreya", "Deepak", "Nisha", "Vivek", "Anjali", "Rajesh"]
LAST_NAMES = ["Sharma", "Verma", "Iyer", "Patel", "Nair", "Gupta", "Reddy", "Menon", "Kapoor",
              "Chatterjee", "Rao", "Joshi", "Malhotra", "Bhatt", "Krishnan"]


def fake_name(rng):
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def weighted_choice(rng, weighted_list):
    items, weights = zip(*weighted_list)
    return rng.choices(items, weights=weights, k=1)[0]


def rand_id(prefix, n, width=6):
    return f"{prefix}-{str(n).zfill(width)}"


def clamp_dt(dt):
    if dt < PERIOD_START:
        return PERIOD_START
    if dt > PERIOD_END:
        return PERIOD_END
    return dt


# ---------------------------------------------------------------------------
# Investigation note text generation
# ---------------------------------------------------------------------------

NOTE_OPENERS = [
    "Reviewed alert triggered on {asset} relating to {category}.",
    "Investigated {category} activity flagged against {asset}.",
    "Analyst triage initiated for {category} event on {asset}.",
]
NOTE_MIDDLES = [
    "Correlated with recent traffic logs and endpoint telemetry; no additional indicators found beyond the initial trigger.",
    "Cross-checked against threat intel feed and prior incident history for the asset; pattern consistent with known baseline noise.",
    "Reviewed asset configuration and recent change history; identified a plausible benign trigger cause.",
    "Escalated internally for a second review before disposition was finalized; consulted with asset owner on operational context.",
    "Traced source IP and session details; activity consistent with authorized maintenance window.",
]
NOTE_CLOSERS = [
    "Disposition set to {disposition} based on above findings.",
    "Closed as {disposition} after confirming with asset owner.",
    "Marked {disposition}; remediation action recorded where applicable.",
]

TEMPLATE_NOTE = ("Alert reviewed. Checked logs. No further action required. Closing as {disposition}.")


def generate_notes(rng, asset_name, category, disposition, template=False):
    if template:
        return TEMPLATE_NOTE.format(disposition=disposition)
    opener = rng.choice(NOTE_OPENERS).format(asset=asset_name, category=category.replace("_", " "))
    middle = rng.choice(NOTE_MIDDLES)
    closer = rng.choice(NOTE_CLOSERS).format(disposition=disposition.replace("_", " "))
    return f"{opener} {middle} {closer}"


# ---------------------------------------------------------------------------
# Generation state (in-memory row lists, bulk-inserted at the end)
# ---------------------------------------------------------------------------

assets_rows = []
alerts_rows = []
cases_rows = []
case_alerts_rows = []
escalations_rows = []
audit_rows = []

_counters = dict(asset=0, alert=0, case=0, esc=0, audit=0)
GAP_WINDOWS = {}  # entity_id -> (start, end) for audit_gap_window entities


def next_id(kind, prefix):
    _counters[kind] += 1
    return rand_id(prefix, _counters[kind])


def gen_assets(entity):
    rng = random.Random(f"{SEED}-assets-{entity['entity_id']}")
    n_assets = rng.randint(18, 35)
    types = SECTOR_ASSET_TYPES[entity["sector"]]
    out = []
    for i in range(n_assets):
        criticality = weighted_choice(rng, CRITICALITY_WEIGHTS)
        atype = rng.choice(types)
        asset_id = next_id("asset", "AST")
        name = f"{atype}-{entity['entity_id']}-{i+1:02d}"
        row = dict(asset_id=asset_id, entity_id=entity["entity_id"], name=name,
                   criticality=criticality, asset_type=atype)
        assets_rows.append(row)
        out.append(row)
    return out


def closure_minutes_normal(rng, severity):
    # realistic-ish closure time distributions, in minutes
    base = {"critical": (180, 90), "high": (360, 180), "medium": (1440, 600), "low": (2880, 1200)}
    mean, sd = base[severity]
    return max(5, rng.gauss(mean, sd))


def gen_alerts_for_entity(entity, entity_assets):
    rng = random.Random(f"{SEED}-alerts-{entity['entity_id']}")
    issues = set(entity["issues"])

    # ---- target volume ----
    base_target = rng.randint(1700, 2500)
    if "low_alert_volume" in issues:
        base_target = int(base_target * 0.10)  # ~90% below peers

    exclude_categories = set()
    if "missing_category" in issues:
        exclude_categories.add("lateral_movement")
    local_categories = [c for c in CATEGORIES if c not in exclude_categories]

    # pick telemetry-gap asset: a critical asset that will get near-zero alerts
    gap_asset_id = None
    if "telemetry_gap_asset" in issues:
        criticals = [a for a in entity_assets if a["criticality"] == "critical"]
        if criticals:
            gap_asset_id = rng.choice(criticals)["asset_id"]

    # weight assets by criticality for alert volume assignment
    weight_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    weighted_assets = []
    for a in entity_assets:
        w = weight_map[a["criticality"]]
        if a["asset_id"] == gap_asset_id:
            w = 0.02  # near-zero
        weighted_assets.append((a, w))

    # flatline / monitoring outage window
    flatline_window = None
    if "volume_flatline" in issues:
        gap_start_day = rng.randint(60, PERIOD_DAYS - 60)
        gap_len = rng.randint(21, 28)
        flatline_window = (PERIOD_START + timedelta(days=gap_start_day),
                            PERIOD_START + timedelta(days=gap_start_day + gap_len))

    severity_weights_by_crit = {
        "critical": [("critical", 0.30), ("high", 0.35), ("medium", 0.25), ("low", 0.10)],
        "high": [("critical", 0.15), ("high", 0.35), ("medium", 0.35), ("low", 0.15)],
        "medium": [("critical", 0.05), ("high", 0.20), ("medium", 0.45), ("low", 0.30)],
        "low": [("critical", 0.02), ("high", 0.10), ("medium", 0.38), ("low", 0.50)],
    }

    entity_alerts = []
    assets_pool, weights_pool = zip(*weighted_assets)

    n = base_target
    # ensure the missing-category entity still has *some* peer-typical categories
    for i in range(n):
        asset = rng.choices(assets_pool, weights=weights_pool, k=1)[0]
        severity = weighted_choice(rng, severity_weights_by_crit[asset["criticality"]])
        category = rng.choice(local_categories)

        day_offset = rng.randint(0, PERIOD_DAYS)
        created_at = PERIOD_START + timedelta(days=day_offset, hours=rng.randint(0, 23),
                                               minutes=rng.randint(0, 59))
        if flatline_window and flatline_window[0] <= created_at <= flatline_window[1]:
            if rng.random() < 0.92:
                continue  # suppress most alerts in the outage window

        disposition_weights = [("true_positive", 0.22), ("false_positive", 0.40),
                                ("benign", 0.28), ("duplicate", 0.10)]
        if severity in ("critical", "high"):
            disposition_weights = [("true_positive", 0.38), ("false_positive", 0.30),
                                    ("benign", 0.22), ("duplicate", 0.10)]
        disposition = weighted_choice(rng, disposition_weights)

        # acknowledgement
        ack_delay_min = max(1, rng.gauss(45, 30))
        acknowledged_at = created_at + timedelta(minutes=ack_delay_min)
        if acknowledged_at > PERIOD_END + timedelta(days=5):
            acknowledged_at = created_at + timedelta(minutes=5)

        # closure timing
        if "fast_close_no_notes" in issues and severity in ("critical", "high") and rng.random() < 0.75:
            close_delay_min = rng.uniform(1, 14)
        else:
            close_delay_min = closure_minutes_normal(rng, severity)
        closed_at = acknowledged_at + timedelta(minutes=close_delay_min)

        # escalation flag (entity-level escalation propensity)
        escalated = False
        if severity in ("critical", "high") and disposition == "true_positive":
            if "no_escalation" in issues:
                escalated = False
            elif "low_escalation_rate" in issues:
                escalated = rng.random() < 0.08
            else:
                escalated = rng.random() < (0.70 if severity == "critical" else 0.45)

        alert_id = next_id("alert", "ALT")
        row = dict(alert_id=alert_id, entity_id=entity["entity_id"], asset_id=asset["asset_id"],
                   severity=severity, category=category,
                   created_at=created_at.isoformat(), acknowledged_at=acknowledged_at.isoformat(),
                   closed_at=closed_at.isoformat(), disposition=disposition,
                   escalated=int(escalated))
        alerts_rows.append(row)
        entity_alerts.append(row)

    return entity_alerts


def gen_cases_for_entity(entity, entity_alerts, entity_assets):
    rng = random.Random(f"{SEED}-cases-{entity['entity_id']}")
    issues = set(entity["issues"])
    asset_by_id = {a["asset_id"]: a for a in entity_assets}
    investigators = [fake_name(rng) for _ in range(rng.randint(5, 8))]

    # candidate alerts for case creation, weighted toward higher severity / true_positive
    candidates = []
    for a in entity_alerts:
        p = {"critical": 0.85, "high": 0.55, "medium": 0.18, "low": 0.06}[a["severity"]]
        if a["disposition"] in ("false_positive", "duplicate"):
            p *= 0.25
        if "low_conversion_rate" in issues and a["severity"] in ("critical", "high"):
            p *= 0.15
        if rng.random() < p:
            candidates.append(a)

    entity_cases = []
    used_alerts = set()
    i = 0
    while i < len(candidates):
        alert = candidates[i]
        i += 1
        if alert["alert_id"] in used_alerts:
            continue
        bundle = [alert]
        used_alerts.add(alert["alert_id"])
        # occasionally bundle 1-2 more nearby alerts on same asset into one case
        if rng.random() < 0.15 and i < len(candidates):
            for j in range(i, min(i + 2, len(candidates))):
                cand2 = candidates[j]
                if cand2["asset_id"] == alert["asset_id"] and cand2["alert_id"] not in used_alerts:
                    bundle.append(cand2)
                    used_alerts.add(cand2["alert_id"])

        primary = bundle[0]
        created_at = datetime.fromisoformat(primary["acknowledged_at"])
        opened_at = created_at + timedelta(minutes=max(1, rng.gauss(20, 15)))

        template_flag = "template_notes" in issues and rng.random() < 0.70
        no_notes_flag = "fast_close_no_notes" in issues and primary["severity"] in ("critical", "high") and rng.random() < 0.75

        if no_notes_flag:
            closed_at = opened_at + timedelta(minutes=rng.uniform(1, 12))
            notes = "" if rng.random() < 0.6 else "Closed."
        else:
            close_delay_min = closure_minutes_normal(rng, primary["severity"])
            closed_at = opened_at + timedelta(minutes=close_delay_min)
            asset_name = asset_by_id[primary["asset_id"]]["name"]
            notes = generate_notes(rng, asset_name, primary["category"], primary["disposition"],
                                    template=template_flag)

        if closed_at > PERIOD_END + timedelta(days=10):
            closed_at = opened_at + timedelta(hours=6)

        if "no_root_cause" in issues and primary["severity"] in ("critical", "high"):
            root_cause = rng.random() < 0.12
        else:
            base_rc_rate = 0.55 if primary["severity"] in ("medium", "low") else 0.80
            root_cause = rng.random() < base_rc_rate

        remediation = None
        if root_cause and rng.random() < 0.85:
            remediation = rng.choice([
                "Blocked source IP at perimeter firewall and rotated affected credentials.",
                "Patched vulnerable service and verified via rescan.",
                "Revoked excess access and reissued least-privilege role.",
                "Isolated affected host and reimaged from known-good baseline.",
                "Updated detection rule to reduce recurrence and closed with monitoring note.",
            ])

        case_id = next_id("case", "CSE")
        entity_cases.append(dict(
            case_id=case_id, entity_id=entity["entity_id"],
            opened_at=opened_at.isoformat(), closed_at=closed_at.isoformat(),
            investigator=rng.choice(investigators),
            investigation_notes=notes, investigation_notes_length=len(notes),
            root_cause_identified=int(root_cause),
            remediation_action=remediation,
            _bundle=bundle, _primary=primary,
        ))

    for c in entity_cases:
        for a in c.pop("_bundle"):
            case_alerts_rows.append(dict(case_id=c["case_id"], alert_id=a["alert_id"]))
        cases_rows.append({k: v for k, v in c.items() if k != "_primary"})

    return entity_cases


def gen_escalations_for_entity(entity, entity_cases, alert_by_id):
    rng = random.Random(f"{SEED}-esc-{entity['entity_id']}")
    for c in entity_cases:
        primary = c["_primary"]
        if primary["escalated"]:
            escalated_at = datetime.fromisoformat(c["opened_at"]) + timedelta(minutes=max(1, rng.gauss(30, 20)))
            escalations_rows.append(dict(
                escalation_id=next_id("esc", "ESC"), case_id=c["case_id"],
                escalated_at=escalated_at.isoformat(),
                escalated_to=rng.choice(ESCALATION_TARGETS),
                severity_at_escalation=primary["severity"],
            ))


def gen_audit_logs_for_entity(entity, entity_alerts, entity_cases):
    rng = random.Random(f"{SEED}-audit-{entity['entity_id']}")
    issues = set(entity["issues"])

    if "audit_no_logs" in issues:
        return  # zero audit trail for this entity's activity — the whole point

    gap_window = None
    if "audit_gap_window" in issues:
        gap_start_day = rng.randint(80, PERIOD_DAYS - 80)
        gap_len = rng.randint(21, 28)
        gap_window = (PERIOD_START + timedelta(days=gap_start_day),
                      PERIOD_START + timedelta(days=gap_start_day + gap_len))
        GAP_WINDOWS[entity["entity_id"]] = gap_window

    actors = [fake_name(rng) for _ in range(rng.randint(4, 7))]
    coverage = 0.35 if entity["category"] == "borderline" else (0.30 if entity["category"] == "bad" else 0.80)

    def in_gap(ts):
        return gap_window is not None and gap_window[0] <= ts <= gap_window[1]

    for c in entity_cases:
        ts = datetime.fromisoformat(c["opened_at"])
        if not in_gap(ts) and rng.random() < coverage:
            audit_rows.append(dict(
                audit_id=next_id("audit", "AUD"), entity_id=entity["entity_id"],
                actor=c["investigator"], action_type="case_update", target_id=c["case_id"],
                timestamp=ts.isoformat(), reviewed_by_supervisor=int(rng.random() < 0.85),
            ))
        closed_ts = datetime.fromisoformat(c["closed_at"])
        if not in_gap(closed_ts) and rng.random() < coverage:
            audit_rows.append(dict(
                audit_id=next_id("audit", "AUD"), entity_id=entity["entity_id"],
                actor=c["investigator"], action_type="alert_review", target_id=c["_primary"]["alert_id"],
                timestamp=closed_ts.isoformat(), reviewed_by_supervisor=int(rng.random() < 0.85),
            ))

    # privileged actions, sprinkled across the period
    n_privileged = rng.randint(15, 40)
    for _ in range(n_privileged):
        day_offset = rng.randint(0, PERIOD_DAYS)
        ts = PERIOD_START + timedelta(days=day_offset, hours=rng.randint(0, 23))
        if in_gap(ts):
            continue
        action = rng.choice(["config_change", "access_grant"])
        if "audit_privileged_not_reviewed" in issues:
            reviewed = 0
        else:
            reviewed = int(rng.random() < 0.90)
        audit_rows.append(dict(
            audit_id=next_id("audit", "AUD"), entity_id=entity["entity_id"],
            actor=rng.choice(actors), action_type=action, target_id=None,
            timestamp=ts.isoformat(), reviewed_by_supervisor=reviewed,
        ))

    # generic alert_review noise entries not tied to a case (routine triage)
    n_noise = int(len(entity_alerts) * coverage * 0.25)
    for _ in range(n_noise):
        alert = rng.choice(entity_alerts)
        ts = datetime.fromisoformat(alert["created_at"]) + timedelta(minutes=rng.randint(1, 120))
        if in_gap(ts):
            continue
        audit_rows.append(dict(
            audit_id=next_id("audit", "AUD"), entity_id=entity["entity_id"],
            actor=rng.choice(actors), action_type="alert_review", target_id=alert["alert_id"],
            timestamp=ts.isoformat(), reviewed_by_supervisor=int(rng.random() < 0.85),
        ))


def gen_escalation_audit_entries():
    rng = random.Random(f"{SEED}-esc-audit")
    case_entity = {c["case_id"]: c["entity_id"] for c in cases_rows}
    no_audit_entities = {e["entity_id"] for e in ENTITIES if "audit_no_logs" in e["issues"]}
    for esc in escalations_rows:
        entity_id = case_entity.get(esc["case_id"])
        if entity_id in no_audit_entities:
            continue
        gap = GAP_WINDOWS.get(entity_id)
        if gap and gap[0] <= datetime.fromisoformat(esc["escalated_at"]) <= gap[1]:
            continue
        audit_rows.append(dict(
            audit_id=next_id("audit", "AUD"), entity_id=entity_id,
            actor="System", action_type="escalation_action", target_id=esc["case_id"],
            timestamp=esc["escalated_at"], reviewed_by_supervisor=int(rng.random() < 0.85),
        ))


def build_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    conn.executemany(
        "INSERT INTO entities (entity_id, name, sector, tier) VALUES (?,?,?,?)",
        [(e["entity_id"], e["name"], e["sector"], e["tier"]) for e in ENTITIES],
    )

    all_alert_by_id = {}
    for entity in ENTITIES:
        entity_assets = gen_assets(entity)
        entity_alerts = gen_alerts_for_entity(entity, entity_assets)
        for a in entity_alerts:
            all_alert_by_id[a["alert_id"]] = a
        entity_cases = gen_cases_for_entity(entity, entity_alerts, entity_assets)
        gen_escalations_for_entity(entity, entity_cases, all_alert_by_id)
        gen_audit_logs_for_entity(entity, entity_alerts, entity_cases)

    gen_escalation_audit_entries()

    conn.executemany(
        "INSERT INTO assets (asset_id, entity_id, name, criticality, asset_type) VALUES (?,?,?,?,?)",
        [(r["asset_id"], r["entity_id"], r["name"], r["criticality"], r["asset_type"]) for r in assets_rows],
    )
    conn.executemany(
        """INSERT INTO alerts (alert_id, entity_id, asset_id, severity, category, created_at,
           acknowledged_at, closed_at, disposition, escalated) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [(r["alert_id"], r["entity_id"], r["asset_id"], r["severity"], r["category"], r["created_at"],
          r["acknowledged_at"], r["closed_at"], r["disposition"], r["escalated"]) for r in alerts_rows],
    )
    conn.executemany(
        """INSERT INTO cases (case_id, entity_id, opened_at, closed_at, investigator,
           investigation_notes, investigation_notes_length, root_cause_identified, remediation_action)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [(r["case_id"], r["entity_id"], r["opened_at"], r["closed_at"], r["investigator"],
          r["investigation_notes"], r["investigation_notes_length"], r["root_cause_identified"],
          r["remediation_action"]) for r in cases_rows],
    )
    conn.executemany(
        "INSERT INTO case_alerts (case_id, alert_id) VALUES (?,?)",
        [(r["case_id"], r["alert_id"]) for r in case_alerts_rows],
    )
    conn.executemany(
        """INSERT INTO escalations (escalation_id, case_id, escalated_at, escalated_to,
           severity_at_escalation) VALUES (?,?,?,?,?)""",
        [(r["escalation_id"], r["case_id"], r["escalated_at"], r["escalated_to"],
          r["severity_at_escalation"]) for r in escalations_rows],
    )
    conn.executemany(
        """INSERT INTO audit_logs (audit_id, entity_id, actor, action_type, target_id,
           "timestamp", reviewed_by_supervisor) VALUES (?,?,?,?,?,?,?)""",
        [(r["audit_id"], r["entity_id"], r["actor"], r["action_type"], r["target_id"],
          r["timestamp"], r["reviewed_by_supervisor"]) for r in audit_rows],
    )

    conn.commit()

    counts = {}
    for tbl in ["entities", "assets", "alerts", "cases", "case_alerts", "escalations", "audit_logs"]:
        counts[tbl] = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    conn.close()
    return counts


def write_issue_seed_sheet():
    seed = {
        "period_start": PERIOD_START.date().isoformat(),
        "period_end": PERIOD_END.date().isoformat(),
        "entities": [
            {
                "entity_id": e["entity_id"],
                "name": e["name"],
                "sector": e["sector"],
                "category": e["category"],
                "injected_issues": [
                    {"code": code, "description": ISSUE_DESCRIPTIONS[code]} for code in e["issues"]
                ],
            }
            for e in ENTITIES
        ],
        "issue_catalog": ISSUE_DESCRIPTIONS,
    }
    ISSUES_PATH.write_text(json.dumps(seed, indent=2))


if __name__ == "__main__":
    print("Generating Anveshak synthetic SOC dataset...")
    counts = build_database()
    write_issue_seed_sheet()
    print(f"Database written to {DB_PATH}")
    for k, v in counts.items():
        print(f"  {k:14s}: {v:,}")
    print(f"Ground-truth seed sheet written to {ISSUES_PATH}")
