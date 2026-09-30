# Anveshak (SAT-SA) — Architecture

## Data flow

```
 ┌─────────────────────┐
 │  data_generator.py   │  synthetic CSE data with injected failure patterns
 │  (or: real CSE ETL)  │  (production: replace this stage only)
 └──────────┬───────────┘
            │ writes
            ▼
 ┌─────────────────────┐
 │  data/anveshak.db     │  SQLite — entities, assets, alerts, cases,
 │  (schema.sql)         │  case_alerts, escalations, audit_logs
 └──────────┬───────────┘
            │ analytics/db.py :: load_all()
            ▼
 ┌─────────────────────┐
 │   pandas DataFrames   │  one in-memory load per session (cached)
 └──────────┬───────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  DETECTION ENGINE  (analytics/detectors.py)               │
 │  14 independent rule functions, each entity-scoped:       │
 │  6 execution-gap · 4 negative-space · 4 audit-supervision  │
 │  → finding {entity_id, category, rule_code, rule_name,     │
 │             severity, rationale, metric_value,             │
 │             threshold_used, evidence_type, evidence_ids,   │
 │             points}                                        │
 └──────────┬──────────────────────────────┬─────────────────┘
            │                              │
            ▼                              ▼
 ┌─────────────────────┐      ┌─────────────────────────────┐
 │  SCORING              │      │  PEER BENCHMARKING            │
 │  (analytics/scoring.py)│     │  (analytics/peer_benchmarking) │
 │  sum(points) capped    │     │  sector-group z-scores on      │
 │  at 100 per entity;    │     │  5 metrics; feeds EG5 and the   │
 │  band = Severe/         │     │  Entity Detail peer chart       │
 │  Moderate/Clean;        │     └─────────────────────────────┘
 │  monthly trend proxy   │
 └──────────┬───────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  EXPLAINABILITY LAYER  (ui_common.py :: evidence_table)    │
 │  every finding's evidence_ids resolve back to raw           │
 │  alert/case/audit/asset rows on demand — nothing is         │
 │  summarized away before it reaches the reviewer              │
 └──────────┬──────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  DASHBOARD  (Streamlit — app.py + pages/)                   │
 │  Overview → Entity Detail → Review Queue → Trend View        │
 │  → Methodology (rule catalog + ground-truth seed sheet)      │
 └─────────────────────────────────────────────────────────┘
```

Everything left of the dashboard is plain pandas/SQLite running in the same
local process — there is no service boundary, no network hop, and no
external call anywhere in this chain. `streamlit run app.py` starts one
local HTTP server (default `localhost:8501`); the only "client" is the
browser tab pointed at it.

## Detectors implemented

**Execution gap** (`EG*`, `analytics/detectors.py`)
1. `EG1` Critical/high case closed faster than a statistical floor (5th
   percentile of closure time for that severity, capped at 30/45 min) with
   no investigation notes.
2. `EG2` Critical alert (confirmed true positive) closed with zero
   escalation records.
3. `EG3` Investigation notes near-duplicated (normalized-text match) across
   ≥3 cases — template/copy-paste detector.
4. `EG4` High/critical case resolved without `root_cause_identified`.
5. `EG5` Critical-alert escalation rate >1.5 std devs below sector peer
   median.
6. `EG6` High/critical alerts acknowledged but rarely converted into a case.

**Negative space** (`NS*`)
1. `NS1` Critical-tier asset with alert volume in the bottom decile of the
   entity's own other critical assets — monitoring/telemetry gap.
2. `NS2` Zero escalations recorded despite critical alerts existing.
3. `NS3` Alert category present for almost every sector peer, never once
   seen for this entity.
4. `NS4` ≥3 consecutive weeks of alert volume collapsing to <15% of the
   entity's own baseline — possible monitoring outage.

**Audit supervision** (`AS*`) — a distinct evidence layer checking whether
activity is *accountable*, not just whether it happened.
1. `AS1` Case activity with no matching `audit_logs` entry.
2. `AS2` ≥3 consecutive weeks with zero audit rows despite active alert
   volume — oversight logging gap.
3. `AS3` Privileged actions (`config_change`, `access_grant`) never marked
   `reviewed_by_supervisor`.
4. `AS4` *(optional, implemented)* Audit-log density (rows per case) >1.5
   std devs below sector peers.

## Scoring methodology

Each rule has three documented constants — `base_points`, `floor`,
`saturation` (full table on the in-app Methodology page). For rate-based
rules:

```
points = base_points × clip((observed_rate − floor) / (saturation − floor), 0, 1)
```

`floor` exists so a rule only fires on a genuine departure from normal
operational noise (e.g. even healthy entities don't escalate 100% of
criticals — the floor absorbs that baseline). Boolean/presence rules (zero
escalations, missing category, audit timeline gap, telemetry-gap asset)
award the full `base_points` when triggered. An entity's **composite risk
score is the plain sum of every finding's points, capped at 100** — no
normalization tricks, no learned weighting. **Bands:** Severe ≥45,
Moderate ≥18, Clean <18. Review-queue items inherit their parent finding's
severity and are ranked by `severity_rank × 10 + evidence-volume bonus`.

## Validation approach

**This prototype** was validated against its own synthetic dataset, which
has known ground truth: 4 entities with deliberately injected severe issues
("bad"), 3 with a deliberate mix of real and clean signals ("borderline"),
5 with none ("good") — see `data/injected_issues.json`. Every detector was
checked to (a) fire clearly on the entity carrying its target pattern and
(b) stay silent or near-zero on entities that don't carry it. The resulting
composite scores separate cleanly: all 5 "good" entities score ≤5/100,
every entity carrying an injected issue scores ≥40/100 — a wide, visible
gap between "has real problems" and "doesn't," which is the property a
supervisory triage tool actually needs. Within the "has problems" group,
ranking reflects total evidence weight rather than the internal
bad/borderline label — one borderline entity legitimately outranks two
"bad" ones because it independently triggers three high-weight rules,
which is the intended behavior of an additive, evidence-based score rather
than a relabeling exercise.

**Against real CSE data**, the same detectors would be validated by
running them over a sample of historical alerts/cases that NCIIPC
supervisors have already manually reviewed and labeled, treating that
manual review as ground truth, and computing precision/recall per rule —
then tuning `floor`/`saturation` per rule until flags agree with expert
judgment at an acceptable precision, exactly as any alerting threshold is
calibrated before it goes live operationally.

## Explicitly out of scope (by design, per the problem statement)

No real-time ingestion or SIEM-style correlation; no calls to any
external/cloud LLM or API for detection logic (the natural "AI-assisted"
extension — local embedding similarity for the template-detection rule —
is noted as future work rather than wired to a cloud model, to keep the
tool air-gapped); no auth/RBAC (noted as a production requirement, not
built here).
