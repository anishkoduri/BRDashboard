"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Horizon } from "@/components/Horizon";
import { InkIcon } from "@/components/InkIcon";
import { useWorkspace } from "@/components/workspace";
import { WorkMark } from "@/components/WorkMark";
import { windowSentence } from "@/lib/horizon";
import type { Plan } from "@/lib/types";
import { compact } from "@/lib/utils";

function bindingSentence(plan: Plan) {
  const sentence = plan.binding?.sentence;
  if (typeof sentence !== "string") return "";
  return sentence.trim();
}

function movedOffWeek(plan: Plan) {
  return (plan.diff ?? []).filter((row) => row.entered_unmet).map((row) => row.cohort_id);
}

function changedLots(plan: Plan) {
  return new Set(
    (plan.diff ?? [])
      .filter((row) => row.entered_unmet || row.left_unmet || (Boolean(row.before) && row.before !== row.after))
      .map((row) => row.cohort_id),
  );
}

export default function PlannerPage() {
  const { snap, link, error, setCapacity, refresh } = useWorkspace();
  const [staff, setStaff] = useState(snap?.multipliers.staff ?? 1);
  const [vet, setVet] = useState(snap?.multipliers.vet ?? 1);
  const [chute, setChute] = useState(snap?.multipliers.chute ?? 1);
  const previous = useRef<string | null>(null);
  const [riseKey, setRiseKey] = useState(0);
  const [announcement, setAnnouncement] = useState("");
  const plan = snap?.plan ?? null;
  const sentence = plan ? bindingSentence(plan) : "";
  const hero = !plan ? "The week has not been generated." : sentence || plan.message;

  useEffect(() => {
    const next = snap?.multipliers.staff;
    if (typeof next === "number") setStaff(next);
    if (typeof snap?.multipliers.vet === "number") setVet(snap.multipliers.vet);
    if (typeof snap?.multipliers.chute === "number") setChute(snap.multipliers.chute);
  }, [snap?.multipliers.staff, snap?.multipliers.vet, snap?.multipliers.chute]);

  useEffect(() => {
    if (!plan) return;
    const signature = `${sentence}\u0000${plan.unmet_clinical.length}`;
    if (previous.current === null) {
      previous.current = signature;
      return;
    }
    if (previous.current === signature) return;
    previous.current = signature;
    setRiseKey((key) => key + 1);
    setAnnouncement(sentence || plan.message);
  }, [plan, sentence]);

  if (!snap) {
    return (
      <div className="screen">
        {link === "failed" ? (
          <>
            <p role="alert" className="alert">{error ? `The snapshot is unavailable. ${error}` : "The snapshot is unavailable."}</p>
            <button className="key" type="button" onClick={() => refresh()}>Retry</button>
          </>
        ) : (
          <WorkMark label="Loading the week." kind="week" />
        )}
      </div>
    );
  }

  const priority = snap.cohorts.find((row) => row.active && row.clinical_obligation) ?? null;
  const priorityPackage = priority && plan ? plan.assignments[priority.cohort_id] : undefined;
  const horizon = priority ? windowSentence(priority.day_on_feed, priorityPackage) : null;
  const reviewDays = [0, 1, 2].map((day) => Object.values(plan?.assignments ?? {}).filter((name) => name.includes(`vet_day_${day}`)).length);
  const movedOff = plan ? movedOffWeek(plan) : [];
  const changed = plan ? changedLots(plan) : new Set<string>();
  const stepping = riseKey > 0;
  const assignmentRows = plan
    ? Object.entries(plan.assignments)
        .map(([cohortId, packageName]) => {
          const cohort = snap.cohorts.find((row) => row.cohort_id === cohortId);
          return { cohortId, packageName, yard: cohort?.yard_id ?? "", pen: cohort?.pen_id ?? "" };
        })
        .sort((left, right) => left.cohortId.localeCompare(right.cohortId))
    : [];

  return (
    <div className="screen">
      <p className="sr-only" aria-live="polite">{announcement}</p>
      <article key={riseKey} className="focus-plate" data-rise={riseKey > 0 ? "true" : "false"}>
        <h1 className={sentence ? "sentence miss" : "sentence"}>{hero}</h1>
        {plan ? (
          <>
            <p className={plan.solver_status === "INFEASIBLE" ? "status miss" : plan.proved_optimal ? "status fits" : "status"}>
              {plan.solver_status === "INFEASIBLE" ? "Does not fit." : plan.proved_optimal ? "Proved optimal." : "Feasible, not proved."}
            </p>
            <p className="note">Solver {plan.solver_status}. {plan.solve_seconds}s.</p>
          </>
        ) : null}
      </article>
      {horizon ? <Horizon day={horizon.day} actionDay={horizon.actionDay} detail={`${priority?.cohort_id ?? ""}. ${horizon.detail}`} /> : null}
      {plan ? <p className="note">Veterinary reviews scheduled this week: day 1 {reviewDays[0]}, day 2 {reviewDays[1]}, day 3 {reviewDays[2]}. A review is not a dose.</p> : null}
      <div className="control-row">
      <label className="field crew" htmlFor="crew">
        <span>Crew on the yard <span className="figure moved">{staff.toFixed(2)}</span></span>
        <input
          type="range"
          min={0.4}
          max={1.2}
          step={0.05}
          value={staff}
          id="crew"
          name="crew"
          onChange={(event) => setStaff(Number(event.target.value))}
          onPointerUp={(event) => setCapacity({ staff: Number(event.currentTarget.value) })}
          onKeyUp={(event) => {
            setCapacity({ staff: Number(event.currentTarget.value) });
          }}
        />
      </label>
      <label className="field crew" htmlFor="vet-slots">
        <span>Veterinary slots <span className="figure">{vet.toFixed(2)}</span></span>
        <input
          type="range"
          min={0.25}
          max={1.2}
          step={0.05}
          value={vet}
          id="vet-slots"
          name="vet-slots"
          onChange={(event) => setVet(Number(event.target.value))}
          onPointerUp={(event) => setCapacity({ vet: Number(event.currentTarget.value) })}
          onKeyUp={(event) => setCapacity({ vet: Number(event.currentTarget.value) })}
        />
      </label>
      <label className="field crew" htmlFor="chute">
        <span>Chute capacity <span className="figure">{chute.toFixed(2)}</span></span>
        <input
          type="range"
          min={0.2}
          max={1.2}
          step={0.05}
          value={chute}
          id="chute"
          name="chute"
          onChange={(event) => setChute(Number(event.target.value))}
          onPointerUp={(event) => setCapacity({ chute: Number(event.currentTarget.value) })}
          onKeyUp={(event) => setCapacity({ chute: Number(event.currentTarget.value) })}
        />
      </label>
      </div>
      {movedOff.length ? (
        <p>
          <span className="figure moved">{movedOff.length}</span>
          {" "}moved off the week:{" "}
          {movedOff.map((id, index) => (
            <span key={`${id}-${riseKey}`}>
              {index ? ", " : null}
              <span className={stepping ? "lot-step figure miss" : "figure miss"} style={stepping ? { animationDelay: `${Math.min(index, 6) * 30}ms` } : undefined}>{id}</span>
            </span>
          ))}
        </p>
      ) : null}
      {plan ? (
        plan.unmet_clinical.length ? (
          <p>
            <span className="miss">Unmet</span>{" "}
            {plan.unmet_clinical.map((id, index) => {
              const step = stepping && changed.has(id);
              return (
                <span key={`${id}-${riseKey}`}>
                  {index ? ", " : null}
                  <span className={step ? "lot-step figure miss" : "figure miss"} style={step ? { animationDelay: `${Math.min(index, 6) * 30}ms` } : undefined}>{id}</span>
                </span>
              );
            })}
          </p>
        ) : (
          <p>Every review trigger has a slot.</p>
        )
      ) : null}
      {plan ? (
        <>
          <h2 className="subhead">Whole week</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Cohort</th>
                  <th scope="col">Package</th>
                  <th scope="col">Yard</th>
                  <th scope="col">Pen</th>
                </tr>
              </thead>
              <tbody>
                {assignmentRows.length ? assignmentRows.map((row, index) => {
                  const step = stepping && changed.has(row.cohortId);
                  return (
                    <tr
                      key={row.cohortId}
                      data-live={step ? "true" : undefined}
                      style={step ? ({ "--step": `${Math.min(index, 6) * 30}ms` } as CSSProperties) : undefined}
                    >
                      <td>
                        <span className={step ? "lot-step figure" : "figure"} style={step ? { animationDelay: `${Math.min(index, 6) * 30}ms` } : undefined}>{row.cohortId}</span>
                      </td>
                      <td className="figure">{row.packageName}</td>
                      <td className="figure">{row.yard || "—"}</td>
                      <td className="pen-mark"><InkIcon name="pen" />{row.pen || "—"}</td>
                    </tr>
                  );
                }) : (
                  <tr>
                    <td colSpan={4}>No assignments were returned.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {plan.usage.length ? <div className="capacity">
          <div className="tracks" aria-hidden="true"><span /><span className="note">Staff</span><span className="note">Vet</span><span className="note">Chute</span></div>
          {plan.usage.filter((row) => row.day_index < 3).map((row) => {
            const staffShare = Math.min(100, (row.staff_hours / Math.max(row.staff_capacity, 0.1)) * 100);
            const vet = Math.min(100, (row.vet_slots / Math.max(row.vet_capacity, 1)) * 100);
            const chute = Math.min(100, (row.chute_head / Math.max(row.chute_capacity, 1)) * 100);
            return (
              <div className="tracks" key={`${row.yard_id}-${row.day_index}`}>
                <span className="note">{row.yard_id} d{row.day_index + 1}</span>
                <div className="track" data-tight={staffShare > 85 ? "true" : "false"} role="img" aria-label={`Staff ${compact(row.staff_hours, 1)} of ${row.staff_capacity} hours`}><i style={{ width: `${staffShare}%` }} /></div>
                <div className="track" data-tight={row.vet_slots >= row.vet_capacity && row.vet_capacity > 0 ? "true" : "false"} role="img" aria-label={`Vet ${row.vet_slots} of ${row.vet_capacity} slots`}><i style={{ width: `${vet}%` }} /></div>
                <div className="track" data-tight={chute > 85 ? "true" : "false"} role="img" aria-label={`Chute ${row.chute_head} of ${row.chute_capacity} head`}><i style={{ width: `${chute}%` }} /></div>
              </div>
            );
          })}
          </div> : null}
        </>
      ) : null}
    </div>
  );
}
