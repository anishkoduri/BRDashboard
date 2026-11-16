"""Reproduce the demonstration numbers from the recorded seed.

Regenerates the synthetic set into a temporary folder (data/ and app.sqlite in the
repository are not touched), runs the same Workspace code the API uses, solves the
full-crew week, and prints the figures quoted in docs/demonstration_case.md.

    .\\.venv\\Scripts\\python.exe scripts\\reproduce_results.py

Exit code 0 when every figure matches. The solver status note is printed as returned
(OPTIMAL or FEASIBLE) and is not checked, because CP-SAT may return either.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.generate import write_dataset  # noqa: E402
from app.service import Workspace  # noqa: E402

EXPECTED = {
    "priority lot": "WK-008",
    "day on feed": 3,
    "assignments": 100,
    "unmet clinical reviews": 7,
    "plan status": "Feasible, not proved.",
    "courses current": 0,
    "courses proposed": 0,
    "courses hypothetical": 1033,
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def plan_status(plan: dict) -> str:
    # Same mapping as the Plan screen (frontend/app/planner/page.tsx).
    if plan["solver_status"] == "INFEASIBLE":
        return "Does not fit."
    return "Proved optimal." if plan["proved_optimal"] else "Feasible, not proved."


def run() -> dict:
    seed = json.loads((ROOT / "data" / "provenance" / "provenance.json").read_text(encoding="utf-8"))["seed"]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        (root / "data").mkdir()
        write_dataset(root, seed)
        same = all(
            read_rows(root / "data" / "demo" / name) == read_rows(ROOT / "data" / "demo" / name)
            for name in ("cohorts.csv", "health_events.csv", "yards.csv")
        )
        ws = Workspace(root)
        try:
            lot = next(row for row in ws.snapshot()["cohorts"] if row["active"] and row["clinical_obligation"])
            plan = ws.solve()
            courses = ws.compare()
        finally:
            ws.db.close()
    return {
        "seed": seed,
        "matches data/demo": same,
        "clock": str(ws.clock),
        "priority lot": lot["cohort_id"],
        "day on feed": lot["day_on_feed"],
        "assignments": len(plan["assignments"]),
        "unmet clinical reviews": len(plan["unmet_clinical"]),
        "plan status": plan_status(plan),
        "solver note": f"Solver {plan['solver_status']}.",
        "courses current": int(courses["baseline"]["antimicrobial_exposed_head"]),
        "courses proposed": int(courses["optimized"]["antimicrobial_exposed_head"]),
        "courses hypothetical": int(courses["alternative"]["antimicrobial_exposed_head"]),
    }


def main() -> int:
    got = run()
    print(f"Seed {got['seed']}; regenerated files match data/demo: {got['matches data/demo']}; data clock {got['clock']}")
    print(f"Priority lot: {got['priority lot']} (Day {got['day on feed']} of 45)")
    print(f"Assignments: {got['assignments']}")
    print(f"Unmet clinical reviews: {got['unmet clinical reviews']}")
    print(f"Plan status: {got['plan status']}")
    print(f"Solver status note (as returned): {got['solver note']}")
    print(f"Antimicrobial courses: current {got['courses current']} / proposed {got['courses proposed']} / hypothetical {got['courses hypothetical']:,}")
    bad = [f"{key}: expected {want!r}, got {got[key]!r}" for key, want in EXPECTED.items() if got[key] != want]
    if not got["matches data/demo"]:
        bad.append("regenerated data differs from data/demo")
    print("MATCH: every figure equals docs/demonstration_case.md" if not bad else "MISMATCH:\n  " + "\n  ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
