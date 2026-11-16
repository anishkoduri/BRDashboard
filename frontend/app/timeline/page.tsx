"use client";

import { useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useWorkspace } from "@/components/workspace";

const START = new Date("2026-02-02T00:00:00");

function dateFromOffset(offset: number) {
  const next = new Date(START);
  next.setDate(START.getDate() + offset);
  return next.toISOString().slice(0, 10);
}

export default function TimelinePage() {
  const { snap, link, error, setClock, addObservation } = useWorkspace();
  const [offset, setOffset] = useState(44);
  const [cohortId, setCohortId] = useState("");
  const [count, setCount] = useState(1);
  if (!snap) {
    return (
      <div className="screen">
        <h1 className="page-title">What the clock can see</h1>
        {link === "failed" ? (
          <p role="alert" className="alert">{error ? `The snapshot is unavailable. ${error}` : "The snapshot is unavailable."}</p>
        ) : (
          <p className="wait" role="status">Loading the clock.</p>
        )}
      </div>
    );
  }
  const cohort = snap.cohorts.find((row) => row.cohort_id === cohortId) ?? snap.cohorts[0];
  const chart = [
    { name: "Recorded", value: cohort?.observed_first ?? 0 },
    { name: "Projected remaining", value: cohort?.expected_remaining ?? 0 },
  ];
  return (
    <div className="screen">
      <h1 className="page-title">What the clock can see</h1>
      <p className="note">{snap.since_yesterday}</p>
      <label className="field crew">
        <span className="note">Assessment date {dateFromOffset(offset)}</span>
        <input type="range" min={0} max={70} value={offset} aria-label="Assessment date" onChange={(event) => setOffset(Number(event.target.value))} onPointerUp={() => setClock(dateFromOffset(offset))} />
      </label>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chart}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Line dataKey="value" stroke="var(--color-ink)" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <form className="split" onSubmit={(event) => { event.preventDefault(); if (cohort) addObservation({ cohort_id: cohort.cohort_id, day: Math.min(cohort.day_on_feed, 45), detected: count, note: "Added from the clock" }); }}>
        <label className="field">
          <span className="note">Cohort</span>
          <select aria-label="Cohort for a new count" value={cohort?.cohort_id} onChange={(event) => setCohortId(event.target.value)}>
            {snap.cohorts.slice(0, 40).map((row) => <option key={row.cohort_id}>{row.cohort_id}</option>)}
          </select>
        </label>
        <label className="field">
          <span className="note">New first treatments</span>
          <input type="number" min={0} max={20} value={count} aria-label="New first treatments" onChange={(event) => setCount(Number(event.target.value))} />
        </label>
        <button className="key" type="submit">Record through today</button>
      </form>
      {cohort ? <p className="note">{cohort.cohort_id} is on day {cohort.day_on_feed}. Recorded {cohort.observed_first}. Remaining projection {cohort.expected_remaining.toFixed(1)}. Deaths observed {cohort.deaths_observed}. There is no mortality forecast.</p> : null}
    </div>
  );
}
