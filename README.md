# Anveshak — SAT-SA (Supervisory Analytics Tool for SOC Assessment)

**NTRO Problem Statement #26157**

Anveshak helps NCIIPC supervisors analyze SOC alert/case-management data
submitted by multiple Critical Sector Entities (CSEs) and surfaces two things
a manual spot-check will usually miss at scale:

- **Execution gaps** — controls and processes that are *documented* as
  working but where the operational evidence says otherwise (criticals
  closed too fast with no notes, no escalation on criticals, template /
  copy-paste investigations, resolutions with no root cause, conversion and
  escalation rates that lag peers).
- **Negative space** — expected evidence that is *missing*: a critical asset
  with almost no telemetry, an entity with zero escalations ever, alert
  categories every peer reports but this entity never does, monitoring
  blind spots, and — as a distinct evidence layer — gaps or blind spots in
  the audit trail itself (who reviewed what, and when).

It is a **batch supervisory analytics tool**, not a SIEM: it does not ingest
live telemetry, does not do real-time correlation, and is not an operational
security product. It runs over a period's worth of already-collected
alert/case/audit data, scores and ranks entities and specific alert/case
samples for human review, and — this is the part that matters for a
supervisory tool — **explains why every single flag fired**, down to the
exact records behind it.

Everything runs fully offline: SQLite for storage, a local Streamlit server
for the UI, pandas for the analytics. No external API calls, no cloud
dependency, no CDN-loaded JS at runtime — it is built to run air-gapped.

---

## What the tool does

1. **Ingests** entity / asset / alert / case / escalation / audit-log data
   (synthetic generator included; see below for pointing it at real data).
2. **Runs a rule-based detection engine** — 14 independent, composable
   detectors across three categories (6+ execution-gap, 4+ negative-space,
   3+ audit-supervision), each producing an entity-level finding with a
   plain-English rationale, the exact metric value vs. the threshold used,
   and a list of the underlying alert/case/audit record IDs as evidence.
3. **Benchmarks every entity against its sector peers** on five metrics
   (escalation rate, closure time by severity, alerts per asset,
   case-to-alert ratio, audit-log coverage ratio) and flags significant
   deviations (>1.5–2 std devs).
4. **Aggregates findings into a single 0–100 composite risk score per
   entity**, using a documented, fully transparent point formula — no
   black-box model, no learned weights. The score for any entity can be
   reconstructed by hand from its findings list.
5. **Ranks entities and individual evidence items** so a supervisor gets a
   prioritized worklist, not just a leaderboard.
6. **Surfaces all of this in a multi-page dashboard** — Overview, Entity
   Detail (with drill-down evidence tables and peer comparison), Review
   Queue, Trend View, and an in-app Methodology page — with every finding
   expandable to its full rationale and raw evidence.

## Setup

Requires Python 3.9+ (no other system dependencies).

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python data_generator.py        # generates data/anveshak.db (~10-20s)
streamlit run app.py            # opens the dashboard at localhost:8501
```

Nothing else is required. No API keys, no network access, no database
server to stand up.

## How the synthetic data works

`data_generator.py` builds 12 fictional CSEs across three sectors (Power,
Banking, Telecom), spanning a 12-month period, with realistic volumes
(~22,000 alerts, ~4,900 cases, ~7,800 audit log entries). Random data alone
proves nothing, so the generator **deliberately injects known failure
patterns** into a subset of entities — fast-closure with no notes, missing
escalations, templated investigation notes, a telemetry-dark critical asset,
an entity with implausibly low alert volume, and (as a distinct evidence
layer) audit-log blind spots: entities with cases/escalations that have zero
matching audit entries, a multi-week gap in the audit timeline, and
privileged actions that were never marked as supervisor-reviewed. The exact
mapping of which entity carries which injected issue is written to
`data/injected_issues.json` and is also browsable from the app's
**Methodology** page, so every detector's output can be checked against
known ground truth.

## Pointing it at real CSE data

Replace the generator step with an ETL that populates the same schema
(`schema.sql` — `entities`, `assets`, `alerts`, `cases`, `case_alerts`,
`escalations`, `audit_logs`) into a SQLite file at `data/anveshak.db`, or
adapt `analytics/db.py::load_all()` to read from CSVs or another database
directly into the same pandas DataFrame shapes. The detection engine,
scoring, and dashboard need no other changes — they operate purely on the
loaded DataFrames and don't know or care whether the data is synthetic or
real.

## Project layout

```
data_generator.py      synthetic multi-entity SOC data generator
schema.sql              SQLite schema
analytics/
  db.py                 data access layer (SQLite -> pandas)
  common.py              shared helpers (case enrichment, finding schema)
  detectors.py           14 detection rules (execution gap / negative space / audit supervision)
  peer_benchmarking.py   sector peer z-scores
  scoring.py             composite risk score + monthly trend proxy
  engine.py               orchestration entry point used by the app
app.py                   Overview page (Streamlit multipage entry point)
pages/
  1_Entity_Detail.py
  2_Review_Queue.py
  3_Trend_View.py
  4_Methodology.py
ui_common.py             shared UI constants/helpers
ARCHITECTURE.md
DEMO_SCRIPT.md
```

---

## Roadmap — next version

This build satisfies the core NTRO #26157 requirement end-to-end
(ingestion → detection → scoring → explainability → dashboard, fully
offline). The next iteration is planned to add:

- **Real CSE data ingestion** — CSV/API adapters and a validation layer for
  onboarding actual entity submissions in place of the synthetic generator.
- **Auth / RBAC** — supervisor login, per-sector access scoping, and an
  audit trail of *who reviewed which finding* inside the tool itself (out
  of scope for this prototype by design, per the problem statement's
  guidance to defer it).
- **Locally-run embedding similarity for the template-detection rule** —
  the current EG3 detector uses exact/normalized text matching; a local
  (no external API) sentence-embedding model would catch paraphrased
  copy-paste, not just verbatim duplicates. Flagged in the problem
  statement as the natural "AI-assisted" extension, intentionally not
  wired to any external LLM/cloud service to keep the tool air-gapped.
- **Precision/recall calibration against supervisor-labeled samples** —
  once real historical review outcomes are available, the `floor` /
  `saturation` constants documented in `analytics/detectors.py` get tuned
  against them instead of against synthetic ground truth (see
  "Validation approach" in `ARCHITECTURE.md`).
- **Case-management write-back** — letting a supervisor mark a finding as
  reviewed/actioned/dismissed from inside the Review Queue, persisted back
  to the store, instead of a read-only worklist.
- **Configurable rule weights** — an admin view for tuning `base_points` /
  `floor` / `saturation` per rule without editing source, while keeping the
  same transparent additive-scoring model.
