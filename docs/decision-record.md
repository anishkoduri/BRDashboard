# BRDashboard decision record

Grill-me status: the build prompt already answered every product decision. No question was re-asked. This file records those decisions. The user then said to run the plugin from the start, orchestrate with subagents, apply the design package on all UI, and verify with browser-qa. Work stays in `C:\Users\heman\BRDashboard`.

Hours left: about 27 hours, calculated from the stated deadline of 15 Nov 2026, 11:00 PM CST, against the session clock of 14 Nov 2026, ~7:30 PM CST. Assumed from the deadline, not a separate hours answer.

Platform: web. Next.js + React + TypeScript + Tailwind + shadcn/ui frontend. Python + FastAPI + Pydantic + NumPy + Pandas + SciPy + OR-Tools CP-SAT backend. SQLite for local persistence. pytest + Playwright.

Design direction: the morning path, not a binding Hallmark theme. Furrow is dropped (the manila survey made every number equal). Wayfind was dealt and then dropped as a constraint. Its clarity stays as a starting point only: one destination, one time, one status. The earlier UI snapshot was removed. The live screens are in `frontend/app/`.

Breaks from Wayfind, each with a reason:

- Two status colors plus one action blue. Wayfind allows cobalt and amber-on-ink only. A manager has to see “fits” and “does not fit” before reading a sentence.
- The lot name uses the already self-hosted Red Hat Display. Figures use Red Hat Mono. Wayfind is mono on every line. One face made every number the same rank. No new font download.
- A quiet grain sits on the page ground only. Cards, the plan list, and tables stay flat. Wayfind forbids texture. The ground is a place. The decision surface stays flat so the number stays readable.
- When a staff cut returns, the consequence plate rises into place in about 180ms and changed lots follow in short steps. Reduced motion swaps instantly. Wayfind is a stiff one-step color change. The wow is seeing the week move.
- The focus plate has a 12px radius. Other controls stay square. Wayfind is square everywhere. The plate has to separate from the yard strip.

Palette: daylight paper `oklch(96% 0.012 95)`, ink `oklch(20% 0.02 255)`, action `oklch(46% 0.14 255)`, fits `oklch(40% 0.08 150)`, does-not-fit `oklch(48% 0.16 28)`. Tangerine is not used.

Motion and accent, added after the morning screens were up. Feel is the existing 180ms rise (A10 feedback that settles, B2 inside 150–250ms, A17 so a wait is named within a glance). `motion/react` is not installed. The same durations live as `--motion-rise` and `--motion-ease`. Recorded gap: no new animation library.

- Priority violet `oklch(34% 0.14 310)` is only the lot id. It is the one destination.
- Live cyan `oklch(46% 0.13 195)` is only the mark on the yard, lot, or plan row that is current or just changed. It is not a status.
- Moved magenta `oklch(40% 0.16 350)` is only the crew figure and the count of lots the cut moved.
- Fit and does-not-fit stay the only status colors. Action blue stays the one next step. A selected yard is no longer filled with action blue, so blue is not also “selected.”

Loading marks name the work: four yard chips while the snapshot is read, seven day chips while the week is scheduled or replanned, a line while a lot file opens, a sheet while the summary is prepared. A screen change paints the next page in place. The 180ms rise plays only when the selected lot changes or the week’s sentence changes, not on every visit (A10: motion answers a change; a route is not a change to hide). The page grain is a CSS dot grid. The SVG turbulence filter is gone because it repainted the window on each switch. Changed plan rows flip on the horizontal axis in the same 180ms, staggered 30ms, and keep the live mark. Reduced motion sets every one of those animations to none and leaves the content in its finished place.

## Decisions already made

- Product: BRDashboard. Tagline: From cattle health data to better decisions.
- Users: feedyard manager and cattle health manager. Supporting: pen rider, processing supervisor, veterinarian, enterprise leadership.
- Decision unit: arrival cohort. Secondary: yard and pen. Animal-level data is optional.
- Data: literature-informed synthetic demo. Four fictional yards (Panhandle North, High Plains South, Western Kansas, Prairie Central). Seeded generator. 80–200 cohorts. CSV import required. Never present synthetic rows as Merck observations.
- Science: 45-day horizon. Rojas 15% is a research threshold, not a clinical cutoff. Dynamic reassessment. Explicit uncertainty. No fabricated validation. No autonomous prescribing. Veterinary review required for medication options.
- Centerpiece: Resource Planner / CP-SAT optimizer, not the prediction chart.
- Scope order: P0 fully working, then P1, then P2 only if stable.
- Constraints: local-first, free tier, no paid APIs, offline-capable core, do not delete pre-existing files.
- Demo video: at first the user said do not film and `/demo` stayed off. Later the user invoked `/demo` and supplied the script and a narration recording (`KEY-RECEIPT: no`, no key needed). The 1:49 video is `demo.mp4` at `BRDashboard/demo.mp4` in the submission ZIP.
- Build order from the user, after the shortlist was approved: demo-path gaps first (planner shows the solver schedule, the report generates the summary, a failed snapshot says so), then the rest of the approved shortlist, then README, technical brief, demonstration case, AI disclosure, and Playwright. P0 working dashboard before those docs.
- Deadline risk: the one-yard infeasibility witness is in the planner. At staff 0.40 the recorded sentence is “PC staff hours does not fit PC-022.”

## Spec audit

The printed summary leads with the witness (or “No named resource shortage”), the assumption-dependent wording, and the three-column trade-off table. The 100-row schedule follows those lines. A cohort missing one field is counted separately from a cohort missing three or more. The second line is “not enough for a confident recommendation,” and this clock has 0 such cohorts. The lot page says that sentence only when the flag is true. PC-005 shows `vaccination_history` missing and does not use that sentence. The summary plate reserves 280px so the Prepare button stays put when the snapshot sentence replaces the loading mark. Measured after load and after Prepare: plate 280px, button top 363px both times.

The morning path now shows the 45-day window, the model’s own arrival factors, and a four-yard operating table. Veterinary-slot and chute multipliers replan because they are solver constraints. The Rojas $23.60 metaphylaxis price is shown on Decisions and is not a slider, because that price does not change the CP-SAT assignment.

## Accepted unknowns

- NASA POWER / NOAA weather ingestion: P2. Owner: builder. Resolution: skip unless P0 and P1 are green. Default: seasonal fields already on the synthetic rows.
- Live deployment: optional. Owner: builder. Resolution: local launch is the submission path. Deploy only if `deploy-fast` finds a free route that does not block the demo.
- Model pin: session allowlist has `grok-4.7-high-fast`, not `grok-4.7-high`. Owner: orchestrator. Resolution: 4.7-high-fast for decision subagents, `cursor-grok-4.6-high-fast` for scout and mechanical work.

## Cut substance

None yet. Existing engines (seeded generator, beta-style risk update, cost reconciliation, CP-SAT) stay. A later cut must be named here with a reason.
