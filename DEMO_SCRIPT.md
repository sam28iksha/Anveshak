# Anveshak — 2-Minute Demo Video Script

Setup before recording: `streamlit run app.py`, browser maximized, start on
the **Overview** page with the sidebar Sector filter set to all three
sectors. Zoom browser to ~100% so text is legible on a recorded video.

Total runtime: 2:00. Timestamps are cumulative — hit each cue on time and
you land the close exactly at 2:00.

---

**0:00 – 0:10 — Cold open on the brand**
Let the Overview page finish loading with the header banner in frame (logo
+ "Anveshak" + tagline visible).
> "Anveshak. See what the reports don't show."

**0:10 – 0:25 — Overview: the spectrum, not a binary**
Point at the ranked table — 12 entities, risk scores from 100 down to 0,
Severe/Moderate/Clean band column, per-entity monthly-risk sparkline.
> "This is a supervisory analytics tool for NCIIPC — it reads SOC alert,
> case, and audit data from multiple Critical Sector Entities and scores
> each one. Notice this isn't a flat list: six entities sit at 40 or above,
> then there's a hard drop to five entities at 5 or below. That gap is the
> whole point — it separates entities with real problems from entities
> that are actually clean."

**0:25 – 0:40 — Click into the worst-ranked entity**
Click **Entity Detail** in the sidebar → top entity is pre-selected (Grid
Power Transmission Co., score 100/Severe).
> "Grid Power Transmission tops the list at 100 out of 100, with seven
> independent findings spanning three categories — execution gaps,
> negative space, and audit supervision. That spread across categories is
> what's driving the score, not one noisy rule."

**0:40 – 0:58 — Evidence drill-down**
Expand **"Critical alert closed without any escalation"**, then scroll to
the evidence table inside it.
> "Every finding is a plain-English sentence with real numbers: 119 of 119
> confirmed critical alerts here — 100% — closed with zero escalation
> record. And it's not just a rate — here are the exact alert IDs behind
> it. A supervisor can open any one and see precisely what closed without
> ever going up the chain."

**0:58 – 1:15 — The audit-supervision layer**
Expand **"Case activity with no matching audit log entry"**.
> "This is a separate evidence layer most tools don't have — auditing the
> audit trail itself. 495 of 495 cases here have zero matching audit-log
> rows. Work happened, cases got closed, but there's no record of who did
> it. That's an accountability gap, not just a performance gap."

**1:15 – 1:30 — Peer comparison**
Scroll up to the **Peer comparison (sector z-score)** chart.
> "Every metric is also benchmarked against this entity's own sector peers.
> Mean closure time for critical and high alerts sits more than one and a
> half standard deviations below the Power sector — flagged red — meaning
> this entity resolves things far faster than anyone else, exactly what
> you'd expect if alerts are being closed without real investigation."

**1:30 – 1:42 — Trend view**
Click **Trend View** in the sidebar.
> "And this isn't just a snapshot — the trend view tracks monthly risk
> across every entity, so a supervisor can tell a sustained pattern from a
> one-off spike."

**1:42 – 1:52 — Review queue**
Click **Review Queue** in the sidebar.
> "Every piece of evidence, across every entity, rolls into one prioritized
> worklist sorted by severity — this is what a supervisor actually works
> from, one line at a time."

**1:52 – 2:00 — Close: proof it's not staged**
Click **Methodology** in the sidebar, open the ground-truth expander for
Grid Power Transmission Co.
> "And because this runs on synthetic data today, we can prove it: this
> entity's issues were deliberately injected, and the engine caught every
> one of them. Anveshak — see what the reports don't show."

---

### Recording notes
- Keep the mouse deliberate — pause half a second after each click before
  talking, so the cut doesn't feel rushed.
- If you're over time on a take, cut the Trend View beat (1:30–1:42) first
  — it's the only page not carrying a unique claim the others don't already
  make.
- Record at 1920×1080 minimum; the dashboard tables get hard to read below
  that on a compressed video export.
