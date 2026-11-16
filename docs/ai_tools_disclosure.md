# External resources and AI tools

## Data sources

The cohorts are synthetic. Generator `backend/app/generate.py`, seed 20261115, files in `data/demo/`. Provenance: `data/provenance/provenance.json`. Dictionary: `data/dictionary/data_dictionary.csv`. They are not Merck records.

Literature used as context, not as fitted weights. The ledger is `backend/app/evidence.py` and the Evidence screen. The PDFs are in `research/sources/`.

- Rojas et al. 2022, Predicting BRD risk in the first 45 days post arrival. doi:10.3390/pathogens11040442. Cohort unit, 45-day outcome, 15% research line, and the historical cost inputs used as assumptions.
- Adekunle et al. 2026, Mapping variability in BRD risk factors. doi:10.3390/ani16111726. Which arrival fields are collected.
- Adekunle and Kaniyamattam 2026, BRD epidemiological drivers. doi:10.3390/agriculture16030311.
- Weber et al. 2024, BRD morbidity and net return. Poster in `research/sources`. Context only. A lower treatment share is not a profit proof.
- Johnson and Pendell 2017, Market impacts of reducing BRD. doi:10.3389/fvets.2017.00189. Context only.
- USDA APHIS, Antimicrobial use and stewardship on U.S. feedlots, 2017. Stewardship context only.

NASA POWER and NOAA were not called. Seasons in the file are synthetic draws.

## Software used by the running application

- OR-Tools CP-SAT, called locally. No solver API.
- Python packages in `backend/requirements.txt`: FastAPI, Pydantic, NumPy, SciPy, Pandas, OR-Tools, pytest, python-multipart, openpyxl, pypdf, fpdf2, fonttools.
- Frontend packages in `frontend/package.json`: Next.js, React, TypeScript, Tailwind, and the libraries listed there.
- Self-hosted Red Hat Display and Red Hat Mono files in `frontend/public/fonts`.

No paid API, no weather service, and no remote model is called at runtime.

## Tools used only to check the build

- axe-core 4.10.3, loaded in the browser from jsDelivr during accessibility checks. It is not a dependency of the dashboard.
- Playwright, a development dependency in the root `package.json`, for the tests in `tests/e2e/`. It is not part of the running app.

## AI tools used to build the repository

The application code, tests, and these documents were written in Cursor with AI assistance, and the team reviewed and checked all of it. The agent ran the local API and the test suite and copied figures from those runs into `docs/demonstration_case.md` and `docs/technical-brief.md`.

AI tools and models used: Cursor with the hackathon-ecc plugin (its agents, skills, and rules); Grok 4.7 High (`grok-4.7-high`) as orchestrator and design lead; Grok 4.6 High Fast (`cursor-grok-4.6-high-fast`) for fast execution workers, such as the read-only scout; and Claude Sonnet 4.5 (Anthropic) for the final polish prompts on Nov 15, 2026, covering the README, technical brief, demonstration case, and reproducibility fixes.

Division of labor: the concept, approach, decisions, and planning for this submission were the team's own work. AI tools were used only for implementation assistance and documentation drafting under the team's direction, and all results, numbers, and claims were verified by the team before submission.

Decisions the team made and handed to the AI tools as requirements (recorded in `docs/decision-record.md`):

- The product and its users: a feedyard manager's decision aid, with the arrival cohort as the decision unit.
- The data approach: a seeded, literature-informed synthetic set of four fictional yards, never presented as Merck observations, plus a required CSV import.
- The science limits: a 45-day horizon, the Rojas 15% line treated as a research threshold and not a clinical cutoff, explicit uncertainty, no autonomous prescribing, and veterinary review required for any medication option.
- The centerpiece: the CP-SAT resource planner, not the prediction chart.
- The scope order (working core first, extras only if stable), the local-first and free-tier constraints, and the build order.
- The wording rules for results: a plan with unmet reviews is labeled "Feasible, not proved." and never "optimal"; the shortage line names only Prairie Central's gap of 4 of the 7 and does not claim a full breakdown; the demo video uses only the approved numbers.
- The demo-video script, which the team wrote and supplied word for word, and the narration recording the team supplied.

Work the team did itself:

- Research and ideation: the team did the literature research (the sources in `research/sources/` and the evidence ledger) and the ideation that shaped the concept and approach.
- Review: the team hand-checked every number, every submission file, and the code before submission.

No other generative model was used to invent scientific results, cohort rows, or economic outcomes. No image generator was used.

The demo video, `demo.mp4` at the root of the submission ZIP, was assembled in Cursor by an AI agent. Playwright filmed the local dashboard, Remotion rendered the cut, and ffmpeg encoded it. The narration is an ElevenLabs text-to-speech recording (voice: George) of the team's script, supplied by the team as an audio file. A local speech-recognition model, faster-whisper, was used only to find the pauses where that recording is cut. None of this is part of the running dashboard.

If a figure in the brief or the demonstration case disagrees with a fresh solve, the fresh solve is the one to trust. CP-SAT may return `FEASIBLE` or `OPTIMAL` on a repeat. The captured full-crew result is the one in the demonstration case: 7 unmet reviews, with the seventh lot allowed to swap.
