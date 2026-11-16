# Demonstration case

One end-to-end decision on the included synthetic set. Clock inside the data: 2026-03-18. Seed 20261115. Model `brd-assumption-1.0.0`.

How to read the solver wording. The app labels the plan "Feasible, not proved." while any clinical review is unmet. A separate note beneath the label reports the solver's own status: "Solver FEASIBLE." or, on solves that finish inside the 3.0-second service limit, "Solver OPTIMAL." The label describes the plan. The note describes the solver. Neither is a different decision when the unmet count stays 7.

## How to reproduce

Prerequisites: Python 3.11 or newer, Node.js 20 or newer. No API key. From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
cd ..\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Leave the API running. In a second terminal:

```powershell
cd frontend
npm run dev -- --port 3000
```

The seeded demo set is already in `data/demo/` (seed 20261115, generator `backend/app/generate.py`). To reload it, use Data, then Load demonstration data, or `POST /api/data/demo`. Then:

1. Open http://127.0.0.1:3000. Morning opens on priority lot WK-008, day 3 of 45.
2. Choose Generate today's plan with crew at 1.00. Expect 100 assignments and 7 unmet clinical reviews.
3. Open Decisions and compare.
4. On Plan, cut crew to 0.40 and read the witness and "17 moved off the week". Put crew back to 1.00.
5. Summary, then Prepare summary.

The backend tests, `.\.venv\Scripts\python.exe -m pytest tests\api -q` from the repository root, check the seed reproduces the same cohorts.

## Inputs

Four fictional yards: Panhandle North, High Plains South, Western Kansas, Prairie Central. Head on feed 12,025. Observed first treatments 394. Projected remaining first treatments 212.1. Those are separate counts.

Priority lot WK-008, pen WK-P01, Western Kansas, day 3 of 45. Observed pulls 1 of 107. Estimated remaining 18.77. Research probability of crossing the 15% line: 0.7101. No field was missing on this lot. The reason on screen is: "Review trigger is on: the 15% research probability or the recorded pulls need a person, not a drug order."

Risk drivers on WK-008: 1 observed first treatment, 4 sources, an assumed commingling shift of 0.28, a scenario yard shift of 0.05, and 8.7 hours of transport. The uncertainty range is 14.3 to 22.5 first treatments per 100 head. The 0.28 and 0.05 shifts are assumptions, not measured effects.

## Current operating approach

The status quo baseline policy: every active cohort on `status_quo` pen checks. No group medication in that column. It is the comparison point for everything below.

## Parameter assumptions

Assumptions on screen: inclusive loss $151.18 per first treatment, from Rojas, a metaphylaxis scenario cost of $23.60 per head (the Rojas price), hypothetical effectiveness 0.5, and labor $18 per hour. These are historical study parameters used as assumptions. The $151.18 is inclusive and is not added on top of its component costs. Monitoring does not prevent disease. The $23.60 price changes only the hypothetical column.

## Alternatives

Three alternatives considered, from the same cohorts.

| Case | What it is | Projected total | Modeled burden | Labor hours | Courses |
|---|---|---:|---:|---:|---:|
| Current operating approach | Pen checks already used on the yard | $95,230.05 | 606.1 | 200.0 | 0 |
| Proposed schedule | The CP-SAT week. Review slots, no drug | $97,148.85 | 606.1 | 261.6 | 0 |
| Hypothetical protocol | Not executed. Applied only in this column | $117,240.86 | 577.7 | 261.6 | 1,033 |

Modeled burden is expected first treatments, not animals already treated. Courses are antimicrobial-exposed head. One animal on a group protocol is one course. Current courses are 0. Proposed courses are 0, because those packages do not administer a drug. Hypothetical courses are 1,033 at the Rojas price of $23.60 per head, and only if effectiveness 0.5 holds. The hypothetical is a what-if for comparison. It is not a recommendation.

The application's own wording: the proposed schedule changes labor cost by $1,109 and does not change modeled disease burden. The hypothetical protocol changes projected total cost by $22,011 if the effectiveness assumption holds. That is not a statement that the plan will save that amount.

## Optimization results

Full crew (1.00). Generate today's plan returns 100 assignments and 7 unmet clinical reviews. The plan label is "Feasible, not proved." and the note beneath it reads "Solver FEASIBLE." on the 3.0-second solve that was first verified, or "Solver OPTIMAL." on solves that finish inside the limit. Both appear with the same 7 unmet. The first verified solve left PN-018, PC-019, PC-020, PC-017, PC-009, PC-012, and PC-006 unmet. The message: "7 clinical review obligations do not fit. They were not dropped from the requirement list."

The 7 are a real capacity result, not a bug. A second solve on the same seed with a 12-second limit also returned exactly 7, with PN-012 in place of PN-018. The identity of the seventh lot can change between solves. The counts of 7 and the comparison totals above did not. The cause is the verified Prairie Central veterinary-slot gap: 7 needed and 3 available in the first 3 days. The shortage line names only that Prairie Central gap, which is 4 of the 7. It is not a full breakdown of all 7, and this document does not claim one.

Crew cut to 0.40. The week does not fit. The solver returns `INFEASIBLE`, 0 assignments, 24 unmet reviews, and the witness "PC staff hours does not fit PC-022." The screen also shows "17 moved off the week" with the 17 lot IDs. The plan label is "Does not fit."

Crew back to 1.00. A fresh solve returns 100 assignments and 7 unmet again, with the plan label "Feasible, not proved." The 7 are still listed.

## Recommendation

Keep the proposed week as a staffing plan for pen checks and veterinary-review slots. Do not read it as permission to medicate. WK-008 is the lot to open the morning on. Its review stays a review. Packages flagged for veterinary review are slots, not prescriptions. Do not adopt the hypothetical protocol on the strength of this table. The 7 unmet reviews stay on the manager's list.

## Projected consequences

Health: modeled burden is 606.1 first treatments for both the current approach and the proposed schedule, so the proposed week does not change modeled disease. The hypothetical burden of 577.7 holds only if effectiveness 0.5 holds. Cost: the proposed week changes labor cost by $1,109. Antimicrobial courses: current 0, proposed 0, hypothetical 1,033. At full crew 7 reviews remain unmet. At crew 0.40 no schedule exists. These are modeled consequences on synthetic data, not forecasts.

## Uncertainty

The range on WK-008 is 14.3 to 22.5 first treatments per 100 head. It is an assumption-dependent range, not a validated confidence interval. The 0.7101 research probability depends on assumed coefficients. An unknown field widens a range and is never treated as low risk. The hypothetical column depends on effectiveness 0.5, a historical study parameter. The data are synthetic. Which lot fills the seventh unmet seat can change between solves.

## Resources needed

The solver's resources are staff hours, veterinary slots, chute head, and hospital pens, by yard and day, with crew, veterinary, and chute multipliers all at 1.00 for the full-crew result. The proposed week uses 261.6 labor hours against 200.0 for the current approach, at $18 per hour. The scarce resource named by the shortage line is Prairie Central veterinary slots: 7 needed, 3 available in the first 3 days.

## Required veterinary review

Clinical reviews are requirements, not preferences. WK-008's review trigger is on, and the app's own wording is that a veterinary assessment on the week plan is "a review slot, not an authorization to treat." A person decides about any treatment. The tool does not prescribe, does not dose, and does not execute medication. The 7 unmet reviews remain on the requirement list for a person to schedule. They are never dropped.

## Capacity sensitivity

Same lot (WK-008, day 3 of 45) and the same Generate today's plan path. Only the crew control changed. Veterinary slots and chute capacity stayed at 1.00. The crew control moves in steps of 0.05, so 0.70 was available. Each row is what the app displayed in this run.

| Crew | Assignments | Unmet clinical reviews | Status label shown |
|---:|---:|---:|---|
| 0.40 | 0 | 24 | Does not fit. |
| 0.70 | 0 | 24 | Does not fit. |
| 1.00 | 100 | 7 | Feasible, not proved. |

At 0.40 and 0.70 no schedule satisfies the resource limits. The solver returns no assignments and all 24 obligated reviews stay on the requirement list. That 24 is the list of obligated lots, not a solved plan. Only the 1.00 row has a schedule: 100 assignments, with 7 reviews still unmet because the capacity needed to cover them is larger than the capacity available. The shortage line names Prairie Central veterinary slots, 7 needed and 3 available in the first 3 days. In every row the optimizer reports the gap and keeps the reviews on the list. It does not silently drop them.

This is a cliff, not a gradual curve. Below full crew the solver is infeasible and builds no plan at all, so unmet reviews do not fall smoothly as crew rises. Every 0.05 step probed from 0.75 through 0.95 also returned "Does not fit." with 0 assignments. Those steps are not table rows. The table says nothing about any crew level above 1.00.

## What the summary shows

Prepare summary repeats the witness when one exists, names priority lot WK-008, states the recommendation, and includes the course line: current 0, proposed 0, hypothetical 1,033. It also counts cohorts with a missing field and cohorts that are insufficient. On this clock those counts are 51 and 0. A missing field is not treated as low risk.
