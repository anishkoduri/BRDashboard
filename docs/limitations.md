# Limitations

- The yards, pens, and cohorts are synthetic. Provenance is `data/provenance/provenance.json`. They are not Merck observations and not a clinical validation set.
- Rojas et al. 2022 supplies the 45-day cohort outcome, the 15% research classification, and the historical cost inputs ($151.18 lost value per morbid animal, effectiveness assumed at 0.5). Those inputs are assumptions, not 2026 prices.
- Matching a published mean in the generator is not validation. The assessment does not see the generator’s noise term.
- `p_exceed_15` is the model’s probability of crossing that research line. It is not a diagnosis and not a treatment threshold.
- A cohort missing one or two fields is still ranked. A missing field is not treated as low risk. Three or more missing fields is the line for “not enough for a confident recommendation.”
- Extra pen checks do not reduce modeled disease burden.
- The hypothetical protocol column is not executed. It moves only when its effectiveness assumption is changed.
- Medication-related packages are veterinary-review slots. The role lens can mark a simulated status. That status is not an authorization to treat.
- CP-SAT can return `OPTIMAL` while `proved_optimal` is false. The screen then says “Feasible, not proved.” An infeasible cut lists the reviews that do not fit. It does not drop them.
- The inclusive morbidity loss is not added on top of the disease, performance, and mortality components. The cost parts are checked against the total.
- No live weather service is called. Seasons in the file are synthetic draws.
