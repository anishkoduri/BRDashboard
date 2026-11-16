# BRDashboard design tokens

Named direction: the morning path. Furrow is dropped. Wayfind was dealt and then dropped as a binding theme. Its clarity stays only as a starting point: one destination, one time, one status. The breaks and the reasons are in `docs/decision-record.md`.

## Color

| Token | Value | Use |
|---|---|---|
| Paper | `oklch(96% 0.012 95)` | Page ground |
| Ink | `oklch(20% 0.02 255)` | Text and rules |
| Action | `oklch(46% 0.14 255)` | The one primary key |
| Fits | `oklch(40% 0.08 150)` | A week that fits |
| Does not fit | `oklch(48% 0.16 28)` | A cut, an unmet lot, a thin consequence |

No tangerine. No second accent on the page ground.

## Type

| Role | Face | Weight |
|---|---|---|
| The one big name or sentence | Red Hat Display | 600 |
| Figures and lot ids | Red Hat Mono | 500 |

Both faces are the self-hosted files in `frontend/public/fonts`.

## Surfaces

Quiet grain on the page ground only, drawn with a CSS dot grid. The earlier SVG turbulence filter was removed because it repainted the whole window on every screen change. Cards that decide something use the warm ground and an ink corner. The plan table and the lot list stay flat except for the row tint, so a number stays readable. The focus plate has a 12px radius. Other controls stay square.

## Accent, one meaning each

| Token | Value | Only used for |
|---|---|---|
| Action | `oklch(46% 0.14 255)` | The one next step (Generate today’s plan, Prepare summary) |
| Fits | `oklch(40% 0.08 150)` | A week or lot that fits |
| Does not fit | `oklch(48% 0.16 28)` | A cut, an unmet lot, a thin consequence sentence |
| Priority | `oklch(34% 0.14 310)` | The lot id, the one destination |
| Live | `oklch(46% 0.13 195)` | The bar on the yard, lot, or plan row that is current or just changed |
| Moved | `oklch(40% 0.16 350)` | The crew figure and the count of lots a cut moved |
| Warm ground | `oklch(93% 0.025 85)` | Decorative fill of a focus plate, a crew control, and the current and proposed comparison cards |
| Row tint | `oklch(95.2% 0.012 90)` | Decorative fill of every other lot row and every other plan row |

Warm ground and row tint are not status. They do not use the semantic hues.

## Motion

| Surface | What moves | Trigger | Token |
|---|---|---|---|
| Morning | Four yard chips fill in order | Snapshot loading | 900ms loop, 140ms stagger. Words stay visible. |
| Morning | Focus plate rises 8px | The selected lot changes. The first paint stays still. Returning to Morning does not replay it. | `--motion-rise` 180ms |
| Plan | Consequence plate rises | The week’s sentence changes after a solve or a cut. Opening the plan does not rise. | 180ms |
| Summary | The generated sheet rises | Prepare summary returns the page | 180ms |
| Plan | Seven day chips fill | Scheduling the week, re-planning, loading the week | 900ms loop, 70ms stagger |
| Plan | Changed rows flip on X | A replan changes that row | 180ms, stagger 30ms, then the live bar stays |
| Lot | A line draws | Opening the lot while the snapshot is still loading | 700ms loop. The lot id is on screen as soon as the snapshot is here. |
| Summary | A sheet grows | Loading the snapshot, preparing the summary | 700ms loop |

`prefers-reduced-motion: reduce` sets every animation above to none. Content is in its finished place. Press scale is off. Fail-safe: the sentence is never hidden. The chips and the line sit on top of text that is already readable.
