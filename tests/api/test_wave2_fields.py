"""Assignment diff, binding sentence, distance to trigger, and monitoring identity."""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(ROOT))

from app.generate import write_dataset  # noqa: E402
from app.model import assess_cohort, clinical_obligation, evaluate_assignment  # noqa: E402
import app.main as main  # noqa: E402
import app.model as model  # noqa: E402
import app.service as service_module  # noqa: E402
from app.service import Workspace  # noqa: E402


def _healthy(head: int) -> dict:
    return {
        "cohort_id": "PN-001",
        "yard_id": "PN",
        "cohort_size": head,
        "mean_arrival_weight_lb": 760,
        "number_of_sources": 1,
        "source_type": "single_ranch",
        "transport_duration_hours": 4,
        "arrival_season": "spring",
        "pen_area_per_head": 22,
        "sex_group": "steer",
        "vaccination_history": "recorded_complete",
        "scenario_yard_offset": 0,
    }


def _oracle(row: dict, observed: int, day: int, intercept: float, flags: int) -> int | None:
    """Exact 1..remaining scan. The implementation may step; this is the smallest flip."""
    head = int(row["cohort_size"])
    if clinical_obligation(assess_cohort(row, observed, min(day, 45), intercept), flags, head) and day <= 45:
        return None
    remaining = max(head - observed, 0)
    for extra in range(1, remaining + 1):
        if day > 45:
            return None
        assessment = assess_cohort(row, observed + extra, min(day, 45), intercept)
        if clinical_obligation(assessment, flags, head):
            return extra
    return None


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _tiny(tmp_path: Path, cohorts: list[dict], events: list[dict], yards: list[dict]) -> Workspace:
    demo = tmp_path / "data" / "demo"
    _write_csv(demo / "cohorts.csv", cohorts)
    _write_csv(demo / "health_events.csv", events)
    _write_csv(demo / "yards.csv", yards)
    (demo / "assumptions.json").write_text(json.dumps({"assessment_intercept": -2.9}), encoding="utf-8")
    (demo / "provenance.json").write_text(json.dumps({"seed": 1}), encoding="utf-8")
    return Workspace(tmp_path)


def _cohort(cohort_id: str, arrival: str, flags: int) -> dict:
    return {
        "cohort_id": cohort_id,
        "yard_id": "PN",
        "pen_id": "PN-P01",
        "arrival_date": arrival,
        "cohort_size": 40,
        "sex_group": "steer",
        "source_type": "single_ranch",
        "number_of_sources": 1,
        "transport_duration_hours": 4,
        "vaccination_history": "recorded_complete",
        "pen_area_per_head": 22,
        "arrival_season": "spring",
        "mean_arrival_weight_lb": 760,
        "scenario_yard_offset": 0,
        "respiratory_observation_count": flags,
        "bunk_space_per_head": 0.4,
        "receiving_ration_category": "starter",
        "prior_metaphylaxis_status": "unknown",
        "water_access_status": "available",
        "weaning_history": "weaned",
        "prior_health_history": "unremarkable",
    }


def _event(cohort_id: str, detected: int) -> dict:
    return {
        "cohort_id": cohort_id,
        "day_on_feed": 3,
        "event_date": "2026-03-03",
        "detected_first_count": detected,
        "latent_first_count": detected,
        "subsequent_count": 0,
        "mortality_count": 0,
    }


def _yard(staff: float, vet: int) -> dict:
    return {
        "yard_id": "PN",
        "name": "Panhandle North",
        "region": "test",
        "staff_hours_per_day": staff,
        "chute_head_per_day": 80,
        "vet_slots_per_day": vet,
        "hospital_pens": 6,
        "labor_cost_per_hour": 18,
    }


def _usage(yard: str, day: int, staff: float, staff_cap: float, vet: int, vet_cap: int) -> dict:
    return {
        "yard_id": yard,
        "day_index": day,
        "staff_hours": staff,
        "staff_capacity": staff_cap,
        "vet_slots": vet,
        "vet_capacity": vet_cap,
    }


def test_first_demo_solve_has_empty_diff_null_binding_and_stays_under_five_seconds(tmp_path):
    write_dataset(tmp_path, 20261115)
    workspace = Workspace(tmp_path)
    started = time.perf_counter()
    plan = workspace.solve()
    elapsed = time.perf_counter() - started
    assert elapsed < 5, elapsed
    assert plan["diff"] == []
    assert plan["binding"] is None
    assert plan["solver_status"]
    assert "assignments" in plan
    assert "unmet_clinical" in plan
    assert "usage" in plan
    assert "proved_optimal" in plan
    assert plan["economics"]["monitoring_changes_disease"] is False
    assumptions = workspace.assumptions
    for view in workspace.cohort_views():
        if not view["active"]:
            continue
        cohort = {
            "cohort_id": view["cohort_id"],
            "cohort_size": view["head"],
            "expected_remaining": view["expected_remaining"],
            "observed_first": view["observed_first"],
        }
        base = evaluate_assignment(cohort, "status_quo", assumptions)
        watched = evaluate_assignment(cohort, "enhanced_observation", assumptions)
        assert watched["expected_remaining"] == base["expected_remaining"]
        assert watched["disease_cost"] == base["disease_cost"]


def test_repeat_solve_that_changes_nothing_leaves_binding_null(tmp_path):
    workspace = _tiny(
        tmp_path,
        [_cohort("PN-001", "2026-03-01", 0)],
        [_event("PN-001", 0)],
        [_yard(20, 2)],
    )
    first = workspace.solve()
    second = workspace.solve()
    assert second["assignments"] == first["assignments"]
    assert second["diff"] == []
    assert second["binding"] is None


def test_diff_and_binding_sentence_follow_the_previous_map():
    from app.optimize import assignment_diff, binding_sentence

    assert assignment_diff(None, None, {"PN-001": "status_quo"}, ["PN-001"]) == []
    changed = assignment_diff(
        {"AA": "vet_day_0", "BB": "status_quo", "CC": "status_quo"},
        set(),
        {"AA": "status_quo", "BB": "enhanced_observation", "CC": "status_quo"},
        ["AA"],
    )
    assert changed == [
        {
            "cohort_id": "AA",
            "before": "vet_day_0",
            "after": "status_quo",
            "entered_unmet": True,
            "left_unmet": False,
        },
        {
            "cohort_id": "BB",
            "before": "status_quo",
            "after": "enhanced_observation",
            "entered_unmet": False,
            "left_unmet": False,
        },
    ]
    left = assignment_diff(
        {"AA": "status_quo"},
        {"AA"},
        {"AA": "vet_day_1"},
        [],
    )
    assert left[0]["left_unmet"] is True
    assert left[0]["entered_unmet"] is False
    usage = [
        _usage("WK", 0, 12, 12, 0, 2),
        _usage("PN", 0, 4, 14, 3, 3),
        _usage("PN", 1, 4, 14, 1, 3),
    ]
    binding = binding_sentence(changed, usage)
    assert binding == {
        "yard_id": "PN",
        "day_index": 0,
        "resource": "vet_slots",
        "sentence": "PN day 1 veterinary slots does not fit AA.",
    }
    assert "do not treat" not in binding["sentence"]
    staff_only = binding_sentence(changed, [_usage("WK", 2, 9, 9, 0, 2)])
    assert staff_only["resource"] == "staff_hours"
    assert staff_only["day_index"] == 2
    assert staff_only["sentence"] == "WK day 3 staff hours does not fit AA."
    many = assignment_diff(
        {code: "vet_day_0" for code in ("AA", "BB", "CC", "DD", "EE")},
        set(),
        {code: "status_quo" for code in ("AA", "BB", "CC", "DD", "EE")},
        ["AA", "BB", "CC", "DD", "EE"],
    )
    named = binding_sentence(many, [_usage("PN", 0, 1, 8, 1, 1)])
    assert named["sentence"] == "PN day 1 veterinary slots does not fit AA, BB, CC."
    assert "DD" not in named["sentence"]
    assert "EE" not in named["sentence"]
    assert binding_sentence(changed, [_usage("PN", 0, 1, 8, 0, 2)]) is None
    assert binding_sentence(left, usage) is None
    assert binding_sentence([], usage) is None


def test_binding_sentence_names_only_cohorts_from_the_short_yard():
    from app.optimize import binding_sentence

    diff = [
        {"cohort_id": "HS-002", "before": "vet_day_0", "after": "status_quo", "entered_unmet": True, "left_unmet": False},
        {"cohort_id": "PC-019", "before": "vet_day_0", "after": "status_quo", "entered_unmet": True, "left_unmet": False},
    ]
    shortages = [{
        "yard_id": "PC",
        "resource": "staff hours",
        "gap_hours": 27.2,
    }]
    binding = binding_sentence(diff, [], shortages)
    assert binding["sentence"] == "PC staff hours does not fit PC-019."
    assert "HS-002" not in binding["sentence"]


def test_binding_sentence_uses_staff_hours_shortage_when_usage_is_empty():
    from app.optimize import binding_sentence

    diff = [{
        "cohort_id": "PN-001",
        "before": "vet_day_0",
        "after": "status_quo",
        "entered_unmet": True,
        "left_unmet": False,
    }]
    shortages = [{
        "yard_id": "PN",
        "resource": "staff hours",
        "needed_hours": 40.0,
        "available_hours": 10.0,
        "gap_hours": 30.0,
    }]
    binding = binding_sentence(diff, [], shortages)
    assert binding is not None
    assert "PN" in binding["sentence"]
    assert "does not fit" in binding["sentence"]
    assert "do not treat" not in binding["sentence"]


def test_vet_cut_records_cohorts_that_entered_unmet(tmp_path):
    workspace = _tiny(
        tmp_path,
        [_cohort("PN-001", "2026-03-01", 3), _cohort("PN-002", "2026-03-01", 3)],
        [_event("PN-001", 2), _event("PN-002", 2)],
        [_yard(24, 1)],
    )
    views = {row["cohort_id"]: row for row in workspace.cohort_views()}
    assert views["PN-001"]["clinical_obligation"] is True
    assert views["PN-002"]["clinical_obligation"] is True
    first = workspace.solve()
    assert first["unmet_clinical"] == []
    assert first["binding"] is None
    workspace.set_multipliers({"vet": 0})
    second = workspace.solve()
    entered = [row for row in second["diff"] if row["entered_unmet"]]
    assert {row["cohort_id"] for row in entered} == {"PN-001", "PN-002"}
    for row in entered:
        assert row["before"] != row["after"]
        assert row["left_unmet"] is False
        assert set(row) == {"cohort_id", "before", "after", "entered_unmet", "left_unmet"}
    binding = second["binding"]
    assert binding is not None
    assert binding["resource"] == "vet_slots"
    assert binding["yard_id"] == "PN"
    assert f"day {binding['day_index'] + 1}" in binding["sentence"]
    assert "veterinary slots" in binding["sentence"]
    assert "does not fit" in binding["sentence"]
    assert "do not treat" not in binding["sentence"]
    named = [row["cohort_id"] for row in entered[:3]]
    for cohort_id in named:
        assert cohort_id in binding["sentence"]


def test_already_obligated_cohort_does_not_get_a_clearing_count(monkeypatch):
    calls = {"n": 0}
    real = model.assess_cohort

    def wrapped(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(model, "assess_cohort", wrapped)
    found = model.distance_to_trigger(_healthy(40), 12, 10, -2.9, 0, already_on=True)
    assert calls["n"] == 0
    assert found["distance_to_trigger"] is None
    assert found["distance_sentence"] == "The review trigger is on."
    assert not any(character.isdigit() for character in found["distance_sentence"])


def test_distance_matches_the_exact_scan_and_steps_only_above_40(monkeypatch):
    real = model.assess_cohort

    def count_scan(head: int, day: int) -> tuple[dict, list[int]]:
        calls: list[int] = []

        def wrapped(*args, **kwargs):
            calls.append(int(args[1]))
            return real(*args, **kwargs)

        monkeypatch.setattr(model, "assess_cohort", wrapped)
        row = _healthy(head)
        found = model.distance_to_trigger(row, 0, day, -2.9, 0, already_on=False)
        monkeypatch.setattr(model, "assess_cohort", real)
        return found, calls

    small, small_calls = count_scan(30, 10)
    assert small["distance_to_trigger"] == _oracle(_healthy(30), 0, 10, -2.9, 0)
    assert small["distance_to_trigger"] == 3
    assert small_calls == [1, 2, 3]
    assert "3" in small["distance_sentence"]
    assert "trigger" in small["distance_sentence"].lower()

    large, large_calls = count_scan(80, 10)
    assert large["distance_to_trigger"] == _oracle(_healthy(80), 0, 10, -2.9, 0)
    assert large["distance_to_trigger"] == 6
    assert max(large_calls) <= 80
    assert len(large_calls) < 40

    quiet, quiet_calls = count_scan(50, 0)
    assert quiet["distance_to_trigger"] is None
    assert quiet["distance_sentence"] == "The review trigger stays off through the remaining head."
    assert 0 < len(quiet_calls) <= 15
    assert max(quiet_calls) <= 50


def test_closed_window_and_zero_remaining_stay_off():
    closed = model.distance_to_trigger(_healthy(20), 0, 46, -2.9, 0, already_on=False)
    assert closed["distance_to_trigger"] is None
    assert "stays off through the remaining head" in closed["distance_sentence"]
    empty = model.distance_to_trigger(_healthy(8), 8, 2, -2.9, 0, already_on=False)
    assert empty["distance_to_trigger"] is None
    assert "stays off through the remaining head" in empty["distance_sentence"]


def test_views_carry_distance_and_the_scan_does_not_call_the_solver(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("distance scan called the solver")

    monkeypatch.setattr(service_module, "solve_plan", boom)
    workspace = _tiny(
        tmp_path,
        [
            _cohort("PN-001", "2026-03-01", 3),
            _cohort("PN-002", "2026-03-10", 0),
            _cohort("PN-003", "2026-01-01", 0),
        ],
        [_event("PN-001", 2)],
        [_yard(20, 2)],
    )
    views = {row["cohort_id"]: row for row in workspace.cohort_views()}
    assert views["PN-001"]["clinical_obligation"] is True
    assert views["PN-001"]["distance_to_trigger"] is None
    assert views["PN-001"]["distance_sentence"] == "The review trigger is on."
    assert views["PN-003"]["past_window"] is True
    assert views["PN-003"]["distance_to_trigger"] is None
    assert "stays off through the remaining head" in views["PN-003"]["distance_sentence"]
    waiting = views["PN-002"]
    assert waiting["clinical_obligation"] is False
    assert "distance_to_trigger" in waiting
    assert "distance_sentence" in waiting
    if waiting["distance_to_trigger"] is None:
        assert "stays off through the remaining head" in waiting["distance_sentence"]
    else:
        assert isinstance(waiting["distance_to_trigger"], int)
        assert waiting["distance_to_trigger"] >= 1


def test_inclusive_loss_is_not_stacked_on_component_costs():
    cohort = {"cohort_id": "PN-001", "cohort_size": 100, "expected_remaining": 6.0, "observed_first": 2}
    inclusive = {
        "labor_cost_per_hour": 18,
        "inclusive_loss_per_first_treatment": 151.18,
        "use_inclusive_morbidity_loss": True,
        "component_treatment_cost": 80,
        "performance_loss_per_case": 70,
    }
    components = {**inclusive, "use_inclusive_morbidity_loss": False}
    bundled = evaluate_assignment(cohort, "enhanced_observation", inclusive)
    split = evaluate_assignment(cohort, "enhanced_observation", components)
    burden = 8.0
    assert bundled["expected_remaining"] == pytest.approx(6.0)
    assert bundled["disease_cost"] == pytest.approx(burden * 151.18)
    assert bundled["performance_cost"] == 0
    assert bundled["disease_cost"] + bundled["performance_cost"] == pytest.approx(bundled["disease_cost"])
    assert split["disease_cost"] == pytest.approx(burden * 80)
    assert split["performance_cost"] == pytest.approx(burden * 70)
    assert split["disease_cost"] != pytest.approx(burden * 80 + burden * 151.18)
    base = evaluate_assignment(cohort, "status_quo", inclusive)
    assert bundled["expected_remaining"] == base["expected_remaining"]
    assert bundled["disease_cost"] == base["disease_cost"]
    assert bundled["monitoring_changes_disease"] is False


def test_report_escapes_binding_sentence_and_does_not_invent_one(tmp_path, monkeypatch):
    workspace = _tiny(
        tmp_path,
        [_cohort("PN-001", "2026-03-01", 0)],
        [_event("PN-001", 0)],
        [_yard(20, 2)],
    )
    plan = workspace.solve()
    assert plan["binding"] is None
    monkeypatch.setattr(main, "workspace", workspace)
    quiet = main.report().body.decode()
    assert "does not fit" not in quiet
    assert "The week has not been generated." not in quiet
    table = main._schedule_table({"assignments": {"A&B": "vet<day"}})
    assert "A&amp;B" in table
    assert "vet&lt;day" in table
    plan["binding"] = {
        "yard_id": "PN",
        "day_index": 0,
        "resource": "vet_slots",
        "sentence": "PN day 1 veterinary slots does not fit A&B, C<D.",
    }
    plan["assignments"] = {**plan["assignments"], "A&B": "status_quo"}
    loud = main.report().body.decode()
    assert "PN day 1 veterinary slots does not fit A&amp;B, C&lt;D." in loud
    assert "does not fit A&B" not in loud
