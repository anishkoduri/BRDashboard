# Technical brief

## 1. Problem and evidence

Decision unit and users. BRDashboard is a local decision aid for a feedyard manager and a cattle health manager. The decision unit is an arrival cohort (a lot) during its first 45 days on feed. The question is which lots need a person this week, which pen checks and veterinary-review slots fit the crew, and what that week costs relative to today's pen checks. It is not a diagnosis and not a prescription.

Each active cohort receives one package. Clinical reviews are requirements, not preferences. The resources are staff hours, veterinary slots, chute head, and hospital pens, by yard and day. If a requirement does not fit, it stays on the list. The manager can cut crew and read which yard is short. A separate, unexecuted column asks what a group protocol would do to cost and to antimicrobial courses if its effectiveness assumption held. That column is not an order.

45-day outcomes. For each week the tool reports the package assigned to each cohort, the reviews that did not fit, modeled burden (expected first treatments, not animals already treated), labor hours, projected cost, and antimicrobial-exposed head. One course is one animal on a group protocol. Review slots are not doses.

Data provenance. There is no supplied observational file. The four yards (Panhandle North, High Plains South, Western Kansas, Prairie Central) are literature-informed synthetic demonstration data, seed 20261115, written by `backend/app/generate.py`. They are never real Merck observations and are not a Merck record. Provenance is `data/provenance/provenance.json`; the dictionary is `data/dictionary/data_dictionary.csv`. Seasons are synthetic draws. NASA POWER and NOAA were not called.

Key literature. Rojas et al. 2022 studied 1,733 cohorts and reports a 6.30% mean 45-day first-treatment morbidity. It supplies the cohort unit, the 45-day first-treatment outcome, and a 15% research threshold. That 15% is a research classification, not a clinical threshold. Rojas also supplies the historical inputs used as assumptions below. Adekunle et al. 2026 informs which arrival fields are collected; study counts are not model weights. Weber et al. 2024 and Johnson and Pendell 2017 are the reason a lower treatment share is not treated as a profit proof. USDA APHIS 2017 is stewardship context only. The Evidence screen states what each source is not used for.

Assumptions and limitations. Observed means a count or a field in the file: head, first treatments already recorded, arrival weight, transport hours, source, season, and vaccination when present. Estimated means a model output: remaining first treatments, the probability of crossing the 15% line, and the range. Assumed means a coefficient or a price the file does not measure. Every arrival shift in `backend/app/model.py` is an assumption with a literature-supported direction and a hypothetical size. The yards are synthetic, monitoring does not reduce modeled disease, medication packages are veterinary-review slots, and the role lens marks a simulated authorization status that is not a real approval. There is no weather feed and no authentication.

## 2. Methods

Risk model. Arrival fields set a cohort's expected 45-day rate through a logistic model with assumed coefficients. The cohort's true rate is a Beta distribution around that mean (concentration 40), so a cohort's count is beta-binomial. `p_exceed_15` is the probability that the cohort crosses the 15% research line.

Synthetic generation. `generate.py` draws cohorts and daily first-treatment events from a seeded NumPy generator (seed 20261115). The same seed reproduces the same cohorts. Events fall inside the cohort's headcount and after its arrival. The generator is calibrated to the published 6.3% mean, which is a matching exercise, not validation.

Temporal updating. Each cohort is reassessed daily on the clock day (2026-03-18 in this file). The Beta rate is updated with only the first treatments recorded on or before that day, and a gamma timing curve maps the 45-day rate to the share expected by that day. Events dated after the clock are not an input, so there is no future-data leakage: moving the clock earlier hides later events.

Action and economic model. Inputs from Rojas are historical study parameters and are shown on screen as assumptions: $151.18 inclusive loss per morbid animal, $23.60 per head as the metaphylaxis scenario cost, and effectiveness 0.5. The $151.18 is an inclusive figure and is not added on top of its component costs, so nothing is double-counted. Labor is $18 per hour. Extra pen checks do not change modeled disease. Effectiveness 0.5 applies only to the hypothetical group-protocol column. The $23.60 price changes the hypothetical total and does not change which package is scheduled, so it is not a live slider. Crew, veterinary slots, and chute capacity are live because they are solver constraints.

Constrained optimizer. `backend/app/optimize.py` is OR-Tools CP-SAT. It is safety-first and lexicographic in effect. The first pass keeps obligated cohorts on veterinary packages and must satisfy staff, veterinary, chute, and hospital-pen limits by yard and day. If that pass is infeasible, a second pass allows an unmet flag per obligated cohort. Its penalty (1,000,000) is far larger than the labor and benefit terms, so reviews are met before labor is traded. The service time limit is 3.0 seconds. An infeasible cut says "Does not fit." and the witness sentence names the yard and the resource, for example "PC staff hours does not fit PC-022." It is not a treatment instruction. While any review is unmet, the screen labels the plan "Feasible, not proved." A separate note beneath the label reports the solver's own status, for example "Solver OPTIMAL." The label describes the plan and the note describes the solver.

Uncertainty framework. The range shown on a lot is the 10th to 90th percentile of the cohort's Beta rate under the assumed concentration. It is labeled "assumption-dependent range". It is never presented as a validated confidence interval. A missing field is not treated as low risk and widens the range.

## 3. Results and evaluation

Reproducible demo case. Priority lot WK-008, Day 3 of 45. "Generate today's plan" returns 100 assignments. A cohort missing three or more arrival fields is an insufficient file and the lot page says it is not enough for a confident recommendation. On the 2026-03-18 clock 51 active cohorts miss at least one field (for example PC-005, vaccination history), and none meet the three-field line, so the insufficient count is 0.

The seven unmet reviews. The full-crew solve (staff, chute, and veterinary multipliers 1.00) returned status `FEASIBLE` inside the 3.0-second limit, 100 assignments, and 7 unmet reviews: PN-018, PC-019, PC-020, PC-017, PC-009, PC-012, and PC-006. The app labels the plan "Feasible, not proved." because 7 reviews remain unmet. Later full-crew solves finished inside the 3.0-second limit and the app showed the note "Solver OPTIMAL." beneath that same label, again with 7 unmet. Both facts hold: the solver proved that 7 is the fewest unmet reviews achievable at this capacity, and the plan is still labeled "Feasible, not proved." because those 7 reviews remain unmet. A separate 12-second solve on the same seed, run in a temporary copy that did not replace the running plan, also returned exactly 7, with PN-012 in place of PN-018 as the non-Prairie-Central lot. So the 7 is a capacity result of the model, not a time-limit defect. The shortage line names only Prairie Central veterinary slots: 7 needed, 3 available in the first 3 days, a gap of 4 of the 7. The brief does not break down the other 3. Which lot fills the seventh seat can change between solves; the comparison totals below did not.

Binding constraints. At staff multiplier 0.40 the solver returned `INFEASIBLE`, 0 assignments, 24 unmet reviews, and the witness "PC staff hours does not fit PC-022." Seventeen lots moved off the week. Capacity sensitivity (table in the demonstration case): below full crew the solver is infeasible and builds no plan. Crew 0.40, 0.70, and every 0.05 step through 0.95 returned "Does not fit." with 0 assignments and 24 reviews listed. Only at crew 1.00 does it produce a schedule: 100 assignments, 7 unmet, "Feasible, not proved." This is a cliff, not a gradual curve. At full crew the veterinary-slot gap at Prairie Central is the shortage the app names.

Current versus proposed, health, cost, antimicrobials. Under the visible assumptions the proposed week changes labor cost by $1,109 and does not change modeled disease burden. The remaining $810 of the $1,919 total increase is veterinary-visit fees — 18 clinical-review packages at $45 each.

Current approach: projected total $95,230.05, burden 606.1, labor 200.0 hours, antimicrobial courses 0. Proposed schedule: $97,148.85, burden 606.1, labor 261.6 hours, courses 0. Hypothetical group protocol, not executed: $117,240.86, burden 577.7, labor 261.6 hours, courses 1,033, and only if effectiveness 0.5 holds. This is not a claim that the plan saves $22,011.

Validation results. The 34 backend tests and the Playwright demo-path and screen tests pass. They check generator reproducibility (same seed, same cohorts), events inside headcount and after arrival, no future-data leakage (an earlier clock hides later events), constraint tests (the solver respects capacity, keeps an unmet review visible, and does not execute medication), and that costs reconcile without stacking the inclusive loss. This is synthetic-data recovery only. It is never claimed as clinical validation, and no performance or savings claim is made from it.

Clinical and data limitations. The data are synthetic and the coefficients are hypothetical, so the tool cannot be used to claim real disease reduction, real savings, or clinical accuracy. Matching a published mean is not validation. These figures are one demonstration, not a performance guarantee. A repeat solve may show "Solver OPTIMAL." or "Solver FEASIBLE." in the note; the plan label stays "Feasible, not proved." while any review is unmet.

## References

Rojas HA et al. Predicting bovine respiratory disease risk in the first 45 days post arrival. Pathogens. 2022. doi:10.3390/pathogens11040442.

Adekunle et al. Mapping variability in BRD risk factors. Animals. 2026. doi:10.3390/ani16111726.

Adekunle and Kaniyamattam. BRD epidemiological drivers. Agriculture. 2026. doi:10.3390/agriculture16030311.

Weber et al. Evaluation of BRD on net return. 2024. Poster in `research/sources`.

Johnson KK, Pendell DL. Market impacts of reducing BRD. Front Vet Sci. 2017. doi:10.3389/fvets.2017.00189.

USDA APHIS. Antimicrobial use and stewardship on U.S. feedlots, 2017.
