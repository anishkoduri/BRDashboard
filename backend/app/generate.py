"""Seeded, literature-informed synthetic feedyards. Not Merck observations."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from app.model import COEFS, MODEL_VERSION, REFERENCE_PROFILE_RATE, hazard_weights

SEED = 20261115
GENERATOR_VERSION = "synthetic-1.0.0"
CLOCK_DEFAULT = date(2026, 3, 18)
YARDS = (
    {
        "yard_id": "PN",
        "name": "Panhandle North",
        "region": "Northern Texas Panhandle",
        "cohorts": 28,
        "weight_mean": 560,
        "commingle": 0.55,
        "staff_hours_per_day": 14,
        "chute_head_per_day": 70,
        "vet_slots_per_day": 3,
        "hospital_pens": 10,
        "labor_cost_per_hour": 18,
        "yard_logit": 0.12,
        "completeness": 0.72,
    },
    {
        "yard_id": "HS",
        "name": "High Plains South",
        "region": "Southern Texas Panhandle",
        "cohorts": 26,
        "weight_mean": 640,
        "commingle": 0.28,
        "staff_hours_per_day": 18,
        "chute_head_per_day": 90,
        "vet_slots_per_day": 4,
        "hospital_pens": 12,
        "labor_cost_per_hour": 19,
        "yard_logit": -0.08,
        "completeness": 0.86,
    },
    {
        "yard_id": "WK",
        "name": "Western Kansas",
        "region": "Western Kansas",
        "cohorts": 24,
        "weight_mean": 590,
        "commingle": 0.40,
        "staff_hours_per_day": 12,
        "chute_head_per_day": 55,
        "vet_slots_per_day": 2,
        "hospital_pens": 8,
        "labor_cost_per_hour": 17,
        "yard_logit": 0.05,
        "completeness": 0.78,
    },
    {
        "yard_id": "PC",
        "name": "Prairie Central",
        "region": "Western Kansas",
        "cohorts": 22,
        "weight_mean": 575,
        "commingle": 0.36,
        "staff_hours_per_day": 9,
        "chute_head_per_day": 40,
        "vet_slots_per_day": 1,
        "hospital_pens": 5,
        "labor_cost_per_hour": 17,
        "yard_logit": 0.04,
        "completeness": 0.7,
    },
)


def _expit(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def _season(day: date) -> str:
    month = day.month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"


def _linear_units(row: dict[str, Any]) -> float:
    """Same directional terms as the assessment, without the intercept."""
    units = 0.0
    if row["mean_arrival_weight_lb"] is not None:
        units += max(0.0, (600 - row["mean_arrival_weight_lb"]) / 100) * COEFS["light_weight_per_100lb"]
    if row["number_of_sources"] is not None:
        commingled = row["source_type"] == "commingled" or row["number_of_sources"] >= 3
        if commingled:
            units += COEFS["commingled"]
        elif row["number_of_sources"] == 2:
            units += COEFS["extra_source"]
    if row["transport_duration_hours"] is not None:
        units += max(0.0, (row["transport_duration_hours"] - 8) / 4) * COEFS["transport_per_4h_over_8"]
    if row["arrival_season"] in {"fall", "winter"}:
        units += COEFS["fall_or_winter"]
    if row["pen_area_per_head"] is not None and row["pen_area_per_head"] < 14:
        units += COEFS["dense_pen"]
    if row["sex_group"] == "bull":
        units += COEFS["bulls"]
    if row["vaccination_history"] == "recorded_complete":
        units += COEFS["recorded_vaccination"]
    offset = row.get("scenario_yard_offset")
    if offset:
        units += float(offset)
    return units


def _calibrate(linear: np.ndarray, noise: np.ndarray) -> dict[str, float]:
    target_mean = 0.063
    target_tail = 0.1085
    best: dict[str, float] | None = None
    for scale in (0.15, 0.3, 0.45, 0.6, 0.8):
        low, high = -8.0, 1.5
        for _ in range(28):
            mid = (low + high) / 2
            rates = _expit(mid + linear + scale * noise)
            if float(rates.mean()) > target_mean:
                high = mid
            else:
                low = mid
        intercept = (low + high) / 2
        rates = _expit(intercept + linear + scale * noise)
        tail = float(np.mean(rates >= 0.15))
        score = abs(tail - target_tail)
        if best is None or score < best["score"]:
            best = {
                "intercept": float(intercept),
                "noise_scale": float(scale),
                "latent_mean": float(rates.mean()),
                "latent_tail": tail,
                "score": score,
            }
    assert best is not None
    return best


def _draw_rows(rng: np.random.Generator) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = date(2026, 2, 2)
    for yard in YARDS:
        for index in range(1, yard["cohorts"] + 1):
            arrival = start + timedelta(days=int(rng.integers(0, 44)))
            head = int(rng.integers(60, 180))
            weight = float(np.clip(rng.normal(yard["weight_mean"], 45), 420, 860))
            sources = int(rng.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1]))
            if rng.random() < yard["commingle"]:
                source_type = "commingled"
                sources = max(sources, 3)
            elif sources == 1:
                source_type = "single_ranch"
            else:
                source_type = "auction_mix"
            transport: float | None = float(np.clip(rng.normal(10, 4), 2, 28))
            vaccination = str(rng.choice(
                ["recorded_complete", "recorded_partial", "recorded_none", "unknown"],
                p=[0.46, 0.18, 0.12, 0.24],
            ))
            if rng.random() > yard["completeness"]:
                transport = None
            if rng.random() > yard["completeness"] + 0.05:
                vaccination = "unknown"
            area = float(np.clip(rng.normal(18, 4), 8, 32))
            if rng.random() > 0.9:
                area_value: float | None = None
            else:
                area_value = area
            sex = str(rng.choice(["steer", "heifer", "mixed", "bull"], p=[0.55, 0.28, 0.12, 0.05]))
            rows.append({
                "yard_id": yard["yard_id"],
                "pen_id": f"{yard['yard_id']}-P{(index % 8) + 1:02d}",
                "cohort_id": f"{yard['yard_id']}-{index:03d}",
                "arrival_date": arrival.isoformat(),
                "cohort_size": head,
                "sex_group": sex,
                "mean_arrival_weight_lb": round(weight, 1),
                "source_type": source_type,
                "number_of_sources": sources,
                "transport_duration_hours": None if transport is None else round(transport, 1),
                "weaning_history": str(rng.choice(["weaned", "freshly_weaned", "unknown"], p=[0.5, 0.3, 0.2])),
                "vaccination_history": vaccination,
                "prior_health_history": str(rng.choice(["unremarkable", "unknown", "prior_respiratory_note"], p=[0.62, 0.28, 0.1])),
                "pen_area_sq_m": None if area_value is None else round(area_value * head, 1),
                "pen_area_per_head": None if area_value is None else round(area_value, 2),
                "bunk_space_per_head": round(float(np.clip(rng.normal(0.45, 0.08), 0.2, 0.8)), 2),
                "receiving_ration_category": str(rng.choice(["starter", "grower", "hay_plus_concentrate"])),
                "prior_metaphylaxis_status": "unknown",
                "arrival_season": _season(arrival),
                "temperature_variation_f": round(float(np.clip(rng.normal(22, 6), 8, 40)), 1),
                "daily_precipitation_in": round(float(np.clip(rng.gamma(1.4, 0.12), 0, 1.8)), 2),
                "water_access_status": "available",
                "source_station_or_dataset": "synthetic seasonal proxy, not a weather service",
                "scenario_yard_offset": yard["yard_logit"],
                "respiratory_observation_count": int(rng.integers(0, 4)),
            })
    return rows


def _events_for(row: dict[str, Any], rate: float, rng: np.random.Generator, curve: np.ndarray) -> list[dict[str, Any]]:
    head = int(row["cohort_size"])
    latent_draws = rng.random(head) < rate
    latent_days = rng.choice(np.arange(1, 46), size=int(latent_draws.sum()), p=curve) if latent_draws.any() else np.array([])
    detected_mask = rng.random(latent_days.shape[0]) < 0.85 if latent_days.size else np.array([])
    by_day: dict[int, dict[str, int]] = {}
    for day, detected in zip(latent_days.tolist(), detected_mask.tolist()):
        bucket = by_day.setdefault(int(day), {"latent": 0, "detected": 0, "retreats": 0, "deaths": 0})
        bucket["latent"] += 1
        if detected:
            bucket["detected"] += 1
            if rng.random() < 0.12:
                bucket["retreats"] += 1
            if rng.random() < 0.015:
                bucket["deaths"] += 1
    arrival = date.fromisoformat(row["arrival_date"])
    events = []
    for day, counts in sorted(by_day.items()):
        events.append({
            "cohort_id": row["cohort_id"],
            "day_on_feed": day,
            "event_date": (arrival + timedelta(days=day - 1)).isoformat(),
            "latent_first_count": counts["latent"],
            "detected_first_count": counts["detected"],
            "subsequent_count": counts["retreats"],
            "mortality_count": counts["deaths"],
            "provenance": "simulated",
        })
    return events


def build_dataset(seed: int = SEED) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rows = _draw_rows(rng)
    linear = np.array([_linear_units(row) for row in rows])
    noise = rng.normal(0, 1, size=len(rows))
    calibration = _calibrate(linear, noise)
    curve = hazard_weights()
    rates = _expit(calibration["intercept"] + linear + calibration["noise_scale"] * noise)
    events: list[dict[str, Any]] = []
    for row, rate in zip(rows, rates.tolist()):
        row["latent_rate_sim"] = round(float(rate), 5)
        cohort_events = _events_for(row, float(rate), rng, curve)
        detected = sum(item["detected_first_count"] for item in cohort_events)
        latent = sum(item["latent_first_count"] for item in cohort_events)
        row["sim_detected_45"] = detected
        row["sim_latent_45"] = latent
        if detected > row["cohort_size"] or latent > row["cohort_size"]:
            raise RuntimeError("event count exceeded head count")
        events.extend(cohort_events)
    realized = np.array([row["sim_detected_45"] / row["cohort_size"] for row in rows])
    calibration_report = {
        "target_mean_first_treatment": 0.063,
        "target_share_at_or_above_15pct": 0.1085,
        "source": "Rojas et al. 2022 cohort summaries, calibration targets only",
        "generator_intercept": calibration["intercept"],
        "noise_scale": calibration["noise_scale"],
        "latent_mean": calibration["latent_mean"],
        "latent_share_at_or_above_15": calibration["latent_tail"],
        "realized_detected_mean": float(realized.mean()),
        "realized_share_at_or_above_15": float(np.mean(realized >= 0.15)),
        "reference_profile_rate_before_shared_intercept": REFERENCE_PROFILE_RATE,
        "note": "Matching a published mean is not clinical validation. Assessment does not see cohort noise.",
    }
    return {
        "cohorts": rows,
        "events": events,
        "yards": [
            {key: value for key, value in yard.items() if key != "cohorts"}
            | {"cohort_target": yard["cohorts"]}
            for yard in YARDS
        ],
        "calibration": calibration_report,
        "seed": seed,
        "generator_version": GENERATOR_VERSION,
        "model_version": MODEL_VERSION,
        "default_clock": CLOCK_DEFAULT.isoformat(),
        "assessment_intercept": calibration["intercept"],
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def dictionary_rows() -> list[dict[str, str]]:
    return [
        {"variable": "cohort_id", "unit": "id", "definition": "Arrival cohort identifier", "range": "unique", "missing_policy": "required", "source_class": "generated"},
        {"variable": "yard_id", "unit": "id", "definition": "Fictional feedyard", "range": "PN HS WK PC", "missing_policy": "required", "source_class": "generated"},
        {"variable": "pen_id", "unit": "id", "definition": "Pen holding the cohort", "range": "yard pen code", "missing_policy": "required", "source_class": "generated"},
        {"variable": "arrival_date", "unit": "date", "definition": "Day the cohort arrived", "range": "ISO date", "missing_policy": "required", "source_class": "generated"},
        {"variable": "cohort_size", "unit": "head", "definition": "Animals in the cohort", "range": "1-500", "missing_policy": "required; must be positive", "source_class": "generated"},
        {"variable": "mean_arrival_weight_lb", "unit": "lb", "definition": "Mean arrival weight", "range": "400-900", "missing_policy": "unknown widens uncertainty; not treated as heavy", "source_class": "generated"},
        {"variable": "sex_group", "unit": "category", "definition": "Steer, heifer, mixed, or bull", "range": "listed", "missing_policy": "unknown adds no sex shift", "source_class": "generated"},
        {"variable": "source_type", "unit": "category", "definition": "Procurement pattern", "range": "single_ranch auction_mix commingled", "missing_policy": "unknown is not single-source", "source_class": "generated"},
        {"variable": "number_of_sources", "unit": "count", "definition": "Source groups mixed into the cohort", "range": "1-8", "missing_policy": "unknown adds no commingling credit", "source_class": "generated"},
        {"variable": "transport_duration_hours", "unit": "hours", "definition": "Transit time", "range": "0-48", "missing_policy": "unknown is not a short haul", "source_class": "generated"},
        {"variable": "vaccination_history", "unit": "category", "definition": "What the paperwork says", "range": "recorded_complete recorded_partial recorded_none unknown", "missing_policy": "unknown is not protective", "source_class": "generated"},
        {"variable": "pen_area_per_head", "unit": "m^2/head", "definition": "Pen space per animal. The only density term in the model.", "range": "5-40", "missing_policy": "unknown does not assume spare space", "source_class": "generated"},
        {"variable": "pen_area_sq_m", "unit": "m^2", "definition": "Descriptive total. Not an independent risk term.", "range": "positive", "missing_policy": "optional", "source_class": "generated"},
        {"variable": "arrival_season", "unit": "category", "definition": "Season of arrival", "range": "winter spring summer fall", "missing_policy": "unknown adds no season shift", "source_class": "generated"},
        {"variable": "detected_first_count", "unit": "head", "definition": "Simulated recorded first BRD treatments that day", "range": "0-cohort size", "missing_policy": "absent day means zero recorded events", "source_class": "simulated"},
        {"variable": "latent_first_count", "unit": "head", "definition": "Simulator construct. Not measured disease.", "range": "0-cohort size", "missing_policy": "simulation only", "source_class": "simulated"},
        {"variable": "inclusive_loss_per_first_treatment", "unit": "USD", "definition": "Rojas historical inclusive cost/lost value per morbid animal", "range": "user editable", "missing_policy": "default 151.18 labeled historical", "source_class": "literature-parameter"},
        {"variable": "prior_metaphylaxis_status", "unit": "category", "definition": "Not used as a protective coefficient. Rojas noted incomplete metaphylaxis history.", "range": "unknown in the demo", "missing_policy": "unknown is not evidence of no prior treatment", "source_class": "assumed"},
    ]


def write_dataset(root: Path, seed: int = SEED) -> dict[str, Any]:
    dataset = build_dataset(seed)
    demo = root / "data" / "demo"
    public_rows = []
    truth_rows = []
    hidden = {"latent_rate_sim", "sim_detected_45", "sim_latent_45"}
    for row in dataset["cohorts"]:
        public_rows.append({key: value for key, value in row.items() if key not in hidden})
        truth_rows.append({
            "cohort_id": row["cohort_id"],
            "latent_rate_sim": row["latent_rate_sim"],
            "sim_detected_45": row["sim_detected_45"],
            "sim_latent_45": row["sim_latent_45"],
            "note": "Simulator truth for tests. The assessment API does not read this file.",
        })
    _write_csv(demo / "cohorts.csv", public_rows)
    _write_csv(demo / "sim_truth.csv", truth_rows)
    _write_csv(demo / "health_events.csv", dataset["events"])
    _write_csv(demo / "yards.csv", dataset["yards"])
    pens = []
    seen: set[str] = set()
    for row in dataset["cohorts"]:
        if row["pen_id"] not in seen:
            seen.add(row["pen_id"])
            pens.append({"pen_id": row["pen_id"], "yard_id": row["yard_id"]})
    _write_csv(demo / "pens.csv", pens)
    _write_csv(demo / "data_dictionary.csv", dictionary_rows())
    protocols = []
    for yard in dataset["yards"]:
        protocols.append({
            "yard_id": yard["yard_id"],
            "policy": "status_quo_pen_checks",
            "description": "Daily pen checks on the existing rider rotation. Veterinary review when a rider pulls an animal. No automatic group medication.",
            "pen_check": "scheduled",
            "automatic_metaphylaxis": "no",
        })
    _write_csv(demo / "baseline_protocols.csv", protocols)
    provenance = {
        "data_mode": "synthetic demonstration",
        "not": "Merck feedyard observations",
        "seed": seed,
        "generator_version": GENERATOR_VERSION,
        "model_version": MODEL_VERSION,
        "calibration": dataset["calibration"],
        "redistributable": True,
        "weather": "Synthetic seasonal draws. NASA POWER and NOAA were not called.",
    }
    (demo / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    assumptions = {
        "assessment_intercept": dataset["assessment_intercept"],
        "inclusive_loss_per_first_treatment": 151.18,
        "inclusive_loss_source": "Rojas et al. 2022 historical scenario figure, not a 2026 quote",
        "use_inclusive_morbidity_loss": True,
        "metaphylaxis_cost_per_head": 23.60,
        "metaphylaxis_cost_source": "Rojas et al. 2022 single-scenario cost, historical",
        "default_effectiveness": 0.50,
        "effectiveness_label": "hypothetical scenario knob, not an estimated treatment effect",
        "labor_cost_per_hour": 18.0,
        "labor_cost_label": "assumption",
        "component_treatment_cost": 80.0,
        "performance_loss_per_case": 70.0,
        "mortality_loss_per_head": 1400.0,
        "mortality_forecast": "none — observed simulator deaths only; no mortality model",
    }
    (demo / "assumptions.json").write_text(json.dumps(assumptions, indent=2), encoding="utf-8")
    (root / "data" / "dictionary").mkdir(parents=True, exist_ok=True)
    _write_csv(root / "data" / "dictionary" / "data_dictionary.csv", dictionary_rows())
    (root / "data" / "provenance").mkdir(parents=True, exist_ok=True)
    (root / "data" / "provenance" / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return dataset
