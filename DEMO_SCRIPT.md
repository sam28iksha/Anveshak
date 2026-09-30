# Anveshak — 90-Second Demo Script

Setup before recording: `streamlit run app.py`, browser at the **Overview**
page, sidebar Sector filter set to all three sectors.

---

**0:00 – 0:15 — Overview: the spectrum, not a binary**
> "This is Anveshak — a supervisory analytics tool that reads SOC alert and
> case data from multiple Critical Sector Entities and scores each one for
> review. It's not a SIEM, it's batch analysis over data that already
> exists."

Point at the ranked table: 12 entities, risk scores from 100 down to 0, with
a **Severe / Moderate / Clean** band column and a per-entity monthly-risk
sparkline. Call out the visible cliff: six entities sitting at 40+, then a
hard drop to five entities at 5 or below.
> "Notice this isn't a flat list — it's a real spectrum, and there's a clear
> gap between entities carrying real problems and entities that are clean."

**0:15 – 0:30 — Click into the worst-ranked entity**
Click **Entity Detail** in the sidebar → **PWR-01 — Grid Power Transmission
Co.** (already top of the list, score 100/Severe).
> "Grid Power Transmission tops the list at 100 out of 100, with seven
> independent findings spanning all three categories — execution gaps,
> negative space, and audit supervision. That spread across categories is
> what's driving the score up, not one noisy rule."

**0:30 – 0:50 — Evidence drill-down on a specific finding**
Expand **"Critical alert closed without any escalation"** in the findings
list.
> "Every finding is a plain-English sentence with the actual numbers: 119 of
> 119 confirmed critical alerts here — that's 100% — were closed with zero
> escalation record anywhere in the log."

Scroll down inside the expander to the evidence table.
> "And it's not just a rate — here are the exact alert IDs behind it. A
> supervisor can open any one of these and see precisely what closed
> without ever going up the chain."

**0:50 – 1:05 — Audit-log supervision finding**
Expand **"Case activity with no matching audit log entry"**.
> "This is the audit-supervision layer — a separate evidence type from
> alerts and cases. Here, 495 of 495 cases for this entity have *zero*
> matching audit_logs rows. Work happened, cases got closed, but there's no
> record of who did it. That's an accountability gap, not just a SOC
> performance gap."

**1:05 – 1:20 — Peer comparison chart**
Scroll up to the **Peer comparison (sector z-score)** chart.
> "Every metric is also benchmarked against this entity's own sector peers
> — same-sector Power entities only. Mean closure time for critical and
> high alerts is sitting more than one and a half standard deviations below
> peers, flagged in red — this entity resolves things far faster than
> anyone else in Power, which is exactly the pattern you'd expect if
> alerts are getting closed without real investigation."

**1:20 – 1:30 — Review queue**
Click **Review Queue** in the sidebar.
> "And finally, every piece of evidence across every entity rolls up into
> one prioritized worklist, sorted by severity — this is what a supervisor
> actually works from, alert by alert, case by case, one rationale line
> each."

*(End at ~1:30. If time remains, add: open Methodology page and show the
ground-truth seed sheet expander for PWR-01 to prove the detectors are
catching exactly what was injected — good closer for a technical audience.)*
