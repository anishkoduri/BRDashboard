"""CP-SAT weekly resource allocation. Safety constraints before labor cost."""

from __future__ import annotations

import time
from typing import Any

from ortools.sat.python import cp_model

from app.model import CATALOG, VET_PACKAGES

BENEFIT_WEIGHT = 40
UNMET_PENALTY = 1_000_000


def _tenths(hours: float) -> int:
    return int(round(hours * 10))


def allowed_packages(cohort: dict[str, Any], hard_clinical: bool) -> list[str]:
    incomplete = bool(cohort["incomplete_history"])
    names = ["status_quo", "enhanced_observation"]
    if incomplete:
        names.append("records_review")
    names.extend(VET_PACKAGES)
    if cohort["clinical_obligation"] and hard_clinical:
        return [name for name in names if name in VET_PACKAGES]
    return names


def _benefit(cohort: dict[str, Any], package: str) -> int:
    remaining_points = int(round(float(cohort["expected_remaining"]) * 10))
    score = 0
    if package in {"enhanced_observation"} or package.startswith("enhanced_vet"):
        score += remaining_points
    if package == "records_review" and cohort["incomplete_history"]:
        score += 20
    if package.startswith("vet_day") or package.startswith("enhanced_vet"):
        score += 5
    return score


def _shortage(cohorts: list[dict[str, Any]], yards: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    notes = []
    for yard_id, yard in yards.items():
        group = [item for item in cohorts if item["yard_id"] == yard_id]
        obligated = [item for item in group if item["clinical_obligation"]]
        vet_capacity = int(yard["vet_slots_per_day"]) * 3
        if len(obligated) > vet_capacity:
            notes.append({
                "yard_id": yard_id,
                "resource": "veterinary review slots",
                "needed": len(obligated),
                "available_in_first_3_days": vet_capacity,
                "gap": len(obligated) - vet_capacity,
            })
        min_hours = 0.0
        for item in group:
            package = VET_PACKAGES[0] if item["clinical_obligation"] else "status_quo"
            min_hours += sum(CATALOG[package]["hours"])
        staff_week = float(yard["staff_hours_per_day"]) * 7
        if min_hours > staff_week + 1e-6:
            notes.append({
                "yard_id": yard_id,
                "resource": "staff hours",
                "needed_hours": round(min_hours, 2),
                "available_hours": round(staff_week, 2),
                "gap_hours": round(min_hours - staff_week, 2),
            })
    return notes


def _consume(assignments: dict[str, str], cohorts: list[dict[str, Any]], yards: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["cohort_id"]: item for item in cohorts}
    usage = []
    for yard_id, yard in yards.items():
        for day in range(7):
            staff = 0.0
            vet = 0
            chute = 0
            hospital = 0
            for cohort_id, package in assignments.items():
                cohort = by_id.get(cohort_id)
                if cohort is None or cohort["yard_id"] != yard_id:
                    continue
                spec = CATALOG[package]
                staff += spec["hours"][day]
                vet += spec["vet"][day]
                chute += spec["chute"][day]
                if spec["vet"][day]:
                    hospital += spec["hospital"]
            usage.append({
                "yard_id": yard_id,
                "day_index": day,
                "staff_hours": round(staff, 3),
                "staff_capacity": float(yard["staff_hours_per_day"]),
                "vet_slots": vet,
                "vet_capacity": int(yard["vet_slots_per_day"]),
                "chute_head": chute,
                "chute_capacity": int(yard["chute_head_per_day"]),
                "hospital_pens": hospital,
                "hospital_capacity": int(yard["hospital_pens"]),
            })
    return usage


def _build(cohorts: list[dict[str, Any]], yards: dict[str, dict[str, Any]], hard_clinical: bool) -> tuple[cp_model.CpModel, dict[tuple[str, str], Any], dict[str, Any]]:
    model = cp_model.CpModel()
    variables: dict[tuple[str, str], Any] = {}
    unmet: dict[str, Any] = {}
    for cohort in cohorts:
        names = allowed_packages(cohort, hard_clinical)
        choices = []
        for name in names:
            var = model.NewBoolVar(f"{cohort['cohort_id']}__{name}")
            variables[(cohort["cohort_id"], name)] = var
            choices.append(var)
        if cohort["clinical_obligation"] and not hard_clinical:
            flag = model.NewBoolVar(f"unmet_{cohort['cohort_id']}")
            unmet[cohort["cohort_id"]] = flag
            vet_vars = [variables[(cohort["cohort_id"], name)] for name in names if name in VET_PACKAGES]
            model.Add(sum(vet_vars) + flag == 1)
            model.Add(sum(choices) == 1)
        else:
            model.Add(sum(choices) == 1)
    by_id = {item["cohort_id"]: item for item in cohorts}
    for yard_id, yard in yards.items():
        members = [item for item in cohorts if item["yard_id"] == yard_id]
        for day in range(7):
            staff_terms = []
            vet_terms = []
            chute_terms = []
            hospital_terms = []
            for cohort in members:
                for name in allowed_packages(cohort, hard_clinical):
                    var = variables[(cohort["cohort_id"], name)]
                    spec = CATALOG[name]
                    staff_terms.append(_tenths(spec["hours"][day]) * var)
                    if spec["vet"][day]:
                        vet_terms.append(var)
                        chute_terms.append(spec["chute"][day] * var)
                        hospital_terms.append(spec["hospital"] * var)
            if staff_terms:
                model.Add(sum(staff_terms) <= _tenths(float(yard["staff_hours_per_day"])))
            if vet_terms:
                model.Add(sum(vet_terms) <= int(yard["vet_slots_per_day"]))
            if chute_terms:
                model.Add(sum(chute_terms) <= int(yard["chute_head_per_day"]))
            if hospital_terms:
                model.Add(sum(hospital_terms) <= int(yard["hospital_pens"]))
    labor_terms = []
    benefit_terms = []
    for (cohort_id, name), var in variables.items():
        cohort = by_id[cohort_id]
        extra = sum(CATALOG[name]["hours"]) - sum(CATALOG["status_quo"]["hours"])
        labor_terms.append(_tenths(max(extra, 0)) * var)
        benefit_terms.append(_benefit(cohort, name) * var)
    unmet_terms = [flag for flag in unmet.values()]
    objective = sum(labor_terms) - BENEFIT_WEIGHT * sum(benefit_terms)
    if unmet_terms:
        objective += UNMET_PENALTY * sum(unmet_terms)
    model.Minimize(objective)
    return model, variables, unmet


def _extract(solver: cp_model.CpSolver, variables: dict[tuple[str, str], Any], unmet: dict[str, Any], cohorts: list[dict[str, Any]]) -> tuple[dict[str, str], list[str]]:
    assignments: dict[str, str] = {}
    for cohort in cohorts:
        chosen = "status_quo"
        for (cohort_id, name), var in variables.items():
            if cohort_id == cohort["cohort_id"] and solver.Value(var) == 1:
                chosen = name
                break
        assignments[cohort["cohort_id"]] = chosen
    unmet_ids = [cohort_id for cohort_id, flag in unmet.items() if solver.Value(flag) == 1]
    return assignments, unmet_ids


def solve_plan(
    cohorts: list[dict[str, Any]],
    yards: dict[str, dict[str, Any]],
    time_limit: float = 4.0,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not cohorts:
        return {
            "solver_status": "OPTIMAL",
            "clinical_label": "optimal",
            "assignments": {},
            "unmet_clinical": [],
            "usage": [],
            "shortages": [],
            "solve_seconds": 0.0,
            "proved_optimal": True,
            "medication_executed": False,
        }
    hard_model, hard_vars, hard_unmet = _build(cohorts, yards, True)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 4
    status = solver.Solve(hard_model)
    status_name = solver.StatusName(status)
    relaxed = False
    unmet_ids: list[str] = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignments, unmet_ids = _extract(solver, hard_vars, hard_unmet, cohorts)
    else:
        relaxed = True
        soft_model, soft_vars, soft_unmet = _build(cohorts, yards, False)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        solver.parameters.num_search_workers = 4
        status = solver.Solve(soft_model)
        status_name = solver.StatusName(status)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {
                "solver_status": status_name,
                "clinical_label": "infeasible",
                "assignments": {},
                "unmet_clinical": [item["cohort_id"] for item in cohorts if item["clinical_obligation"]],
                "usage": [],
                "shortages": _shortage(cohorts, yards),
                "solve_seconds": round(time.perf_counter() - started, 3),
                "proved_optimal": False,
                "medication_executed": False,
                "message": "No schedule satisfies the resource limits. Clinical obligations stay on the list.",
            }
        assignments, unmet_ids = _extract(solver, soft_vars, soft_unmet, cohorts)
    if unmet_ids or relaxed:
        label = "unmet_care"
        proved = False
    elif status == cp_model.OPTIMAL:
        label = "optimal"
        proved = True
    else:
        label = "feasible_not_proved"
        proved = False
    return {
        "solver_status": status_name,
        "clinical_label": label,
        "assignments": assignments,
        "unmet_clinical": unmet_ids,
        "usage": _consume(assignments, cohorts, yards),
        "shortages": _shortage(cohorts, yards) if unmet_ids else [],
        "solve_seconds": round(time.perf_counter() - started, 3),
        "proved_optimal": proved,
        "medication_executed": False,
        "message": _message(label, unmet_ids),
    }


def _message(label: str, unmet: list[str]) -> str:
    if label == "optimal":
        return "Proved optimal for the safety-first objective under the current capacities."
    if label == "feasible_not_proved":
        return "Feasible schedule. The solver did not prove optimality before the time limit."
    if label == "unmet_care":
        return f"{len(unmet)} clinical review obligations do not fit. They were not dropped from the requirement list."
    return "No feasible schedule."


def assignment_diff(
    previous_assignments: dict[str, str] | None,
    previous_unmet: set[str] | None,
    assignments: dict[str, str],
    unmet: list[str] | set[str],
) -> list[dict[str, Any]]:
    """Cohorts whose package or unmet membership changed since the previous solve."""
    if previous_assignments is None:
        return []
    old_unmet = set(previous_unmet or ())
    new_unmet = set(unmet)
    cohort_ids = set(previous_assignments) | set(assignments) | old_unmet | new_unmet
    rows: list[dict[str, Any]] = []
    for cohort_id in sorted(cohort_ids):
        before = previous_assignments.get(cohort_id)
        after = assignments.get(cohort_id)
        entered = cohort_id in new_unmet and cohort_id not in old_unmet
        left = cohort_id in old_unmet and cohort_id not in new_unmet
        if before == after and not entered and not left:
            continue
        rows.append({
            "cohort_id": cohort_id,
            "before": before,
            "after": after,
            "entered_unmet": entered,
            "left_unmet": left,
        })
    return rows


_RESOURCE_WORDS = {
    "vet_slots": "veterinary slots",
    "staff_hours": "staff hours",
}


def _names_for_sentence(entered: list[str], yard_id: str) -> str:
    prefix = f"{yard_id}-"
    matched = [cohort_id for cohort_id in entered if str(cohort_id).startswith(prefix)]
    chosen = matched or entered
    return ", ".join(chosen[:3])


def binding_sentence(
    diff: list[dict[str, Any]],
    usage: list[dict[str, Any]],
    shortages: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Yard-day whose listed capacity is full and the cohorts that entered unmet."""
    entered = [row["cohort_id"] for row in diff if row["entered_unmet"]]
    if not entered:
        return None
    chosen, resource = _binding_resource(usage)
    if chosen is not None and resource is not None:
        names = _names_for_sentence(entered, str(chosen["yard_id"]))
        day_number = int(chosen["day_index"]) + 1
        sentence = f"{chosen['yard_id']} day {day_number} {_RESOURCE_WORDS[resource]} does not fit {names}."
        return {
            "yard_id": chosen["yard_id"],
            "day_index": chosen["day_index"],
            "resource": resource,
            "sentence": sentence,
        }
    notes = shortages or []
    if notes:
        tightest = max(notes, key=_shortage_gap)
        names = _names_for_sentence(entered, str(tightest["yard_id"]))
        sentence = f"{tightest['yard_id']} {tightest['resource']} does not fit {names}."
        return {
            "yard_id": tightest["yard_id"],
            "day_index": None,
            "resource": tightest["resource"],
            "sentence": sentence,
        }
    if not usage:
        return {
            "yard_id": "",
            "day_index": None,
            "resource": "",
            "sentence": "The cut does not fit the listed reviews.",
        }
    return None


def _shortage_gap(row: dict[str, Any]) -> float:
    if "gap_hours" in row:
        return float(row["gap_hours"])
    return float(row["gap"])


def _binding_resource(usage: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    for row in usage:
        if float(row["vet_slots"]) >= float(row["vet_capacity"]):
            return row, "vet_slots"
    for row in usage:
        if float(row["staff_hours"]) >= float(row["staff_capacity"]):
            return row, "staff_hours"
    return None, None


def violates_capacity(usage: list[dict[str, Any]]) -> list[str]:
    problems = []
    for row in usage:
        if row["staff_hours"] - row["staff_capacity"] > 0.05:
            problems.append(f"{row['yard_id']} day {row['day_index']} staff")
        if row["vet_slots"] > row["vet_capacity"]:
            problems.append(f"{row['yard_id']} day {row['day_index']} vet")
        if row["chute_head"] > row["chute_capacity"]:
            problems.append(f"{row['yard_id']} day {row['day_index']} chute")
        if row["hospital_pens"] > row["hospital_capacity"]:
            problems.append(f"{row['yard_id']} day {row['day_index']} hospital")
    return problems
