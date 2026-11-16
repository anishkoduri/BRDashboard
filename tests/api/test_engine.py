"""Behavior tests for generation, risk, cost, and the scheduler."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(ROOT))

from app.generate import build_dataset  # noqa: E402
from app.model import (  # noqa: E402
    assess_cohort,
    clinical_obligation,
    covariate_linear,
    evaluate_assignment,
    sum_plan,
)
from app.optimize import solve_plan, violates_capacity  # noqa: E402


def _row(**overrides):
    base = {
        "cohort_id": "PN-001",
        "yard_id": "PN",
        "cohort_size": 100,
        "mean_arrival_weight_lb": 700,
        "number_of_sources": 1,
        "source_type": "single_ranch",
        "transport_duration_hours": 4,
        "arrival_season": "spring",
        "pen_area_per_head": 20,
        "sex_group": "steer",
        "vaccination_history": "recorded_complete",
        "scenario_yard_offset": 0,
    }
    base.update(overrides)
    return base


def test_same_seed_reproduces_cohorts():
    first = build_dataset(20261115)
    second = build_dataset(20261115)
    assert [row["cohort_id"] for row in first["cohorts"]] == [row["cohort_id"] for row in second["cohorts"]]
    assert [row["sim_detected_45"] for row in first["cohorts"]] == [row["sim_detected_45"] for row in second["cohorts"]]
    assert len({row["cohort_id"] for row in first["cohorts"]}) == len(first["cohorts"])


def test_events_stay_inside_headcount_and_after_arrival():
    data = build_dataset(7)
    by_id = {row["cohort_id"]: row for row in data["cohorts"]}
    detected: dict[str, int] = {}
    for event in data["events"]:
        cohort = by_id[event["cohort_id"]]
        assert event["day_on_feed"] >= 1
        assert event["event_date"] >= cohort["arrival_date"]
        assert event["detected_first_count"] <= event["latent_first_count"]
        detected[event["cohort_id"]] = detected.get(event["cohort_id"], 0) + event["detected_first_count"]
    for cohort_id, count in detected.items():
        assert count <= by_id[cohort_id]["cohort_size"]
        assert count == by_id[cohort_id]["sim_detected_45"]


def test_probabilities_and_remaining_stay_in_bounds():
    row = _row()
    early = assess_cohort(row, 0, 0, -2.9)
    assert 0 <= early["p_exceed_15"] <= 1
    assert 0 <= early["expected_remaining"] <= row["cohort_size"]
    late = assess_cohort(row, 4, 45, -2.9)
    assert late["expected_remaining"] == 0
    assert late["observed_first"] == 4


def test_future_events_are_not_an_input():
    row = _row()
    before = assess_cohort(row, 0, 5, -2.9)
    # A later observation must not be passed in by the caller. Feeding only day-5 counts
    # keeps the day-5 assessment stable when a day-20 count exists elsewhere.
    assert before["observed_first"] == 0
    leaked = assess_cohort(row, 12, 5, -2.9)
    assert leaked["observed_first"] == 12
    assert leaked["updated_mu"] != before["updated_mu"]


def test_unknown_vaccination_is_not_protective():
    known = covariate_linear(_row(vaccination_history="recorded_complete"), -2.9)
    unknown = covariate_linear(_row(vaccination_history="unknown"), -2.9)
    none = covariate_linear(_row(vaccination_history="recorded_none"), -2.9)
    assert unknown["mu"] > known["mu"]
    assert unknown["mu"] == pytest.approx(none["mu"])
    assert "vaccination_history" in unknown["missing"]
    assert unknown["kappa"] < known["kappa"]


def test_monitoring_does_not_reduce_burden_and_costs_reconcile():
    cohort = {"cohort_id": "PN-001", "cohort_size": 100, "expected_remaining": 6.0, "observed_first": 2}
    assumptions = {
        "labor_cost_per_hour": 18,
        "inclusive_loss_per_first_treatment": 151.18,
        "use_inclusive_morbidity_loss": True,
        "component_treatment_cost": 999,
        "performance_loss_per_case": 999,
        "mortality_loss_per_head": 9999,
    }
    base = evaluate_assignment(cohort, "status_quo", assumptions)
    watched = evaluate_assignment(cohort, "enhanced_observation", assumptions)
    assert watched["modeled_burden"] == base["modeled_burden"]
    assert watched["labor_cost"] > base["labor_cost"]
    assert watched["performance_cost"] == 0
    assert watched["mortality_cost"] == 0
    protocol = {"cohort_ids": ["PN-001"], "effectiveness": 0.0, "cost_per_head": 23.60}
    zero = evaluate_assignment(cohort, "status_quo", assumptions, protocol)
    assert zero["expected_remaining"] == base["expected_remaining"]
    assert zero["protocol_cost"] == pytest.approx(2360.0)
    totals = sum_plan([base, watched])
    assert totals["total_cost"] == pytest.approx(base["total_cost"] + watched["total_cost"])


def test_positive_effect_reduces_only_remaining_burden():
    cohort = {"cohort_id": "PN-001", "cohort_size": 80, "expected_remaining": 10.0, "observed_first": 3}
    assumptions = {
        "labor_cost_per_hour": 18,
        "inclusive_loss_per_first_treatment": 100,
        "use_inclusive_morbidity_loss": True,
    }
    protocol = {"cohort_ids": ["PN-001"], "effectiveness": 0.5, "cost_per_head": 10}
    result = evaluate_assignment(cohort, "status_quo", assumptions, protocol)
    assert result["expected_remaining"] == pytest.approx(5.0)
    assert result["modeled_burden"] == pytest.approx(8.0)


def _planner_cohort(cohort_id: str, yard: str, remaining: float, obligation: bool) -> dict:
    return {
        "cohort_id": cohort_id,
        "yard_id": yard,
        "expected_remaining": remaining,
        "incomplete_history": False,
        "clinical_obligation": obligation,
        "observed_first": 2 if obligation else 0,
        "cohort_size": 100,
    }


def test_solver_respects_capacity_and_does_not_execute_medication():
    cohorts = [
        _planner_cohort("PN-001", "PN", 8, True),
        _planner_cohort("PN-002", "PN", 1, False),
        _planner_cohort("PN-003", "PN", 6, False),
        _planner_cohort("PC-001", "PC", 7, True),
    ]
    yards = {
        "PN": {"staff_hours_per_day": 20, "vet_slots_per_day": 2, "chute_head_per_day": 80, "hospital_pens": 4},
        "PC": {"staff_hours_per_day": 12, "vet_slots_per_day": 1, "chute_head_per_day": 40, "hospital_pens": 2},
    }
    plan = solve_plan(cohorts, yards, time_limit=5)
    assert plan["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    assert plan["medication_executed"] is False
    assert not any("metaphylaxis" in name for name in plan["assignments"].values())
    assert violates_capacity(plan["usage"]) == []
    assert plan["assignments"]["PN-001"].startswith("vet_day") or plan["assignments"]["PN-001"].startswith("enhanced_vet")


def test_zero_vet_slots_keeps_the_obligation_visible():
    cohorts = [_planner_cohort("PC-001", "PC", 9, True), _planner_cohort("PC-002", "PC", 1, False)]
    yards = {"PC": {"staff_hours_per_day": 16, "vet_slots_per_day": 0, "chute_head_per_day": 40, "hospital_pens": 4}}
    plan = solve_plan(cohorts, yards, time_limit=5)
    assert "PC-001" in plan["unmet_clinical"] or plan["clinical_label"] in {"unmet_care", "infeasible"}
    assert plan["clinical_label"] != "optimal"
    if plan["assignments"]:
        assert not plan["assignments"]["PC-001"].startswith("vet_day")
        assert violates_capacity(plan["usage"]) == []


def test_tighter_staff_changes_or_blocks_the_plan():
    cohorts = [_planner_cohort(f"PN-{i:03d}", "PN", float(8 - i), i == 1) for i in range(1, 8)]
    wide = {"PN": {"staff_hours_per_day": 30, "vet_slots_per_day": 3, "chute_head_per_day": 100, "hospital_pens": 6}}
    tight = {"PN": {"staff_hours_per_day": 6, "vet_slots_per_day": 3, "chute_head_per_day": 100, "hospital_pens": 6}}
    full = solve_plan(cohorts, wide, time_limit=5)
    short = solve_plan(cohorts, tight, time_limit=5)
    assert full["assignments"] != short["assignments"] or short["clinical_label"] in {"unmet_care", "infeasible"}
    assert violates_capacity(full["usage"]) == []
    if short["usage"]:
        assert violates_capacity(short["usage"]) == []


def test_obligation_rule_is_not_a_drug_order():
    assessment = {"p_exceed_15": 0.6, "observed_first": 0, "day_on_feed": 10}
    assert clinical_obligation(assessment, 0) is True


def test_calibration_hits_the_published_mean():
    report = build_dataset(20261115)["calibration"]
    assert abs(report["latent_mean"] - 0.063) < 0.002
    assert report["generator_intercept"] < -3.0
    assert "not clinical validation" in report["note"]


def test_unmet_review_is_not_described_as_routine():
    from app.explain import explain_cohort

    cohort = {"cohort_id": "PC-001", "insufficient": False, "clinical_obligation": True, "missing": [], "factors": []}
    text = explain_cohort(cohort, "status_quo", None, True)
    assert "No slot fit" in text["how_this_differs_from_baseline"]
    assert "usual pen-check rotation" not in text["how_this_differs_from_baseline"]


def test_earlier_clock_hides_later_events(tmp_path):
    from app.generate import write_dataset
    from app.service import Workspace

    write_dataset(tmp_path, 20261115)
    workspace = Workspace(tmp_path)
    late = {row["cohort_id"]: row["observed_first"] for row in workspace.cohort_views()}
    workspace.set_clock("2026-02-08")
    early = {row["cohort_id"]: row["observed_first"] for row in workspace.cohort_views()}
    assert sum(early.values()) < sum(late.values())
    workspace.set_clock("2026-03-18")
