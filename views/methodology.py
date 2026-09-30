"""Methodology — scoring formula, full rule catalog, and (for this synthetic demo
build only) the injected ground-truth seed sheet used to validate the detectors."""

import json
from pathlib import Path

import streamlit as st

from ui_common import page_header, rule_catalog_markdown

page_header("Methodology & Explainability")

st.markdown("""
### How the composite risk score is built

Every detector rule produces **entity-level findings**, each carrying a fixed
number of *points* computed by a documented, fully transparent formula — no
black-box model, no learned weights:

```
points = base_points × min(1.0, max(0.0, (observed_rate − floor) / (saturation − floor)))
```

- **base_points** — the rule's maximum contribution (its documented supervisory severity weight).
- **floor** — the rate below which the rule does not fire at all (filters normal
  operational noise so a rule only lights up on a genuine departure from baseline).
- **saturation** — the rate at which the rule contributes its full base_points.
- Boolean / presence-based rules (e.g. "zero escalations despite critical alerts")
  simply award the full base_points when they fire.

An entity's **total risk score** is the straight sum of every finding's points,
capped at 100. That means the score for any entity can be fully reconstructed
by hand from the Entity Detail page's findings list — nothing is hidden.

**Bands:** Severe ≥ 45, Moderate ≥ 18, Clean below that.
""")

st.subheader("Full rule catalog")
st.markdown(rule_catalog_markdown())

st.markdown("""
---
### Peer benchmarking

Entities are grouped by **sector** (Power / Banking / Telecom) as their peer
group. For five key metrics — critical-alert escalation rate, mean closure
time by severity, alerts per asset, case-to-alert ratio, and audit-log
coverage ratio — each entity gets a z-score against its sector peers. A
deviation beyond ±1.5–2 standard deviations is flagged as significant (see
the peer comparison chart on the Entity Detail page).

### Review priority

Individual evidence items (alerts / cases / audit rows) inherit their parent
finding's severity and are ranked by `severity_rank × 10 + evidence-volume
bonus (capped)` — the Review Queue page sorts on this directly.

### Validation approach

**For this prototype:** every detector was validated against a synthetic
dataset with deliberately injected failure patterns (fast-closure, template
notes, missing escalations, telemetry gaps, audit blind spots, etc.), spread
across 4 "bad", 3 "borderline" and 5 "good" entities. Each detector was
confirmed to fire clearly on the entity carrying its target pattern and to
stay silent (or near-zero) on entities that don't — i.e. it correctly
separates the injected ground truth. The seed sheet documenting exactly which
entity carries which issue is shown below for transparency.

**For production deployment against real CSE data:** the same detectors would
be validated by computing precision/recall against a sample of historical
alerts/cases that NCIIPC supervisors have already manually reviewed and
labeled — treating supervisor judgment as ground truth and tuning the
`floor`/`saturation` constants per rule until the detectors' flags agree with
expert review at an acceptable precision, the way any alerting threshold is
calibrated before going live.
""")

st.markdown("---")
st.subheader("Synthetic data ground truth (this demo build only)")
st.caption("Not part of the production tool — included so reviewers can verify the detectors against "
           "the known-injected issues in the synthetic dataset.")

seed_path = Path(__file__).parent.parent / "data" / "injected_issues.json"
if seed_path.exists():
    seed = json.loads(seed_path.read_text())
    for ent in seed["entities"]:
        label = ent["category"].upper()
        with st.expander(f"{ent['entity_id']} — {ent['name']} [{label}]"):
            if not ent["injected_issues"]:
                st.write("No issues injected — expected to score near zero.")
            else:
                for issue in ent["injected_issues"]:
                    st.write(f"- **{issue['code']}** — {issue['description']}")
else:
    st.info("Seed sheet not found — run `python data_generator.py` to regenerate it.")
