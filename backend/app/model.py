"""Risk, timing, and cost calculations.

Every number the API returns is produced here. Coefficients are labeled
assumptions with literature-supported direction, not fitted effects.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import numpy as np
from scipy import stats

MODEL_VERSION = "brd-assumption-1.0.0"
HAZARD_VERSION = "gamma-2.4-7.5-truncated-1-45"
REFERENCE_PROFILE_RATE = 0.05
INCLUSIVE_LOSS_USD = 151.18
METAPHYLAXIS_COST_USD = 23.60
DEFAULT_EFFECTIVENESS = 0.50
DEFAULT_LABOR_USD = 18.0
VET_VISIT_USD = 45.0
KAPPA = 40.0

# Log-odds per unit. Signs follow the reviews; magnitudes are hypothetical.
COEFS: dict[str, float] = {
    "light_weight_per_100lb": 0.22,
    "extra_source": 0.14,
    "transport_per_4h_over_8": 0.12,
    "commingled": 0.28,
    "fall_or_winter": 0.16,
    "dense_pen": 0.15,
    "bulls": 0.08,
    "recorded_vaccination": -0.10,
}

COEF_NOTES: dict[str, str] = {
    "light_weight_per_100lb": "Lighter arrivals are a repeatedly studied risk context (Adekunle 2026 review). Magnitude is hypothetical.",
    "extra_source": "Commingling and multiple sources are frequently studied risk contexts, not weights.",
    "transport_per_4h_over_8": "Longer transport is a studied stressor. Hours above 8 are scaled by a hypothetical coefficient.",
    "commingled": "Commingling is directional context only. Not a measured effect size.",
    "fall_or_winter": "Season modifies outcomes in Cheek et al. 2026; this shift is hypothetical.",
    "dense_pen": "Stocking density is studied often. Only area per head is used, so total area is not double-counted.",
    "bulls": "Sex is a studied covariate. The bull shift is hypothetical and small.",
    "recorded_vaccination": "A recorded complete vaccination history is a hypothetical modest reduction. Unknown history is not protective.",
}


@lru_cache(maxsize=1)
def hazard_weights() -> np.ndarray:
    """Front-loaded timing curve. Assumption, not a fitted Babcock hazard."""
    days = np.arange(1, 46)
    weights = stats.gamma.pdf(days, a=2.4, scale=7.5)
    total = float(weights.sum())
    return weights / total


def cumulative_hazard(day_on_feed: int, weights: np.ndarray | None = None) -> float:
    curve = hazard_weights() if weights is None else weights
    if day_on_feed <= 0:
        return 0.0
    if day_on_feed >= 45:
        return 1.0
    return float(curve[:day_on_feed].sum())


def expit(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def logit(probability: float) -> float:
    p = min(max(probability, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "unknown", "missing", "na", "n/a"}:
        return True
    return False


def _factor(name: str, units: float, coefficient: float) -> dict[str, Any]:
    return {
        "factor": name,
        "units": round(units, 4),
        "coefficient": coefficient,
        "log_odds": round(units * coefficient, 4),
        "note": COEF_NOTES[name],
        "label": "assumption",
    }


def covariate_linear(row: dict[str, Any], intercept: float) -> dict[str, Any]:
    """Arrival linear predictor from fields available at assessment.

    Unknown vaccination, transport, source, or density does not pull risk down.
    """
    missing: list[str] = []
    factors: list[dict[str, Any]] = []
    kappa_scale = 1.0
    linear = intercept

    weight = row.get("mean_arrival_weight_lb")
    if _blank(weight):
        missing.append("mean_arrival_weight_lb")
        kappa_scale *= 0.75
    else:
        units = max(0.0, (600.0 - float(weight)) / 100.0)
        factor = _factor("light_weight_per_100lb", units, COEFS["light_weight_per_100lb"])
        factors.append(factor)
        linear += factor["log_odds"]

    sources = row.get("number_of_sources")
    source_type = str(row.get("source_type") or "")
    if _blank(sources) and source_type in {"", "unknown", "missing"}:
        missing.append("source_history")
        kappa_scale *= 0.8
    else:
        commingled = source_type == "commingled" or (not _blank(sources) and float(sources) >= 3)
        if commingled:
            factor = _factor("commingled", 1.0, COEFS["commingled"])
            factors.append(factor)
            linear += factor["log_odds"]
        elif not _blank(sources) and float(sources) == 2:
            factor = _factor("extra_source", 1.0, COEFS["extra_source"])
            factors.append(factor)
            linear += factor["log_odds"]

    transport = row.get("transport_duration_hours")
    if _blank(transport):
        missing.append("transport_duration_hours")
        kappa_scale *= 0.75
    else:
        units = max(0.0, (float(transport) - 8.0) / 4.0)
        factor = _factor("transport_per_4h_over_8", units, COEFS["transport_per_4h_over_8"])
        factors.append(factor)
        linear += factor["log_odds"]

    season = str(row.get("arrival_season") or "")
    if season in {"fall", "winter"}:
        factor = _factor("fall_or_winter", 1.0, COEFS["fall_or_winter"])
        factors.append(factor)
        linear += factor["log_odds"]
    elif _blank(season):
        missing.append("arrival_season")

    area = row.get("pen_area_per_head")
    if _blank(area):
        missing.append("pen_area_per_head")
        kappa_scale *= 0.85
    elif float(area) < 14.0:
        factor = _factor("dense_pen", 1.0, COEFS["dense_pen"])
        factors.append(factor)
        linear += factor["log_odds"]

    sex = str(row.get("sex_group") or "")
    if sex == "bull":
        factor = _factor("bulls", 1.0, COEFS["bulls"])
        factors.append(factor)
        linear += factor["log_odds"]

    offset = row.get("scenario_yard_offset")
    if not _blank(offset) and float(offset) != 0:
        factor = {
            "factor": "scenario_yard_offset",
            "units": round(float(offset), 4),
            "coefficient": 1.0,
            "log_odds": round(float(offset), 4),
            "note": "Fictional yard shift shared with the simulator. Not an estimated yard effect.",
            "label": "assumption",
        }
        factors.append(factor)
        linear += factor["log_odds"]

    vaccination = str(row.get("vaccination_history") or "")
    if vaccination == "recorded_complete":
        factor = _factor("recorded_vaccination", 1.0, COEFS["recorded_vaccination"])
        factors.append(factor)
        linear += factor["log_odds"]
    elif vaccination in {"", "unknown", "missing"}:
        missing.append("vaccination_history")
        kappa_scale *= 0.7

    mu = min(max(expit(linear), 0.005), 0.8)
    return {
        "mu": mu,
        "kappa": KAPPA * kappa_scale,
        "linear": linear,
        "factors": factors,
        "missing": missing,
        "insufficient": len(missing) >= 3,
    }


def exceedance_probability(head: int, mu: float, kappa: float, threshold: float = 0.15) -> float:
    if head <= 0:
        return 0.0
    alpha = max(mu * kappa, 1e-3)
    beta = max((1 - mu) * kappa, 1e-3)
    minimum = int(math.ceil(threshold * head - 1e-9))
    if minimum <= 0:
        return 1.0
    if minimum > head:
        return 0.0
    return float(1 - stats.betabinom.cdf(minimum - 1, head, alpha, beta))


def rate_band(mu: float, kappa: float) -> tuple[float, float]:
    alpha = max(mu * kappa, 1e-3)
    beta = max((1 - mu) * kappa, 1e-3)
    low = float(stats.beta.ppf(0.1, alpha, beta))
    high = float(stats.beta.ppf(0.9, alpha, beta))
    return low, high


def update_rate(mu: float, kappa: float, head: int, observed: int, hazard_to_date: float) -> tuple[float, float]:
    """Beta update on the cumulative recorded-treatment probability, mapped back to 45 days.

    `observed` must already be filtered to events on or before the assessment day.
    """
    seen = min(max(int(observed), 0), int(head))
    if hazard_to_date <= 1e-6 or head <= 0:
        return mu, kappa
    cumulative = min(mu * hazard_to_date, 0.98)
    alpha = cumulative * kappa
    beta = (1 - cumulative) * kappa
    alpha_post = alpha + seen
    beta_post = beta + (head - seen)
    cumulative_post = alpha_post / (alpha_post + beta_post)
    updated = min(max(cumulative_post / hazard_to_date, 0.005), 0.9)
    return updated, alpha_post + beta_post


def remaining_expected(mu: float, hazard_to_date: float, at_risk: int) -> float:
    """Expected additional first treatments among animals not yet recorded."""
    if at_risk <= 0 or hazard_to_date >= 1:
        return 0.0
    denominator = 1 - mu * hazard_to_date
    if denominator <= 1e-6:
        return float(at_risk)
    probability = min(max(mu * (1 - hazard_to_date) / denominator, 0.0), 1.0)
    return float(at_risk) * probability


def assess_cohort(
    row: dict[str, Any],
    observed_first: int,
    day_on_feed: int,
    intercept: float,
    weights: np.ndarray | None = None,
) -> dict[str, Any]:
    profile = covariate_linear(row, intercept)
    curve = hazard_weights() if weights is None else weights
    hazard = cumulative_hazard(day_on_feed, curve)
    head = int(row["cohort_size"])
    mu, kappa = update_rate(profile["mu"], profile["kappa"], head, observed_first, hazard)
    low, high = rate_band(mu, kappa)
    at_risk = max(head - int(observed_first), 0)
    remaining = remaining_expected(mu, hazard, at_risk)
    probability = exceedance_probability(head, mu, kappa)
    per_hundred = mu * 100
    return {
        "model_version": MODEL_VERSION,
        "hazard_version": HAZARD_VERSION,
        "arrival_mu": profile["mu"],
        "updated_mu": mu,
        "kappa": kappa,
        "expected_per_100": per_hundred,
        "expected_first_count": mu * head,
        "expected_remaining": remaining,
        "observed_first": int(observed_first),
        "p_exceed_15": probability,
        "band_low": low,
        "band_high": high,
        "band_label": "assumption-dependent range",
        "factors": profile["factors"],
        "missing": profile["missing"],
        "insufficient": profile["insufficient"],
        "hazard_to_date": hazard,
        "day_on_feed": day_on_feed,
        "research_threshold": 0.15,
        "research_threshold_note": "Rojas et al. 2022 cohort classification, not a clinical trigger.",
    }


def package_catalog() -> dict[str, dict[str, Any]]:
    """Seven-day resource patterns. Hours are totals for the cohort that week."""
    base = [0.4, 0.2, 0.4, 0.2, 0.4, 0.2, 0.2]
    enhanced_add = [0.6, 0.1, 0.6, 0.1, 0.6, 0.1, 0.1]
    catalog: dict[str, dict[str, Any]] = {
        "status_quo": {
            "category": "routine",
            "hours": base,
            "vet": [0, 0, 0, 0, 0, 0, 0],
            "chute": [0, 0, 0, 0, 0, 0, 0],
            "hospital": 0,
            "veterinary_review_required": False,
            "purpose": "Standard pen checks already in the yard baseline.",
        },
        "enhanced_observation": {
            "category": "monitoring",
            "hours": [base[i] + enhanced_add[i] for i in range(7)],
            "vet": [0, 0, 0, 0, 0, 0, 0],
            "chute": [0, 0, 0, 0, 0, 0, 0],
            "hospital": 0,
            "veterinary_review_required": False,
            "purpose": "More pen checks. Adds detection effort, not a disease-prevention credit.",
        },
        "records_review": {
            "category": "records",
            "hours": [base[0], base[1] + 1.4, *base[2:]],
            "vet": [0, 0, 0, 0, 0, 0, 0],
            "chute": [0, 0, 0, 0, 0, 0, 0],
            "hospital": 0,
            "veterinary_review_required": False,
            "purpose": "Chase missing arrival, source, or vaccination history.",
        },
    }
    for day in range(3):
        vet_hours = base.copy()
        vet_hours[day] += 1.2
        vet_slots = [0, 0, 0, 0, 0, 0, 0]
        vet_slots[day] = 1
        chute = [0, 0, 0, 0, 0, 0, 0]
        chute[day] = 12
        catalog[f"vet_day_{day}"] = {
            "category": "clinical_review",
            "hours": vet_hours,
            "vet": vet_slots,
            "chute": chute,
            "hospital": 1,
            "veterinary_review_required": True,
            "purpose": f"Veterinary assessment on planner day {day + 1}. Not a prescription.",
        }
        enh = [base[i] + enhanced_add[i] for i in range(7)]
        enh[day] += 1.2
        catalog[f"enhanced_vet_day_{day}"] = {
            "category": "clinical_review",
            "hours": enh,
            "vet": vet_slots,
            "chute": chute,
            "hospital": 1,
            "veterinary_review_required": True,
            "purpose": "Extra checks plus a veterinary assessment. Not a prescription.",
        }
    return catalog


CATALOG = package_catalog()
VET_PACKAGES = tuple(name for name, item in CATALOG.items() if item["category"] == "clinical_review")


def package_hours(name: str) -> float:
    return float(sum(CATALOG[name]["hours"]))


def clinical_obligation(assessment: dict[str, Any], respiratory_flags: int, head: int = 1) -> bool:
    """Scarce veterinary-review trigger. Not a diagnosis and not a drug order."""
    head = max(int(head), 1)
    running_hot = assessment["observed_first"] / head >= 0.10 and assessment["day_on_feed"] >= 5
    flagged = respiratory_flags >= 3 and assessment["observed_first"] >= 1
    return bool(assessment["p_exceed_15"] >= 0.55 or running_hot or flagged)


_TRIGGER_ON = "The review trigger is on."
_TRIGGER_OFF = "The review trigger stays off through the remaining head."


def distance_to_trigger(
    row: dict[str, Any],
    observed_first: int,
    day_on_feed: int,
    intercept: float,
    respiratory_flags: int,
    *,
    already_on: bool,
) -> dict[str, Any]:
    """Smallest added count, through today, that turns the review trigger on."""
    if already_on:
        return {"distance_to_trigger": None, "distance_sentence": _TRIGGER_ON}
    head = int(row["cohort_size"])
    observed = max(int(observed_first), 0)
    remaining = max(head - observed, 0)
    if int(day_on_feed) > 45 or remaining <= 0:
        return {"distance_to_trigger": None, "distance_sentence": _TRIGGER_OFF}
    clock_day = min(int(day_on_feed), 45)

    def turns_on(extra: int) -> bool:
        assessment = assess_cohort(row, observed + extra, clock_day, intercept)
        return clinical_obligation(assessment, respiratory_flags, head)

    found = _smallest_added_count(turns_on, remaining)
    if found is None:
        return {"distance_to_trigger": None, "distance_sentence": _TRIGGER_OFF}
    sentence = f"{found} more recorded first treatments turn the review trigger on."
    return {"distance_to_trigger": found, "distance_sentence": sentence}


def _smallest_added_count(turns_on: Callable[[int], bool], remaining: int) -> int | None:
    if remaining <= 40:
        return _scan_window(turns_on, 1, remaining)
    # shortcut: remaining head above 40 steps by 5, switch to a 1..n scan if a trigger turns off after it turns on
    stride = 5
    hit = _first_stride_hit(turns_on, remaining, stride)
    if hit is None:
        return _scan_window(turns_on, _tail_start(remaining, stride), remaining)
    found = _scan_window(turns_on, hit - stride + 1, hit)
    return hit if found is None else found


def _first_stride_hit(turns_on: Callable[[int], bool], remaining: int, stride: int) -> int | None:
    extra = stride
    while extra < remaining:
        if turns_on(extra):
            return extra
        extra += stride
    return None


def _tail_start(remaining: int, stride: int) -> int:
    return ((remaining - 1) // stride) * stride + 1


def _scan_window(turns_on: Callable[[int], bool], start: int, stop: int) -> int | None:
    for extra in range(max(start, 1), stop + 1):
        if turns_on(extra):
            return extra
    return None


def evaluate_assignment(
    cohort: dict[str, Any],
    package: str,
    assumptions: dict[str, Any],
    protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cost one cohort under one package. Monitoring does not shrink disease burden."""
    labor_rate = float(assumptions["labor_cost_per_hour"])
    inclusive = float(assumptions["inclusive_loss_per_first_treatment"])
    use_inclusive = bool(assumptions.get("use_inclusive_morbidity_loss", True))
    hours = package_hours(package)
    labor = hours * labor_rate
    remaining = float(cohort["expected_remaining"])
    observed = float(cohort["observed_first"])
    effect = 0.0
    protocol_cost = 0.0
    exposed = 0
    if protocol and cohort["cohort_id"] in protocol.get("cohort_ids", []):
        effect = float(protocol.get("effectiveness", 0.0))
        remaining = remaining * (1 - effect)
        protocol_cost = float(protocol.get("cost_per_head", 0.0)) * int(cohort["cohort_size"])
        exposed = int(cohort["cohort_size"])
    burden = observed + remaining
    if use_inclusive:
        disease = burden * inclusive
        performance = 0.0
        mortality_dollars = 0.0
    else:
        disease = burden * float(assumptions.get("component_treatment_cost", 0.0))
        performance = burden * float(assumptions.get("performance_loss_per_case", 0.0))
        mortality_dollars = 0.0
    vet_fee = VET_VISIT_USD if CATALOG[package]["category"] == "clinical_review" else 0.0
    total = labor + disease + performance + mortality_dollars + protocol_cost + vet_fee
    return {
        "cohort_id": cohort["cohort_id"],
        "package": package,
        "labor_hours": hours,
        "labor_cost": labor,
        "disease_cost": disease,
        "performance_cost": performance,
        "mortality_cost": mortality_dollars,
        "protocol_cost": protocol_cost,
        "vet_fee": vet_fee,
        "total_cost": total,
        "expected_remaining": remaining,
        "observed_first": observed,
        "modeled_burden": burden,
        "antimicrobial_exposed_head": exposed,
        "effectiveness_applied": effect,
        "monitoring_changes_disease": False,
    }


def sum_plan(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys = [
        "labor_hours",
        "labor_cost",
        "disease_cost",
        "performance_cost",
        "mortality_cost",
        "protocol_cost",
        "vet_fee",
        "total_cost",
        "expected_remaining",
        "observed_first",
        "modeled_burden",
        "antimicrobial_exposed_head",
    ]
    totals = {key: 0.0 for key in keys}
    for row in rows:
        for key in keys:
            totals[key] += float(row[key])
    parts = (
        totals["labor_cost"]
        + totals["disease_cost"]
        + totals["performance_cost"]
        + totals["mortality_cost"]
        + totals["protocol_cost"]
        + totals["vet_fee"]
    )
    if abs(parts - totals["total_cost"]) > 0.05:
        raise RuntimeError("cost components do not reconcile")
    return totals
