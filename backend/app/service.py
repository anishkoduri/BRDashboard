"""Working dataset, clock, overlays, and plan cache."""

from __future__ import annotations

import csv
import json
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.explain import explain_cohort, morning_brief, priority_reason
from app.generate import CLOCK_DEFAULT, GENERATOR_VERSION, SEED, write_dataset
from app.model import (
    CATALOG,
    INCLUSIVE_LOSS_USD,
    METAPHYLAXIS_COST_USD,
    MODEL_VERSION,
    assess_cohort,
    clinical_obligation,
    distance_to_trigger,
    evaluate_assignment,
    package_hours,
    sum_plan,
)
from app.optimize import assignment_diff, binding_sentence, solve_plan

ROOT = Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _named_record(row: Any, columns: tuple[str, ...]) -> dict[str, Any] | None:
    """Read a sqlite3.Row by column name. A short row is skipped."""
    keys = getattr(row, "keys", None)
    if callable(keys):
        names = list(keys())
        if len(names) < len(columns) or any(name not in names for name in columns):
            return None
        try:
            return {name: row[name] for name in columns}
        except IndexError:
            return None
    if len(row) < len(columns):
        return None
    try:
        return {name: row[index] for index, name in enumerate(columns)}
    except IndexError:
        return None


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_cohort(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["cohort_size"] = int(float(item["cohort_size"]))
    item["mean_arrival_weight_lb"] = _number(item.get("mean_arrival_weight_lb"))
    item["number_of_sources"] = _number(item.get("number_of_sources"))
    item["transport_duration_hours"] = _number(item.get("transport_duration_hours"))
    item["pen_area_per_head"] = _number(item.get("pen_area_per_head"))
    item["scenario_yard_offset"] = _number(item.get("scenario_yard_offset")) or 0
    item["respiratory_observation_count"] = int(float(item.get("respiratory_observation_count") or 0))
    item["bunk_space_per_head"] = _number(item.get("bunk_space_per_head"))
    return item


class Workspace:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.lock = threading.Lock()
        self.mode = "synthetic demonstration"
        self.clock = CLOCK_DEFAULT
        self.cohorts: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.yards: list[dict[str, Any]] = []
        self.assumptions = self._default_assumptions()
        self.multipliers = {"staff": 1.0, "chute": 1.0, "vet": 1.0, "budget_cents": 10_000_000}
        self.plan: dict[str, Any] | None = None
        self._prior_assignments: dict[str, str] | None = None
        self._prior_unmet: set[str] | None = None
        self.pending_import: dict[str, Any] | None = None
        self.role = "manager"
        demo = root / "data" / "demo" / "cohorts.csv"
        if not demo.exists():
            write_dataset(root, SEED)
        self._load_demo_files()
        self.db = sqlite3.connect(root / "data" / "app.sqlite", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE IF NOT EXISTS overlay (id INTEGER PRIMARY KEY, cohort_id TEXT, day INTEGER, detected INTEGER, note TEXT, actor TEXT, ts TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS review (cohort_id TEXT PRIMARY KEY, status TEXT, actor TEXT, note TEXT, ts TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS scenario (id TEXT PRIMARY KEY, payload TEXT)")
        self.db.commit()
        self._load_scenario()

    def _default_assumptions(self) -> dict[str, Any]:
        return {
            "assessment_intercept": -2.9,
            "inclusive_loss_per_first_treatment": INCLUSIVE_LOSS_USD,
            "use_inclusive_morbidity_loss": True,
            "metaphylaxis_cost_per_head": METAPHYLAXIS_COST_USD,
            "effectiveness": 0.50,
            "labor_cost_per_hour": 18.0,
            "component_treatment_cost": 80.0,
            "performance_loss_per_case": 70.0,
        }

    def _load_demo_files(self) -> None:
        demo = self.root / "data" / "demo"
        self.cohorts = [_coerce_cohort(row) for row in _read_csv(demo / "cohorts.csv")]
        self.events = []
        for row in _read_csv(demo / "health_events.csv"):
            self.events.append({
                "cohort_id": row["cohort_id"],
                "day_on_feed": int(row["day_on_feed"]),
                "event_date": row["event_date"],
                "detected_first_count": int(row["detected_first_count"]),
                "latent_first_count": int(row["latent_first_count"]),
                "subsequent_count": int(row["subsequent_count"]),
                "mortality_count": int(row["mortality_count"]),
            })
        self.yards = []
        for row in _read_csv(demo / "yards.csv"):
            self.yards.append({
                "yard_id": row["yard_id"],
                "name": row["name"],
                "region": row["region"],
                "staff_hours_per_day": float(row["staff_hours_per_day"]),
                "chute_head_per_day": int(float(row["chute_head_per_day"])),
                "vet_slots_per_day": int(float(row["vet_slots_per_day"])),
                "hospital_pens": int(float(row["hospital_pens"])),
                "labor_cost_per_hour": float(row["labor_cost_per_hour"]),
            })
        assumptions = json.loads((demo / "assumptions.json").read_text(encoding="utf-8"))
        self.assumptions["assessment_intercept"] = float(assumptions["assessment_intercept"])
        provenance = json.loads((demo / "provenance.json").read_text(encoding="utf-8"))
        self.provenance = provenance
        self.mode = "synthetic demonstration"

    def _load_scenario(self) -> None:
        row = self.db.execute("SELECT payload FROM scenario WHERE id = 'current'").fetchone()
        if not row:
            return
        payload = json.loads(row[0])
        self.clock = date.fromisoformat(payload["clock"])
        self.assumptions.update(payload.get("assumptions", {}))
        self.multipliers.update(payload.get("multipliers", {}))
        self.role = payload.get("role", "manager")

    def _save_scenario(self) -> None:
        payload = {
            "clock": self.clock.isoformat(),
            "assumptions": self.assumptions,
            "multipliers": self.multipliers,
            "role": self.role,
        }
        self.db.execute("INSERT INTO scenario (id, payload) VALUES ('current', ?) ON CONFLICT(id) DO UPDATE SET payload = excluded.payload", (json.dumps(payload),))
        self.db.commit()

    def overlays(self) -> list[dict[str, Any]]:
        columns = ("cohort_id", "day", "detected", "note", "actor", "ts")
        rows = self.db.execute(
            "SELECT cohort_id, day, detected, note, actor, ts FROM overlay"
        ).fetchall()
        parsed = []
        for row in rows:
            item = _named_record(row, columns)
            if item is not None:
                parsed.append(item)
        return parsed

    def reviews(self) -> dict[str, dict[str, Any]]:
        columns = ("cohort_id", "status", "actor", "note", "ts")
        rows = self.db.execute(
            "SELECT cohort_id, status, actor, note, ts FROM review"
        ).fetchall()
        found: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = _named_record(row, columns)
            if item is None:
                continue
            found[str(item["cohort_id"])] = {
                "status": item["status"],
                "actor": item["actor"],
                "note": item["note"],
                "ts": item["ts"],
            }
        return found

    def reload_demo(self) -> None:
        with self.lock:
            write_dataset(self.root, SEED)
            self._load_demo_files()
            self.db.execute("DELETE FROM overlay")
            self.db.execute("DELETE FROM review")
            self.plan = None
            self._prior_assignments = None
            self._prior_unmet = None
            self.pending_import = None
            self._save_scenario()

    def set_clock(self, value: str) -> None:
        with self.lock:
            self.clock = date.fromisoformat(value)
            self.plan = None
            self._save_scenario()

    def set_role(self, role: str) -> None:
        if role not in {"manager", "rider", "veterinarian"}:
            raise ValueError("Role must be manager, rider, or veterinarian.")
        with self.lock:
            self.role = role
            self._save_scenario()

    def update_assumptions(self, patch: dict[str, Any]) -> None:
        allowed = {
            "inclusive_loss_per_first_treatment",
            "effectiveness",
            "labor_cost_per_hour",
            "use_inclusive_morbidity_loss",
            "metaphylaxis_cost_per_head",
        }
        with self.lock:
            for key, value in patch.items():
                if key not in allowed:
                    continue
                self.assumptions[key] = value
            self.plan = None
            self._save_scenario()

    def set_multipliers(self, patch: dict[str, Any]) -> None:
        with self.lock:
            for key in ("staff", "chute", "vet"):
                if key in patch:
                    self.multipliers[key] = max(0.0, float(patch[key]))
            if "budget_cents" in patch:
                self.multipliers["budget_cents"] = int(patch["budget_cents"])
            self.plan = None
            self._save_scenario()

    def add_observation(self, cohort_id: str, day: int, detected: int, note: str, actor: str) -> None:
        if detected < 0 or day < 1 or day > 45:
            raise ValueError("Observation day must be 1-45 and the count cannot be negative.")
        with self.lock:
            if not any(row["cohort_id"] == cohort_id for row in self.cohorts):
                raise ValueError("Unknown cohort.")
            self.db.execute(
                "INSERT INTO overlay (cohort_id, day, detected, note, actor, ts) VALUES (?, ?, ?, ?, ?, ?)",
                (cohort_id, day, detected, note, actor, datetime.now().isoformat(timespec="seconds")),
            )
            self.db.commit()
            self.plan = None

    def set_review(self, cohort_id: str, status: str, actor: str, note: str) -> None:
        allowed = {
            "needs_clinical_review",
            "awaiting_veterinary_authorization",
            "authorized_under_recorded_protocol",
            "declined_or_revised",
            "completed",
            "follow_up_required",
        }
        if status not in allowed:
            raise ValueError("Unknown review status.")
        with self.lock:
            self.db.execute(
                "INSERT INTO review (cohort_id, status, actor, note, ts) VALUES (?, ?, ?, ?, ?) ON CONFLICT(cohort_id) DO UPDATE SET status = excluded.status, actor = excluded.actor, note = excluded.note, ts = excluded.ts",
                (cohort_id, status, actor, note, datetime.now().isoformat(timespec="seconds")),
            )
            self.db.commit()

    def _events_through(self, cohort_id: str, day: int) -> tuple[int, int, int]:
        detected = subsequent = deaths = 0
        for event in self.events:
            if event["cohort_id"] == cohort_id and event["day_on_feed"] <= day:
                detected += event["detected_first_count"]
                subsequent += event["subsequent_count"]
                deaths += event["mortality_count"]
        for overlay in self.overlays():
            if overlay["cohort_id"] == cohort_id and overlay["day"] <= day:
                detected += int(overlay["detected"])
        return detected, subsequent, deaths

    def _view_cohort(self, row: dict[str, Any], reviews: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        arrival = date.fromisoformat(row["arrival_date"])
        if self.clock < arrival:
            return None
        day = (self.clock - arrival).days + 1
        detected, subsequent, deaths = self._events_through(row["cohort_id"], day)
        detected = min(detected, row["cohort_size"])
        assessment = assess_cohort(row, detected, min(day, 45), float(self.assumptions["assessment_intercept"]))
        obligation = clinical_obligation(assessment, int(row["respiratory_observation_count"]), row["cohort_size"]) and day <= 45
        distance = distance_to_trigger(
            row,
            detected,
            day,
            float(self.assumptions["assessment_intercept"]),
            int(row["respiratory_observation_count"]),
            already_on=obligation,
        )
        incomplete = bool(assessment["missing"])
        view = {
            **{key: row.get(key) for key in (
                "cohort_id", "yard_id", "pen_id", "arrival_date", "sex_group", "source_type",
                "vaccination_history", "receiving_ration_category", "prior_metaphylaxis_status",
                "arrival_season", "water_access_status", "weaning_history", "prior_health_history",
            )},
            "head": row["cohort_size"],
            "weight": row["mean_arrival_weight_lb"],
            "sources": row["number_of_sources"],
            "transport": row["transport_duration_hours"],
            "area_per_head": row["pen_area_per_head"],
            "bunk_space_per_head": row.get("bunk_space_per_head"),
            "day_on_feed": day,
            "past_window": day > 45,
            "active": day <= 45,
            "observed_first": detected,
            "subsequent": subsequent,
            "deaths_observed": deaths,
            "expected_remaining": round(assessment["expected_remaining"], 3) if day <= 45 else 0,
            "expected_per_100": round(assessment["expected_per_100"], 2),
            "p_exceed_15": round(assessment["p_exceed_15"], 4),
            "band_low": round(assessment["band_low"], 4),
            "band_high": round(assessment["band_high"], 4),
            "band_label": assessment["band_label"],
            "factors": assessment["factors"],
            "missing": assessment["missing"],
            "insufficient": assessment["insufficient"],
            "clinical_obligation": obligation,
            "distance_to_trigger": distance["distance_to_trigger"],
            "distance_sentence": distance["distance_sentence"],
            "incomplete_history": incomplete,
            "respiratory_flags": row["respiratory_observation_count"],
            "model_version": MODEL_VERSION,
            "research_threshold_note": assessment["research_threshold_note"],
        }
        review = reviews.get(row["cohort_id"])
        if review:
            view["review"] = review
        elif obligation:
            view["review"] = {"status": "needs_clinical_review", "actor": "system", "note": "Simulated queue. Not a clinical approval.", "ts": None}
        else:
            view["review"] = {"status": "no_review_queued", "actor": "system", "note": "", "ts": None}
        return view

    def cohort_views(self) -> list[dict[str, Any]]:
        reviews = self.reviews()
        views = []
        for row in self.cohorts:
            view = self._view_cohort(row, reviews)
            if view is not None:
                views.append(view)
        yard_mean: dict[str, float] = {}
        for yard in {row["yard_id"] for row in views}:
            group = [row["expected_per_100"] for row in views if row["yard_id"] == yard]
            yard_mean[yard] = sum(group) / len(group) if group else 0
        for view in views:
            view["yard_reference_per_100"] = round(yard_mean[view["yard_id"]], 2)
            view["versus_yard"] = round(view["expected_per_100"] - yard_mean[view["yard_id"]], 2)
            view["priority_reason"] = priority_reason(view)
            view["priority_score"] = round(
                view["expected_remaining"] * 10
                + (30 if view["clinical_obligation"] else 0)
                + (12 if view["insufficient"] else 0)
                + len(view["missing"]),
                2,
            )
            filled = 6 - len(view["missing"])
            view["completeness"] = round(max(filled, 0) / 6, 2)
        views.sort(key=lambda item: item["priority_score"], reverse=True)
        return views

    def _yard_payload(self, views: list[dict[str, Any]]) -> list[dict[str, Any]]:
        payloads = []
        for yard in self.yards:
            group = [row for row in views if row["yard_id"] == yard["yard_id"] and row["active"]]
            baseline = sum(CATALOG["status_quo"]["hours"][0] for _ in group)
            capacity = yard["staff_hours_per_day"] * self.multipliers["staff"]
            observed = sum(int(row["observed_first"]) for row in group)
            head = sum(int(row["head"]) for row in group)
            cost = sum(
                evaluate_assignment({
                    "cohort_id": row["cohort_id"],
                    "cohort_size": row["head"],
                    "expected_remaining": row["expected_remaining"],
                    "observed_first": row["observed_first"],
                }, "status_quo", self.assumptions)["total_cost"]
                for row in group
            )
            payloads.append({
                **yard,
                "staff_hours_per_day": round(capacity, 2),
                "chute_head_per_day": int(yard["chute_head_per_day"] * self.multipliers["chute"]),
                "vet_slots_per_day": int(yard["vet_slots_per_day"] * self.multipliers["vet"]),
                "active_cohorts": len(group),
                "head": head,
                "observed_first": observed,
                "observed_per_100": round(100 * observed / head, 2) if head else 0,
                "expected_remaining": round(sum(float(row["expected_remaining"]) for row in group), 2),
                "current_approach_cost": round(cost, 2),
                "baseline_staff_day0": round(baseline, 2),
                "staff_slack_hours": round(capacity - baseline, 2),
            })
        return payloads

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            views = self.cohort_views()
            yards = self._yard_payload(views)
            active = [row for row in views if row["active"]]
            yesterday = self._yesterday_note(views)
            metrics = {
                "head": sum(row["head"] for row in active),
                "cohorts": len(active),
                "attention_cohorts": sum(1 for row in active if row["clinical_obligation"] or row["insufficient"] or row["p_exceed_15"] >= 0.35),
                "observed_first": sum(row["observed_first"] for row in active),
                "projected_remaining": round(sum(row["expected_remaining"] for row in active), 2),
                "vet_queue": sum(1 for row in active if row["clinical_obligation"]),
                "staff_available_today": round(sum(yard["staff_hours_per_day"] for yard in yards), 2),
                "baseline_staff_day0": round(sum(yard["baseline_staff_day0"] for yard in yards), 2),
                "deaths_observed": sum(row["deaths_observed"] for row in active),
            }
            return {
                "meta": {
                    "product": "BRDashboard",
                    "tagline": "From cattle health data to better decisions.",
                    "data_mode": self.mode,
                    "model_version": MODEL_VERSION,
                    "generator_version": GENERATOR_VERSION,
                    "seed": self.provenance.get("seed", SEED),
                    "clock": self.clock.isoformat(),
                    "role": self.role,
                    "disclaimer": "Research demonstration and decision support. Not a diagnostic system. Not a prescription.",
                    "updated": datetime.now().isoformat(timespec="seconds"),
                },
                "clock": self.clock.isoformat(),
                "assumptions": self.assumptions,
                "multipliers": self.multipliers,
                "yards": yards,
                "cohorts": views,
                "metrics": metrics,
                "plan": self.plan,
                "since_yesterday": yesterday,
                "provenance": self.provenance,
            }

    def _yesterday_note(self, views: list[dict[str, Any]]) -> str:
        return (
            f"On {self.clock.isoformat()}, {sum(row['observed_first'] for row in views)} first treatments are visible. "
            "Moving the clock earlier hides later records. The model never reads them."
        )

    def planner_cohorts(self, views: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "cohort_id": row["cohort_id"],
                "yard_id": row["yard_id"],
                "expected_remaining": row["expected_remaining"],
                "incomplete_history": row["incomplete_history"],
                "clinical_obligation": row["clinical_obligation"],
                "observed_first": row["observed_first"],
                "cohort_size": row["head"],
            }
            for row in views
            if row["active"]
        ]

    def yard_map(self, yards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            yard["yard_id"]: {
                "staff_hours_per_day": yard["staff_hours_per_day"],
                "chute_head_per_day": yard["chute_head_per_day"],
                "vet_slots_per_day": yard["vet_slots_per_day"],
                "hospital_pens": yard["hospital_pens"],
            }
            for yard in yards
        }

    def solve(self) -> dict[str, Any]:
        with self.lock:
            return self._solve_locked()

    def _solve_locked(self) -> dict[str, Any]:
        previous_assignments = self._prior_assignments
        previous_unmet = self._prior_unmet
        views = self.cohort_views()
        yards = self._yard_payload(views)
        plan = solve_plan(self.planner_cohorts(views), self.yard_map(yards), time_limit=3.0)
        assignments = plan.get("assignments") or {}
        unmet = plan.get("unmet_clinical") or []
        plan["diff"] = assignment_diff(previous_assignments, previous_unmet, assignments, unmet)
        plan["binding"] = binding_sentence(plan["diff"], plan.get("usage") or [], plan.get("shortages") or [])
        plan["economics"] = self._economics(views, assignments, None)
        self._prior_assignments = dict(assignments)
        self._prior_unmet = set(unmet)
        self.plan = plan
        return plan

    def _economics(self, views: list[dict[str, Any]], assignments: dict[str, str], protocol: dict[str, Any] | None) -> dict[str, Any]:
        active = [row for row in views if row["active"]]
        rows = []
        for row in active:
            package = assignments.get(row["cohort_id"], "status_quo")
            rows.append(evaluate_assignment({
                "cohort_id": row["cohort_id"],
                "cohort_size": row["head"],
                "expected_remaining": row["expected_remaining"],
                "observed_first": row["observed_first"],
            }, package, self.assumptions, protocol))
        totals = sum_plan(rows)
        totals["cost_per_head"] = totals["total_cost"] / max(sum(row["head"] for row in active), 1)
        return {
            "totals": totals,
            "rows": rows,
            "monitoring_changes_disease": _monitoring_changes_disease(active, self.assumptions),
        }

    def compare(self) -> dict[str, Any]:
        with self.lock:
            views = self.cohort_views()
            if self.plan is None:
                self._solve_locked()
            active = [row for row in views if row["active"]]
            baseline_assign = {row["cohort_id"]: "status_quo" for row in active}
            optimized = self.plan["assignments"]
            protocol_ids = [row["cohort_id"] for row in active if row["clinical_obligation"]][:8]
            protocol = {
                "cohort_ids": protocol_ids,
                "effectiveness": float(self.assumptions["effectiveness"]),
                "cost_per_head": float(self.assumptions["metaphylaxis_cost_per_head"]),
                "label": "Hypothetical group-level protocol. Veterinary review required. Not executed.",
            }
            baseline = self._economics(views, baseline_assign, None)
            proposed = self._economics(views, optimized, None)
            alternative = self._economics(views, optimized, protocol)
            head = max(sum(row["head"] for row in active), 1)
            return {
                "baseline": {**baseline["totals"], "label": "Current operating approach", "per_head": baseline["totals"]["total_cost"] / head},
                "optimized": {**proposed["totals"], "label": "Proposed schedule", "per_head": proposed["totals"]["total_cost"] / head, "clinical_label": self.plan["clinical_label"]},
                "alternative": {**alternative["totals"], "label": protocol["label"], "per_head": alternative["totals"]["total_cost"] / head, "protocol_cohorts": protocol_ids},
                "wording": _delta_sentence(baseline["totals"], proposed["totals"], alternative["totals"]),
                "plan_status": self.plan["clinical_label"],
                "assumptions_visible": {
                    "inclusive_loss": self.assumptions["inclusive_loss_per_first_treatment"],
                    "effectiveness": self.assumptions["effectiveness"],
                    "labor": self.assumptions["labor_cost_per_hour"],
                    "monitoring_does_not_prevent_disease": True,
                },
            }

    def sensitivity(self) -> dict[str, Any]:
        with self.lock:
            views = self.cohort_views()
            active = [row for row in views if row["active"]]
            assign = {row["cohort_id"]: "status_quo" for row in active}
            protocol_ids = [row["cohort_id"] for row in active if row["clinical_obligation"]][:8]
            base_loss = float(self.assumptions["inclusive_loss_per_first_treatment"])
            base_effect = float(self.assumptions["effectiveness"])
            original = self.assumptions
            try:
                return self._sensitivity_points(views, assign, protocol_ids, base_loss, base_effect, original)
            finally:
                self.assumptions = original

    def _sensitivity_points(self, views, assign, protocol_ids, base_loss, base_effect, original):
        points = []
        for loss_scale, effect in ((0.7, base_effect), (1.0, 0.0), (1.0, base_effect), (1.0, 0.7), (1.3, base_effect)):
            trial = dict(original)
            trial["inclusive_loss_per_first_treatment"] = base_loss * loss_scale
            self.assumptions = trial
            without = self._economics(views, assign, None)["totals"]["total_cost"]
            with_protocol = self._economics(views, assign, {
                "cohort_ids": protocol_ids,
                "effectiveness": effect,
                "cost_per_head": float(trial["metaphylaxis_cost_per_head"]),
            })["totals"]["total_cost"]
            points.append({
                "loss_scale": loss_scale,
                "effectiveness": effect,
                "delta_vs_baseline": round(with_protocol - without, 2),
                "label": "assumption-dependent scenario robustness",
            })
        flips = [point for point in points if point["delta_vs_baseline"] > 0]
        return {
            "points": points,
            "protocol_higher_cost_cases": len(flips),
            "cases": len(points),
            "allocation_note": "These knobs do not rewrite the executed schedule.",
        }

    def explain(self, cohort_id: str) -> dict[str, Any]:
        with self.lock:
            views = {row["cohort_id"]: row for row in self.cohort_views()}
            if cohort_id not in views:
                raise ValueError("Unknown cohort.")
            assignment = None if self.plan is None else self.plan["assignments"].get(cohort_id)
            unmet = False if self.plan is None else cohort_id in self.plan["unmet_clinical"]
            return explain_cohort(views[cohort_id], assignment, None, unmet) | {"cohort": views[cohort_id]}

    def commit_import(self, rows: list[dict[str, Any]]) -> None:
        with self.lock:
            self.cohorts = []
            for row in rows:
                row.setdefault("respiratory_observation_count", 0)
                row.setdefault("scenario_yard_offset", 0)
                row.setdefault("prior_metaphylaxis_status", "unknown")
                row.setdefault("vaccination_history", "unknown")
                self.cohorts.append(_coerce_cohort(row))
            self.events = []
            self.mode = "uploaded"
            self.plan = None
            self._prior_assignments = None
            self._prior_unmet = None
            self.provenance = {"data_mode": "uploaded", "not": "a claim that the file is a Merck extract", "rows": len(rows)}


def _monitoring_changes_disease(active: list[dict[str, Any]], assumptions: dict[str, Any]) -> bool:
    """True when extra pen checks change remaining burden or disease cost."""
    for row in active:
        cohort = {
            "cohort_id": row["cohort_id"],
            "cohort_size": row["head"],
            "expected_remaining": row["expected_remaining"],
            "observed_first": row["observed_first"],
        }
        base = evaluate_assignment(cohort, "status_quo", assumptions)
        watched = evaluate_assignment(cohort, "enhanced_observation", assumptions)
        if base["expected_remaining"] != watched["expected_remaining"]:
            return True
        if base["disease_cost"] != watched["disease_cost"]:
            return True
    return False


def _delta_sentence(baseline: dict[str, float], proposed: dict[str, float], alternative: dict[str, float]) -> str:
    labor_delta = proposed["labor_cost"] - baseline["labor_cost"]
    protocol_delta = alternative["total_cost"] - baseline["total_cost"]
    return (
        f"Under the selected assumptions, the proposed schedule changes labor cost by ${labor_delta:,.0f} "
        f"and does not change modeled disease burden. The hypothetical protocol changes projected total cost "
        f"by ${protocol_delta:,.0f} if the effectiveness assumption holds. This is not a statement that the plan will save that amount."
    )


def package_summary(name: str) -> dict[str, Any]:
    spec = CATALOG[name]
    return {"package": name, "hours": round(package_hours(name), 2), "purpose": spec["purpose"], "category": spec["category"]}
