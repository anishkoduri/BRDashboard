"""Decision summary and named overlay rows."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(ROOT))

from app.generate import write_dataset  # noqa: E402
from app.service import Workspace  # noqa: E402
import app.main as main  # noqa: E402


def _demo(tmp_path: Path) -> Workspace:
    write_dataset(tmp_path, 20261115)
    return Workspace(tmp_path)


def test_report_includes_schedule_after_solve(tmp_path, monkeypatch):
    workspace = _demo(tmp_path)
    plan = workspace.solve()
    monkeypatch.setattr(main, "workspace", workspace)
    cohort_id, package = next(iter(plan["assignments"].items()))
    started = time.perf_counter()
    html = main.report().body.decode()
    assert time.perf_counter() - started < 2
    assert cohort_id in html
    assert package in html
    assert "Proposed schedule" in html
    assert "Hypothetical" in html
    assert "Unmet clinical reviews" in html
    assert "Not a diagnosis" in html
    assert "Not a prescription" in html
    for unmet_id in plan["unmet_clinical"]:
        assert unmet_id in html


def test_report_stands_alone_with_tradeoffs_and_limits(tmp_path, monkeypatch):
    workspace = _demo(tmp_path)
    workspace.solve()
    monkeypatch.setattr(main, "workspace", workspace)
    html = main.report().body.decode()
    assert "Current operating approach" in html
    assert "Modeled burden" in html
    assert "Antimicrobial-exposed head" in html
    assert "Veterinary review is required" in html
    assert "not a prescription" in html.lower() or "not prescriptions" in html.lower()
    assert "enough history for a confident recommendation" in html
    assert "missing at least one arrival field" in html
    assert "does not change modeled disease burden" in html
    if workspace.plan["binding"] is None:
        assert "No named resource shortage" in html


def test_report_names_the_priority_lot_and_when_it_falls(tmp_path, monkeypatch):
    workspace = _demo(tmp_path)
    workspace.solve()
    monkeypatch.setattr(main, "workspace", workspace)
    snap = workspace.snapshot()
    lot = next(row for row in snap["cohorts"] if row["active"] and row["clinical_obligation"])
    html = main.report().body.decode()
    assert f"Priority lot {lot['cohort_id']}" in html
    assert f"Day {int(lot['day_on_feed'])} of 45" in html
    assert "Recommendation:" in html
    assert "Veterinary review" in html
    assert "one course" in html


def test_yard_roll_matches_observed_counts_and_status_quo_cost(tmp_path):
    from app.model import evaluate_assignment

    workspace = _demo(tmp_path)
    snap = workspace.snapshot()
    for yard in snap["yards"]:
        group = [row for row in snap["cohorts"] if row["active"] and row["yard_id"] == yard["yard_id"]]
        head = sum(row["head"] for row in group)
        observed = sum(row["observed_first"] for row in group)
        assert yard["observed_first"] == observed
        assert yard["observed_per_100"] == (round(100 * observed / head, 2) if head else 0)
        expected = round(sum(evaluate_assignment({
            "cohort_id": row["cohort_id"],
            "cohort_size": row["head"],
            "expected_remaining": row["expected_remaining"],
            "observed_first": row["observed_first"],
        }, "status_quo", workspace.assumptions)["total_cost"] for row in group), 2)
        assert yard["current_approach_cost"] == expected


def test_committed_upload_is_what_the_planner_reads(tmp_path):
    workspace = _demo(tmp_path)
    workspace.commit_import([{
        "cohort_id": "NEW-1",
        "yard_id": "PN",
        "pen_id": "PN-P09",
        "arrival_date": "2026-03-01",
        "cohort_size": 80,
        "mean_arrival_weight_lb": 500,
        "source_type": "commingled",
        "number_of_sources": 3,
        "transport_duration_hours": 16,
        "vaccination_history": "unknown",
        "pen_area_per_head": 12,
        "arrival_season": "winter",
    }])
    plan = workspace.solve()
    assert plan["assignments"].get("NEW-1") or "NEW-1" in plan["unmet_clinical"]
    assert "WK-008" not in plan["assignments"]


def test_report_without_plan_does_not_invent_rows(tmp_path, monkeypatch):
    workspace = _demo(tmp_path)
    assert workspace.plan is None
    monkeypatch.setattr(main, "workspace", workspace)
    html = main.report().body.decode()
    assert "The week has not been generated." in html
    assert "Proposed schedule" not in html
    assert "<td>" not in html
    assert workspace.plan is None
    assert "Not a diagnosis" in html
    assert "Not a prescription" in html


class _ShortRowQuery:
    """Returns one truncated row ahead of the real query result."""

    def __init__(self, connection, marker: str) -> None:
        self.connection = connection
        self.marker = marker

    def execute(self, sql, *args, **kwargs):
        result = self.connection.execute(sql, *args, **kwargs)
        if self.marker not in sql:
            return result

        class Mixed:
            def fetchall(_self):
                return [("short",), *result.fetchall()]

        return Mixed()


def test_short_overlay_row_does_not_raise_index_error(tmp_path):
    workspace = _demo(tmp_path)
    cohort_id = workspace.cohorts[0]["cohort_id"]
    workspace.add_observation(cohort_id, 3, 2, "pen check", "rider")
    workspace.db = _ShortRowQuery(workspace.db, "FROM overlay")
    rows = workspace.overlays()
    assert rows == [
        {
            "cohort_id": cohort_id,
            "day": 3,
            "detected": 2,
            "note": "pen check",
            "actor": "rider",
            "ts": rows[0]["ts"],
        }
    ]


def test_short_review_row_does_not_raise_index_error(tmp_path):
    workspace = _demo(tmp_path)
    cohort_id = workspace.cohorts[0]["cohort_id"]
    workspace.set_review(cohort_id, "needs_clinical_review", "veterinarian", "look")
    workspace.db = _ShortRowQuery(workspace.db, "FROM review")
    reviews = workspace.reviews()
    assert reviews[cohort_id]["status"] == "needs_clinical_review"
    assert reviews[cohort_id]["actor"] == "veterinarian"
    assert reviews[cohort_id]["note"] == "look"
    assert "short" not in reviews
