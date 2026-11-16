# Expansion — planner-approved list

Story: The morning survey shows a feasible week; cutting staff names the lot and the yard-day that no longer fit, and a later pull cannot rewrite an earlier morning.

Scores are value / originality / feasibility / differentiation / demo / effort, each 1–3. Effort scores high when the work is small. One bold bet: the infeasibility witness, with a fallback.

| # | Feature | Why | Effort | Depends on | UI | Tool/API | Scores | Verdict | Order | Risk |
|---|---------|-----|--------|------------|----|----------|--------|---------|-------|------|
| 1 | A dead API or a failed refresh leaves the morning on “Loading the four yards.” | The command frame stays up, shows the failure, and keeps the last snapshot. Generate stays disabled until a snapshot exists. | S | `GET /api/snapshot` | Y | none | 3/1/3/2/3/3 | Approve | 1 | If the rewrite hangs, a 8s timeout must still flip the frame to failed. |
| 2 | After a staff cut the new week replaces the old one with no named lot or cause. | Diff the assignment maps. One sentence names the lot that left a review and the yard-day whose vet slots or staff hours are full. Pins read held, moved, or unmet. | M | `plan.assignments`, `unmet_clinical`, `usage` | Y | none | 3/2/3/2/3/2 | Approve | 2 | If no usage row is saturated, the sentence says the cut did not bind a listed resource. |
| 3 | The priority lot opens on a risk percentage. | The lot leads with its review slot or unmet review. The 15% figure stays the research-threshold note. | S | `plan.assignments`, `explain_cohort` | Y | none | 3/1/3/1/3/3 | Approve | 3 | No plan yet: say the week has not been generated. |
| 4 | The lot does not say how many more pulls would turn the review on. | Integer scan of additional first-treatment counts through the current clock. Report the smallest count that flips `clinical_obligation`. | S | `assess_cohort` | Y | none | 3/2/3/2/2/3 | Approve | 6 | Already on: the sentence says it is on. The scan never offers a lower count to clear it. |
| 5 | The assumption that moves the hypothetical column lives on another screen. | On Decisions, changing effectiveness or loss highlights only the hypothetical figures. Proposed-schedule totals stay the same values. | S | compare + assumption patch | Y | none | 3/1/3/1/3/3 | Approve | 4 | A failed patch restores the previous comparison. |
| 6 | The print summary is a different story from the planner. | The HTML report headlines the same binding sentence and unmet names as the planner. | S | feature 2, existing report route | Y | none | 3/2/3/1/3/3 | Approve | 5 | No plan: the report says the week has not been generated. |
| 7 | The timeline is one point, so a later pull can be mistaken for something the earlier morning knew. | For each day through the clock, assess with events on or before that day. A later overlay must leave earlier rows unchanged. | M | `assess_cohort`, `_events_through` | Y | none | 3/2/2/3/2/2 | Approve | 8 | Never read simulator truth. Cap the series at the clock day. |
| 8 | When the week cannot cover every review, the unmet list has no proof. | On one yard, attach CP-SAT assumption literals and return a sufficient set. If the core is empty or the time limit hits, say the witness is unavailable and keep feature 2’s sentence. | L | `solve_plan` | Y | `ortools.sat.python.cp_model` | 2/3/2/3/3/1 | Tweak: one yard only; fallback is the binding sentence, not a second planner. | 10 | A wide core or a timeout must not replace the working plan. Wording stays “does not fit.” |
| 9 | Extra pen checks can look like they reduced disease, and the sweep prices the wrong column. | `monitoring_changes_disease` stays false. Inclusive loss is not added on top of component costs. The hypothetical column is the only place effectiveness moves. | M | `evaluate_assignment`, frozen assignments | Y | none | 3/2/3/2/1/2 | Tweak: lock it with a test and one visible line. Do not rebuild the cost model. | 7 | If the identity fails, show the failure. Do not zero a real disease term to force a pass. |
| 10 | An unmet review looks like the computer dropped care. | A veterinarian can record a simulated review on one named cohort. The stamp does not delete the obligation, rewrite other packages, or authorize a drug. | S | `POST /api/reviews` | Y | none | 3/1/3/1/2/3 | Approve | 9 | Role other than veterinarian: the control stays unavailable. |

## Rejected

- Day lock and forced-slot trade: easy to read as scheduling treatment, and the witness covers “why it does not fit.”
- Smallest-crew objective and staff-multiplier bisection: extra solves; the binding sentence is the demo beat.
- Rate-band flip solves: a weak weight can return an empty flip list inside the demo pause.
- Lexicographic two-stage replace: can reshuffle the current solver tests. Keep the existing safety-then-labor path.
- Pen-walk order: pen numbers are a generator modulus, not a yard map.
- Three-morning leak seal and the discardable peek: the day-prefix replay already shows that a later pull cannot rewrite an earlier morning.
- Survey contour density: decoration once pins already change with the diff.
- Pen-day mutex: can reshuffle a feasible demo week. Yard capacity stays the constraint.
- One-slot counterfactual probes: extra solves. The witness is the one bold bet.
- Retreat-count obligation: a new clinical rule. Retreat stays a count. It does not add a second $151.18 or a new trigger.
- Kappa shrink for missing history: a new coefficient. Missing history stays listed. Unknown vaccination stays not protective.

## Assumptions

- API on 127.0.0.1:8000 was healthy at approval time. A second uvicorn process must not be started.
- New plan fields are added. Existing assignment, unmet, and usage keys stay.
- `grok-4.7-high` is not in this session’s model list. Decision implementers use `grok-4.7-high-fast`.
