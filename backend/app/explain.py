"""Deterministic explanations. Language is a layer over calculated fields."""

from __future__ import annotations

from typing import Any


def priority_reason(cohort: dict[str, Any]) -> str:
    if cohort["insufficient"]:
        return "Thin arrival history. The range is wide, and unknown fields are not treated as low risk."
    if cohort["clinical_obligation"]:
        return "Review trigger is on: the 15% research probability or the recorded pulls need a person, not a drug order."
    if cohort["missing"]:
        return "Missing " + ", ".join(cohort["missing"][:2]) + ". That gap is listed, not scored as healthy."
    top = max(cohort["factors"], key=lambda item: abs(item["log_odds"]), default=None)
    if top and top["log_odds"] > 0:
        return f"{top['factor'].replace('_', ' ')} raises the assumption-based rate."
    return "Near the yard reference on the fields that are filled in."


def explain_cohort(cohort: dict[str, Any], assignment: str | None, usage_note: str | None, unmet: bool = False) -> dict[str, Any]:
    drivers = [
        {
            "factor": item["factor"],
            "log_odds": item["log_odds"],
            "label": item["label"],
            "note": item["note"],
        }
        for item in cohort["factors"]
        if abs(item["log_odds"]) >= 0.05
    ]
    return {
        "cohort_id": cohort["cohort_id"],
        "why_prioritized": priority_reason(cohort),
        "inputs_that_moved_the_rate": drivers,
        "missing": cohort["missing"],
        "unknown_is_not_low_risk": True,
        "package": assignment,
        "how_this_differs_from_baseline": _package_sentence(assignment, unmet),
        "constraint_note": usage_note,
        "not_a_diagnosis": "This is a cohort research-threshold assessment, not an animal diagnosis and not a prescription.",
        "could_change_the_decision": [
            "A filled vaccination or transport record, because unknown currently widens the range.",
            "New first-treatment counts on a later day, because the remaining-period update uses only records through that day.",
            "Fewer veterinary slots, because an obligated cohort can be left unmet rather than silently skipped.",
            "The hypothetical effectiveness knob, which never changes the executed plan.",
        ],
    }


def _package_sentence(assignment: str | None, unmet: bool = False) -> str:
    if assignment is None:
        return "No plan has been generated yet. The baseline is still the yard's usual pen checks."
    if unmet:
        return "A veterinary review is still required. No slot fit this week, so the usual pen checks remain and the obligation stays on the list."
    if assignment == "status_quo":
        return "The planner left this cohort on the usual pen-check rotation."
    if assignment == "enhanced_observation":
        return "Extra checks were scheduled. Modeled disease burden is unchanged; labor goes up."
    if assignment == "records_review":
        return "A records chase was scheduled because history is incomplete."
    if assignment.startswith("enhanced_vet") or assignment.startswith("vet_day"):
        return "A veterinary assessment is on the week plan. It is a review slot, not an authorization to treat."
    return "The selected package is an operational task."


def morning_brief(snapshot: dict[str, Any]) -> dict[str, Any]:
    metrics = snapshot["metrics"]
    plan = snapshot.get("plan")
    lines = [
        f"{metrics['attention_cohorts']} cohorts need a person to look at them on {snapshot['clock']}.",
        f"Recorded first treatments so far: {metrics['observed_first']}. Projected remaining first treatments: {metrics['projected_remaining']:.1f}. Those are different numbers.",
        f"Veterinary review queue: {metrics['vet_queue']}.",
    ]
    if plan is None:
        lines.append("Today's plan has not been generated. The baseline pen-check rotation is still the working plan.")
    else:
        lines.append(plan["message"])
        if plan["unmet_clinical"]:
            lines.append("Unscheduled clinical reviews: " + ", ".join(plan["unmet_clinical"][:6]) + ".")
    thin = [row["cohort_id"] for row in snapshot["cohorts"] if row["insufficient"]][:6]
    if thin:
        lines.append("Thin files: " + ", ".join(thin) + ".")
    return {
        "title": "Morning briefing",
        "clock": snapshot["clock"],
        "lines": lines,
        "source": "template over the current calculations",
        "model": None,
    }


def answer_question(question: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    text = question.lower().strip()
    cohorts = snapshot["cohorts"]
    if "vaccin" in text:
        names = [row["cohort_id"] for row in cohorts if "vaccination_history" in row["missing"]]
        return _answer(f"{len(names)} cohorts have no usable vaccination history.", names[:12])
    if "staff" in text or "shortfall" in text:
        yards = sorted(snapshot["yards"], key=lambda yard: yard["staff_slack_hours"])
        tight = yards[0]
        return _answer(
            f"{tight['name']} has the least spare staff on a baseline day: {tight['staff_slack_hours']:.1f} hours.",
            [yard["yard_id"] for yard in yards],
        )
    if "binding" in text or "constraint" in text:
        plan = snapshot.get("plan")
        if not plan:
            return _answer("Generate today's plan to see which capacities bind.", [])
        binding = [row for row in plan["usage"] if row["staff_hours"] > 0.85 * row["staff_capacity"] or row["vet_slots"] >= row["vet_capacity"] and row["vet_capacity"] > 0]
        return _answer(f"{len(binding)} yard-days are at or above 85% of a listed capacity.", [f"{row['yard_id']} day {row['day_index'] + 1}" for row in binding[:10]])
    if "yesterday" in text or "changed" in text:
        return _answer(snapshot.get("since_yesterday", "Move the clock to compare two assessment dates."), [])
    if text.startswith("why") or "lot " in text or "-" in text:
        token = _cohort_token(text, cohorts)
        if token is None:
            return _answer("Name a cohort id, for example PN-001.", [])
        plan = snapshot.get("plan") or {}
        detail = explain_cohort(token, plan.get("assignments", {}).get(token["cohort_id"]), None, token["cohort_id"] in plan.get("unmet_clinical", []))
        return _answer(detail["why_prioritized"] + " " + detail["how_this_differs_from_baseline"], detail["missing"])
    if "additional staff" in text or "extra staff" in text or "one more" in text:
        return _answer("Use the staff slider on the planner and generate the plan again. The solver reruns; this box does not invent a headcount.", [])
    if "sensitive" in text or "effectiveness" in text:
        return _answer("The effectiveness slider changes only the hypothetical protocol column. It does not rewrite the executed schedule.", [])
    return _answer("I can answer priorities, missing vaccination, staffing slack, binding days, and why a named cohort is on the list. I do not answer open clinical questions.", [])


def _cohort_token(text: str, cohorts: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in cohorts:
        if row["cohort_id"].lower() in text:
            return row
    return None


def _answer(text: str, items: list[str]) -> dict[str, Any]:
    return {"answer": text, "items": items, "source": "structured retrieval", "clinical_advice": False}
