# QA notes: out/demo.mp4

Take 2, checked 15 Nov 2026 against `out/qa/sheet_01-03.png` (16 mid-beat stills) and `out/qa-video/sheet_01-08.jpg` (48 frames pulled from the rendered MP4).

## Output

- 1920x1080, 30 fps, H.264 + AAC, 108.99 s (1:49), 71.8 MB. Limit is 130 s.
- `out/demo-small.mp4` is the same cut at 20.3 MB.
- Narration is the supplied recording, cut at pauses into 16 clips. No synthesis, no music bed.
- Loudness: -14.6 LUFS integrated, true peak -1.4 dBFS.

## Automated checks

- `capture/marks.json` warnings: 0. `capture/failures/`: absent.
- `node scripts/qa.mjs`: no blocking findings.
- Speech recognition on the final MP4 audio against the source recording: 278 of 280 words match in order. The two that differ are one word, "feedlots", split differently. Offset holds at about 0.72 s (the 0.7 s lead) from the first line to the last, so no drift and no word lost at a cut.

## Per-beat A/V table

| Beat | Narration | On screen | Supports it |
|---|---|---|---|
| hook | BRD costs feedlots millions. In treatment. In lost performance. In cattle that never make it. | Kinetic type of the same words over the lot ledger; tiles turn red | yes |
| problem | Incomplete records, not enough hours | Same words; tiles thin out; camera pushes to WK-008 | yes |
| product | Turns cattle health data into a plan | Morning view, WK-008 priority lot, four yards | yes |
| watch | First 45 days, ranks every lot, crew and vet slots | Day 3 of 45 line, ranked lot list, Plan capacity sliders | yes |
| morning | Lot WK-008, day 3 of 45 | WK-008 card, "Day 3 of 45" | yes |
| drivers | 1 observed first treatment, four sources, 14 to 22 per hundred head | "Why this lot": observed 1, 4 sources, 14.3 to 22.5 per 100 head | yes |
| generate | One click, 100 assignments | Generate button pressed, Plan view with the week | yes |
| unmet | Seven reviews stay unmet, says so plainly | "7 clinical review obligations do not fit", "Feasible, not proved." | yes |
| cut | Crew to 40 percent, does not fit, 17 lots move off | Crew 0.40, "PC staff hours does not fit PC-022.", "17 moved off the week" | yes |
| restore | Fresh solve, 100 assignments, 7 unmet | Crew 1.00, 7 unmet list, "Feasible, not proved." | yes |
| reason | Vet-slot gap at Prairie Central | Capacity bars, Prairie Central vet row | yes |
| steward | Zero current, zero proposed, hypothetical 1,033 | Decisions: Current 0, Proposed 0, Hypothetical 1033, $23.60 per head | yes |
| vet | Vet stays in charge, nothing prescribed without review | Decisions cards, "Veterinary review required" | yes |
| honest | Knows, assumes, cannot decide | Evidence view "What is known", then Morning | yes |
| docs | Technical brief and demonstration case | Cards naming `docs/technical_brief.pdf` and `docs/demonstration_case.md` | yes |
| close | BRDashboard. From cattle health data to better decisions. | Wordmark and the tagline | yes |

## Not checked

- Nobody listened to the mix. The audio checks above are measurements, not a listen.
- The solver wait after the crew restore is cut from the footage (about 3.5 s). The result shown is the real solve.
