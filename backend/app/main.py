"""Local API. Calculations stay in the service layer."""

from __future__ import annotations

import html

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from app.evidence import LEDGER
from app.explain import answer_question, morning_brief
from app.ingest import frame_from_upload, validate_cohort_frame
from app.model import CATALOG
from app.service import Workspace

app = FastAPI(title="BRDashboard", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
workspace = Workspace()


class ClockBody(BaseModel):
    clock: str


class RoleBody(BaseModel):
    role: str


class AssumptionBody(BaseModel):
    inclusive_loss_per_first_treatment: float | None = None
    effectiveness: float | None = None
    labor_cost_per_hour: float | None = None
    use_inclusive_morbidity_loss: bool | None = None
    metaphylaxis_cost_per_head: float | None = None


class MultiplierBody(BaseModel):
    staff: float | None = None
    chute: float | None = None
    vet: float | None = None


class ObservationBody(BaseModel):
    cohort_id: str
    day: int = Field(ge=1, le=45)
    detected: int = Field(ge=0, le=40)
    note: str = ""
    actor: str = "manager"


class ReviewBody(BaseModel):
    cohort_id: str
    status: str
    actor: str = "veterinarian"
    note: str = "Simulated status change. Not a clinical approval."


class AskBody(BaseModel):
    question: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": workspace.mode}


@app.get("/api/snapshot")
def snapshot() -> dict:
    return workspace.snapshot()


@app.get("/api/yards")
def yards() -> list:
    return workspace.snapshot()["yards"]


@app.get("/api/cohorts")
def cohorts() -> list:
    return workspace.snapshot()["cohorts"]


@app.get("/api/cohorts/{cohort_id}")
def cohort(cohort_id: str) -> dict:
    try:
        return workspace.explain(cohort_id)
    except ValueError as exc:
        raise HTTPException(404, "Cohort not on feed at this clock.") from exc


@app.post("/api/clock")
def set_clock(body: ClockBody) -> dict:
    try:
        workspace.set_clock(body.clock)
    except ValueError as exc:
        raise HTTPException(400, "Clock must be YYYY-MM-DD.") from exc
    return workspace.snapshot()["meta"]


@app.post("/api/role")
def set_role(body: RoleBody) -> dict:
    try:
        workspace.set_role(body.role)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"role": workspace.role}


@app.post("/api/scenarios/assumptions")
def assumptions(body: AssumptionBody) -> dict:
    workspace.update_assumptions(body.model_dump(exclude_none=True))
    return workspace.assumptions


@app.post("/api/scenarios/capacity")
def capacity(body: MultiplierBody) -> dict:
    workspace.set_multipliers(body.model_dump(exclude_none=True))
    return workspace.multipliers


@app.post("/api/optimization/solve")
def solve() -> dict:
    return workspace.solve()


@app.post("/api/decisions/compare")
def compare() -> dict:
    return workspace.compare()


@app.post("/api/sensitivity/run")
def sensitivity() -> dict:
    return workspace.sensitivity()


@app.post("/api/observations")
def observations(body: ObservationBody) -> dict:
    try:
        workspace.add_observation(body.cohort_id, body.day, body.detected, body.note, body.actor)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


@app.post("/api/reviews")
def reviews(body: ReviewBody) -> dict:
    try:
        workspace.set_review(body.cohort_id, body.status, body.actor, body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "simulated": True}


@app.post("/api/briefing")
def briefing() -> dict:
    return morning_brief(workspace.snapshot())


@app.post("/api/ask")
def ask(body: AskBody) -> dict:
    return answer_question(body.question, workspace.snapshot())


@app.get("/api/evidence")
def evidence() -> dict:
    return {"ledger": LEDGER, "model_version": workspace.snapshot()["meta"]["model_version"]}


@app.post("/api/data/validate")
async def validate(file: UploadFile = File(...)) -> dict:
    payload = await file.read()
    try:
        frame = frame_from_upload(file.filename or "upload.csv", payload)
        result = validate_cohort_frame(frame)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    workspace.pending_import = result if result["ok"] else None
    return {"ok": result["ok"], "errors": result["errors"], "preview": result["preview"], "row_count": result["row_count"]}


@app.post("/api/data/import")
def commit_import() -> dict:
    pending = workspace.pending_import
    if not pending or not pending.get("rows"):
        raise HTTPException(400, "Nothing validated to commit. Existing data was left in place.")
    workspace.commit_import(pending["rows"])
    workspace.pending_import = None
    return {"ok": True, "mode": workspace.mode, "rows": len(workspace.cohorts)}


@app.post("/api/data/demo")
def load_demo() -> dict:
    workspace.reload_demo()
    return {"ok": True, "mode": workspace.mode}


@app.get("/api/template")
def template() -> Response:
    header = "cohort_id,yard_id,pen_id,arrival_date,cohort_size,mean_arrival_weight_lb,sex_group,source_type,number_of_sources,transport_duration_hours,vaccination_history,pen_area_per_head,arrival_season\n"
    sample = "DEMO-1,PN,PN-P01,2026-03-01,100,580,steer,commingled,3,,unknown,12,winter\n"
    return Response(header + sample, media_type="text/csv")


def _report_style() -> str:
    return (
        "body{font-family:Georgia,serif;margin:32px;color:#241c14}"
        "h1{font-family:Arial,sans-serif}"
        "table{border-collapse:collapse;width:100%}"
        "td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left}"
    )


def _missing_week_html(snap: dict) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>BRDashboard decision summary</title>
    <style>{_report_style()}</style></head><body>
    <p>Synthetic demonstration. Not a diagnosis. Not a prescription. Veterinary review is simulated.</p>
    <h1>Decision summary · {html.escape(str(snap["clock"]))}</h1>
    <p>Head on feed {snap["metrics"]["head"]}. Observed first treatments {snap["metrics"]["observed_first"]}. Projected remaining {snap["metrics"]["projected_remaining"]}.</p>
    <p>The week has not been generated.</p>
    </body></html>"""


def _schedule_table(plan: dict) -> str:
    rows = []
    assignments = plan.get("assignments") or {}
    for cohort_id, package in sorted(assignments.items()):
        rows.append(
            "<tr><td>"
            + html.escape(str(cohort_id))
            + "</td><td>"
            + html.escape(str(package))
            + "</td></tr>"
        )
    body = "".join(rows)
    return (
        "<table><caption>Schedule</caption><thead><tr><th>Cohort</th><th>Package</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _comparison_table(comparison: dict) -> str:
    columns = (
        ("baseline", "Current operating approach"),
        ("optimized", "Proposed schedule"),
        ("alternative", "Hypothetical protocol"),
    )
    rows = []
    for key, title in columns:
        column = comparison[key]
        rows.append(
            "<tr><td>"
            + html.escape(title)
            + "</td><td>$"
            + f"{float(column['total_cost']):,.2f}"
            + "</td><td>"
            + f"{float(column['modeled_burden']):.1f}"
            + "</td><td>"
            + f"{float(column['labor_hours']):.1f}"
            + "</td><td>"
            + str(int(column["antimicrobial_exposed_head"]))
            + "</td></tr>"
        )
    body = "".join(rows)
    return (
        "<table><caption>Trade-offs under the visible assumptions</caption>"
        "<thead><tr><th>Case</th><th>Projected total</th><th>Modeled burden</th>"
        "<th>Labor hours</th><th>Antimicrobial-exposed head</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
        "<p>Modeled burden is expected first treatments, not animals already treated. "
        "The hypothetical protocol is not executed. "
        "Courses in this table are the antimicrobial-exposed head: one animal on a group protocol is one course. "
        "Current and proposed courses are 0 because those packages do not administer a drug.</p>"
    )


def _priority_html(snap: dict, plan: dict) -> str:
    lot = next(
        (row for row in snap.get("cohorts") or [] if row.get("active") and row.get("clinical_obligation")),
        None,
    )
    if lot is None:
        return "<p>No lot currently needs a person.</p>"
    cohort_id = str(lot["cohort_id"])
    package = (plan.get("assignments") or {}).get(cohort_id)
    unmet = cohort_id in (plan.get("unmet_clinical") or [])
    day = int(lot["day_on_feed"])
    if unmet or not package:
        recommendation = "Recommendation: the review does not fit this week. It stays on the list."
        review = "Veterinary review is still required. No slot was scheduled."
        when = f"Day {day} of 45. No action day was scheduled."
    else:
        spec = CATALOG.get(str(package), {})
        recommendation = "Recommendation: " + html.escape(str(package)) + ". " + html.escape(str(spec.get("purpose", "")))
        if spec.get("veterinary_review_required"):
            review = "Veterinary review is required for this package. It is a review slot, not a prescription."
        else:
            review = "This package is not a medication. It does not require a veterinary review."
        when = _when_sentence(day, str(package))
    return (
        f"<h2>Priority lot {html.escape(cohort_id)}</h2>"
        f"<p>Pen {html.escape(str(lot.get('pen_id', '')))}. {when} "
        f"{html.escape(str(lot.get('priority_reason', '')))}</p>"
        f"<p>{recommendation}</p><p>{review}</p>"
    )


def _when_sentence(day_on_feed: int, package: str) -> str:
    marker = "vet_day_"
    if marker in package:
        offset = int(package.rsplit(marker, 1)[1][:1])
        return f"Day {day_on_feed} of 45. The veterinary review falls on day {day_on_feed + offset} of 45."
    last = min(day_on_feed + 6, 45)
    return f"Day {day_on_feed} of 45. Pen checks in this package run from day {day_on_feed} through day {last}."


def _binding_html(plan: dict) -> str:
    binding = plan.get("binding")
    sentence = binding.get("sentence") if isinstance(binding, dict) else ""
    if sentence:
        return "<p>" + html.escape(str(sentence)) + "</p>"
    return "<p>No named resource shortage on this solve.</p>"


def _review_html(plan: dict) -> str:
    assignments = plan.get("assignments") or {}
    needing = [
        cohort_id
        for cohort_id, package in assignments.items()
        if CATALOG.get(str(package), {}).get("veterinary_review_required")
    ]
    return (
        f"<p>Veterinary review is required for {len(needing)} scheduled assessments. "
        "Those packages are review slots, not prescriptions.</p>"
    )


def _thin_html(snap: dict) -> str:
    active = [row for row in snap.get("cohorts") or [] if row.get("active")]
    partial = [row for row in active if row.get("missing")]
    thin = [str(row["cohort_id"]) for row in partial if row.get("insufficient")]
    named = ", ".join(html.escape(item) for item in thin[:8])
    suffix = f" Named here: {named}." if named else ""
    return (
        f"<p>{len(partial)} active cohorts are missing at least one arrival field. "
        f"{len(thin)} of them do not have enough history for a confident recommendation.{suffix} "
        "A missing field is not treated as low risk.</p>"
    )


def _decision_summary_html(snap: dict, comparison: dict) -> str:
    plan = snap["plan"]
    unmet_ids = plan.get("unmet_clinical") or []
    unmet = ", ".join(html.escape(str(item)) for item in unmet_ids) or "None"
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>BRDashboard decision summary</title>
    <style>{_report_style()}</style></head><body>
    <p>Synthetic demonstration. Not a diagnosis. Not a prescription. Veterinary review is simulated.</p>
    <h1>Decision summary · {html.escape(str(snap["clock"]))}</h1>
    {_priority_html(snap, plan)}
    {_binding_html(plan)}
    <p>{comparison["wording"]}</p>
    {_comparison_table(comparison)}
    <p>Plan status: {html.escape(str(comparison["plan_status"]))}. Unmet clinical reviews: {unmet}.</p>
    {_review_html(plan)}
    {_thin_html(snap)}
    <p>Inclusive loss assumption ${comparison["assumptions_visible"]["inclusive_loss"]:.2f}. Hypothetical effectiveness {comparison["assumptions_visible"]["effectiveness"]}. Labor ${comparison["assumptions_visible"]["labor"]:.2f}/hour.</p>
    <p>Head on feed {snap["metrics"]["head"]}. Observed first treatments {snap["metrics"]["observed_first"]}. Projected remaining {snap["metrics"]["projected_remaining"]}. Mode: {html.escape(str(snap["meta"]["data_mode"]))}. Model {html.escape(str(snap["meta"]["model_version"]))}.</p>
    {_schedule_table(plan)}
    </body></html>"""


@app.post("/api/reports/generate")
def report() -> HTMLResponse:
    snap = workspace.snapshot()
    if not snap.get("plan"):
        return HTMLResponse(_missing_week_html(snap))
    comparison = workspace.compare()
    return HTMLResponse(_decision_summary_html(snap, comparison))


@app.get("/api/reports/latest")
def report_get() -> HTMLResponse:
    return report()
