-- SAT-SA (Anveshak) — Supervisory Analytics Tool for SOC Assessment
-- SQLite schema. Single-file DB, zero external services.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS escalations;
DROP TABLE IF EXISTS case_alerts;
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS entities;

CREATE TABLE entities (
    entity_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    sector      TEXT NOT NULL CHECK (sector IN ('Power','Banking','Telecom')),
    tier        TEXT NOT NULL CHECK (tier IN ('Tier-1','Tier-2','Tier-3'))
);

CREATE TABLE assets (
    asset_id     TEXT PRIMARY KEY,
    entity_id    TEXT NOT NULL REFERENCES entities(entity_id),
    name         TEXT NOT NULL,
    criticality  TEXT NOT NULL CHECK (criticality IN ('critical','high','medium','low')),
    asset_type   TEXT NOT NULL
);

CREATE TABLE alerts (
    alert_id        TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(entity_id),
    asset_id        TEXT NOT NULL REFERENCES assets(asset_id),
    severity        TEXT NOT NULL CHECK (severity IN ('critical','high','medium','low')),
    category        TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    acknowledged_at TEXT,
    closed_at       TEXT,
    disposition     TEXT CHECK (disposition IN ('true_positive','false_positive','benign','duplicate')),
    escalated       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE cases (
    case_id                     TEXT PRIMARY KEY,
    entity_id                   TEXT NOT NULL REFERENCES entities(entity_id),
    opened_at                   TEXT NOT NULL,
    closed_at                   TEXT,
    investigator                TEXT NOT NULL,
    investigation_notes         TEXT,
    investigation_notes_length  INTEGER NOT NULL DEFAULT 0,
    root_cause_identified       INTEGER NOT NULL DEFAULT 0,
    remediation_action          TEXT
);

CREATE TABLE case_alerts (
    case_id   TEXT NOT NULL REFERENCES cases(case_id),
    alert_id  TEXT NOT NULL REFERENCES alerts(alert_id),
    PRIMARY KEY (case_id, alert_id)
);

CREATE TABLE escalations (
    escalation_id           TEXT PRIMARY KEY,
    case_id                 TEXT NOT NULL REFERENCES cases(case_id),
    escalated_at            TEXT NOT NULL,
    escalated_to            TEXT NOT NULL,
    severity_at_escalation  TEXT NOT NULL CHECK (severity_at_escalation IN ('critical','high','medium','low'))
);

CREATE TABLE audit_logs (
    audit_id               TEXT PRIMARY KEY,
    entity_id               TEXT NOT NULL REFERENCES entities(entity_id),
    actor                    TEXT NOT NULL,
    action_type              TEXT NOT NULL CHECK (action_type IN
                              ('alert_review','case_update','escalation_action','config_change','access_grant')),
    target_id                TEXT,
    "timestamp"               TEXT NOT NULL,
    reviewed_by_supervisor   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_assets_entity ON assets(entity_id);
CREATE INDEX idx_alerts_entity ON alerts(entity_id);
CREATE INDEX idx_alerts_asset ON alerts(asset_id);
CREATE INDEX idx_alerts_created ON alerts(created_at);
CREATE INDEX idx_cases_entity ON cases(entity_id);
CREATE INDEX idx_case_alerts_case ON case_alerts(case_id);
CREATE INDEX idx_case_alerts_alert ON case_alerts(alert_id);
CREATE INDEX idx_escalations_case ON escalations(case_id);
CREATE INDEX idx_audit_entity ON audit_logs(entity_id);
CREATE INDEX idx_audit_timestamp ON audit_logs("timestamp");
