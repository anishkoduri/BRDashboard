# BRDashboard scope

Source: `docs/decision-record.md`. Next step after this file: `feature-expansion` Phases 0–3, then `orchestrate` builds. `orch-build-mvp` does not run in this pass.

Hours left: ~27 (assumption from the 15 Nov 2026, 11:00 PM CST deadline). Time budget: ~9h keep the demo path reliable, ~9h design package and planner polish, ~9h rehearsal, tests, submission docs, slack.

Platform: web.

Design direction: Furrow (Hallmark). Light manila paper, tangerine accent, survey-map command center, Red Hat Display / Fraunces (sentences only) / Red Hat Mono. Dashboard lead: `ui-ux-pro-max`. Texture: `less-flat-ui`. Theme deal: `design-taste-frontend`.

Winnable category: the assigned AISFS × Merck decision-aid challenge. Win on a feasible morning plan a judge can stress, not on a risk-score chart.

## Project assessment

- Strengths: cohort risk, economics, and a real CP-SAT planner already exist in this repo, with a running Next.js shell.
- Weaknesses: several planning notes in this file are older than the morning-path redesign. The submission documents named in the README are now written.
- Opportunities: the live replan when staff is cut is the moment judges remember.
- Constraints: ~27 hours, local-only, no paid APIs, do not delete the six research PDFs or working code.
- Recommended direction: make the 3-minute morning path solid and visually Furrow, then add only expansions that change that path.

## Wow test

The judge cuts staff on the planner and the week either reallocates or lists the clinical reviews that no longer fit. The survey map and the solver status change together. A static risk percentage does not pass this test.

## Must-have (CORE demo)

1. Load the synthetic four-yard set and show head count, attention, recorded first treatments, and projected remaining treatments as different numbers.
2. Open one priority cohort and show drivers, missing history, and the research-threshold label.
3. Generate today’s plan with OR-Tools. Show packages, capacity, and solver status. Do not call a feasible plan optimal.
4. Compare baseline checks, the proposed schedule, and a hypothetical protocol. Wording stays assumption-dependent. The protocol is not executed.
5. Reduce staff. The solver reruns. Unmet clinical work stays visible.
6. Move the clock or add a first-treatment count. Remaining-period numbers update. Future events do not enter an earlier assessment.
7. Change the effectiveness or loss assumption. The hypothetical column moves. The executed schedule does not become a prescription.
8. Export a print summary that matches the on-screen comparison.
9. Banner: demonstration data, not a diagnosis, not a prescription.

## Cut list

- P2 offline sync, NASA POWER / NOAA live weather, role-based auth, shared-staff routing between yards, extra prediction-model bakeoff.
- Paid APIs and any LLM that the demo requires.
- Presenting synthetic calibration as clinical validation.
- Autonomous drug selection, dose, or withholding of care to save money.
- cut substance: none. The optimizer, temporal filter, and cost functions stay real.

## Demo storyboard (live, 3 minutes)

1. 0:00–0:30 Command Center. Four yards, head count, recorded vs projected.
2. 0:30–1:00 Open the priority lot. Drivers and missing history.
3. 1:00–1:45 Generate the plan and compare it with baseline checks.
4. 1:45–2:20 Cut staff. Show the new feasible plan or the unmet reviews.
5. 2:20–2:45 Name the assumption that would flip the hypothetical column.
6. 2:45–3:00 Open the print summary.

## Technical substance

### Load and prioritize

- Architecture: browser `WorkspaceProvider` → `GET /api/snapshot` → `Workspace.cohort_views()` over demo CSVs plus SQLite overlays.
- Algorithm: logistic-normal arrival rate, beta-style update through the assessment day, hazard curve for remaining first treatments (`app/model.py`).
- Performance budget: snapshot under 2 seconds on the demo set.
- Edges: API down shows an error, not an infinite “Loading”; unknown vaccination is not low risk; cohort not yet arrived is hidden; counts cannot exceed head.

### Optimize and stress

- Architecture: `POST /api/optimization/solve` → `solve_plan` (CP-SAT) → plan cached on the workspace and shown on Command, Planner, and Decisions.
- Algorithm: one package per active cohort, lexicographic safety then cost/labor, integer-scaled hours, unmet clinical obligations reported instead of dropped.
- Performance budget: solve under 5 seconds, status string honest.
- Edges: staff multiplier 0.4; infeasible care stays listed; budget cannot delete mandatory review; medication packages stay veterinary-review-required and unexecuted.

### Clock, assumptions, export

- Architecture: clock and observations write SQLite; economics recompute from the same views; HTML report reads the comparison.
- Algorithm: events with `day_on_feed` after the clock are excluded; common scenario inputs for the three columns; inclusive morbidity loss is not added twice.
- Performance budget: assumption patch returns in under 2 seconds; report is the same totals as the decisions page.
- Edges: bad clock rejected; failed CSV import leaves the working set; zero effectiveness adds no prevention benefit; monitoring does not reduce biological burden.

## Unknowns

- Weather API: skipped (P2). Owner: builder. Resolution: during build, keep seasonal fields.
- Deploy: local first. Owner: builder. Resolution: after browser-qa, only if a free path exists.
