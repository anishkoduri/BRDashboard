"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Drivers } from "@/components/Drivers";
import { Horizon } from "@/components/Horizon";
import { InkIcon } from "@/components/InkIcon";
import { useWorkspace } from "@/components/workspace";
import { WorkMark } from "@/components/WorkMark";
import { windowSentence } from "@/lib/horizon";
import { compact, money } from "@/lib/utils";

export default function CommandPage() {
  const { snap, link, error, yard, setYard, solve, busy, refresh } = useWorkspace();
  const [selected, setSelected] = useState<string | null>(null);
  const seen = useRef<string | null>(null);
  const active = useMemo(() => {
    const all = snap?.cohorts.filter((row) => row.active) ?? [];
    return yard === "all" ? all : all.filter((row) => row.yard_id === yard);
  }, [snap, yard]);
  const obligations = active.filter((row) => row.clinical_obligation);
  const focus = (selected ? obligations.find((row) => row.cohort_id === selected) : undefined) ?? obligations[0] ?? active[0] ?? null;
  const focusId = focus?.cohort_id ?? "";
  const arrive = seen.current !== null && focusId !== "" && seen.current !== focusId;

  useEffect(() => {
    if (focusId) seen.current = focusId;
  }, [focusId]);

  if (!snap) {
    return (
      <div className="screen">
        {link === "failed" ? (
          <>
            <p role="alert" className="alert">{error ? `The snapshot is unavailable. ${error}` : "The snapshot is unavailable."}</p>
            <button className="key secondary" type="button" onClick={() => refresh()}>Retry</button>
          </>
        ) : (
          <WorkMark label="Loading the four yards." kind="yards" />
        )}
        <button className="key" type="button" disabled>Generate today's plan</button>
      </div>
    );
  }

  const thin = Boolean(focus && (focus.missing.length > 0 || focus.insufficient));
  const busiest = Math.max(
    1,
    ...snap.yards.map((yardItem) => snap.cohorts.filter((row) => row.active && row.yard_id === yardItem.yard_id && row.clinical_obligation).length),
  );
  const horizon = focus ? windowSentence(focus.day_on_feed) : null;
  return (
    <div className="screen morning">
      <article key={focus?.cohort_id ?? "empty"} className="focus-plate morning-hero" data-rise={arrive ? "true" : "false"}>
        {focus ? (
          <>
            <p className="kicker"><InkIcon name="pen" />{snap.yards.find((item) => item.yard_id === focus.yard_id)?.name ?? focus.yard_id} · pen {focus.pen_id}</p>
            <h1 className="hero" aria-live="polite">{focus.cohort_id}</h1>
            <p className="reason">{focus.priority_reason}</p>
            {horizon ? <Horizon day={horizon.day} actionDay={horizon.actionDay} detail={horizon.detail} /> : null}
            {thin ? <p className="thin">Thin file{focus.missing.length ? `. ${focus.missing.join(", ")}` : "."}</p> : null}
          </>
        ) : (
          <h1 className="sentence">No lot is on feed.</h1>
        )}
        <p className="note">All four yards</p>
        <div className="pair">
          <div>
            <span className="note">Observed</span>
            <b className="figure">{snap.metrics.observed_first}</b>
          </div>
          <div>
            <span className="note">Estimated</span>
            <b className="figure">{compact(snap.metrics.projected_remaining, 0)}</b>
          </div>
        </div>
      </article>
      <div className="actions morning-actions">
        <button className="key" type="button" onClick={() => solve()} disabled={!snap || Boolean(busy)}>Generate today's plan</button>
        {focus ? (
          <Link className="key secondary" href={`/cohorts/${focus.cohort_id}`}>Open this lot</Link>
        ) : (
          <button className="key secondary" type="button" disabled>Open this lot</button>
        )}
      </div>
      <div className="morning-rest">
      <div className="yard-row" role="group" aria-label="Yards">
        {snap.yards.map((item) => {
          const count = snap.cohorts.filter((row) => row.active && row.yard_id === item.yard_id && row.clinical_obligation).length;
          const pressed = yard === item.yard_id;
          return (
            <button key={item.yard_id} type="button" className="yard" aria-pressed={pressed} onClick={() => setYard(item.yard_id)}>
              <span className="yard-top">
                <InkIcon name="pen" />
                <span className="yard-name">{item.name}</span>
              </span>
              <span className="figure">{count}</span>
              <span className="ink-bar" aria-hidden="true"><i style={{ width: `${Math.max(12, (count / busiest) * 100)}%` }} /></span>
              <span className="sr-only">lots that need a person</span>
            </button>
          );
        })}
      </div>
      <section className="lot-section">
        {focus ? <Drivers cohort={focus} /> : null}
        <h2 className="subhead">Lots that need a person</h2>
        {obligations.length ? (
          <ul className="lot-list">
            {obligations.map((row) => (
              <li key={row.cohort_id}>
                <button
                  type="button"
                  className="lot-row"
                  aria-pressed={focus?.cohort_id === row.cohort_id}
                  onClick={() => setSelected(row.cohort_id)}
                >
                  <span className="ink-dot" aria-hidden="true" />
                  <span className="figure">{row.cohort_id}</span>
                  <span className="pen-mark"><InkIcon name="pen" />{row.pen_id}</span>
                  <span className="lot-figs">
                    <span><span className="note">Observed</span> <span className="figure">{row.observed_first}</span></span>
                    <span><span className="note">Estimated</span> <span className="figure">{compact(row.expected_remaining, 1)}</span></span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>No lot needs a person.</p>
        )}
      </section>
      </div>
      <section className="yard-ops">
        <h2 className="subhead">How the yards differ</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Yard</th>
                <th scope="col">Observed first treatments per 100</th>
                <th scope="col">Day-0 pen-check hours / staff hours</th>
                <th scope="col">Current-approach cost</th>
              </tr>
            </thead>
            <tbody>
              {snap.yards.map((item) => (
                <tr key={item.yard_id}>
                  <td>{item.name}</td>
                  <td className="figure">{item.observed_per_100 == null ? "—" : compact(item.observed_per_100, 2)}</td>
                  <td className="figure">{compact(item.baseline_staff_day0, 1)} / {compact(item.staff_hours_per_day, 1)}</td>
                  <td className="figure">{item.current_approach_cost == null ? "—" : money(item.current_approach_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note">Observed counts are pulls already recorded. Cost is the current pen-check approach under the visible loss assumption. It is not money saved.</p>
      </section>
    </div>
  );
}
