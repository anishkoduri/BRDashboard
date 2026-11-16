"use client";

import { useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useWorkspace } from "@/components/workspace";

export default function ScenariosPage() {
  const { snap, link, error, setAssumptions, loadSensitivity, sensitivity, loadCompare } = useWorkspace();
  const [loss, setLoss] = useState(snap?.assumptions.inclusive_loss_per_first_treatment ?? 151.18);
  const [effect, setEffect] = useState(snap?.assumptions.effectiveness ?? 0.5);
  if (!snap) {
    return (
      <div className="screen">
        <h1 className="page-title">Assumptions you can move</h1>
        {link === "failed" ? (
          <p role="alert" className="alert">{error ? `The snapshot is unavailable. ${error}` : "The snapshot is unavailable."}</p>
        ) : (
          <p className="wait" role="status">Loading assumptions.</p>
        )}
      </div>
    );
  }
  return (
    <div className="screen">
      <h1 className="page-title">Assumptions you can move</h1>
      <p className="note">Effectiveness changes the hypothetical column only. It does not authorize a drug and it does not rewrite the schedule.</p>
      <div className="split">
        <label className="field">
          <span className="note">Inclusive loss per first treatment, USD ({loss.toFixed(0)})</span>
          <input type="range" min={80} max={250} value={loss} aria-label="Inclusive loss" onChange={(event) => setLoss(Number(event.target.value))} onPointerUp={() => setAssumptions({ inclusive_loss_per_first_treatment: loss })} />
        </label>
        <label className="field">
          <span className="note">Hypothetical effectiveness ({effect.toFixed(2)})</span>
          <input type="range" min={0} max={0.8} step={0.05} value={effect} aria-label="Hypothetical effectiveness" onChange={(event) => setEffect(Number(event.target.value))} onPointerUp={() => setAssumptions({ effectiveness: effect })} />
        </label>
      </div>
      <div className="button-row">
        <button className="key" type="button" onClick={() => loadCompare()}>Refresh the comparison</button>
        <button className="key secondary" type="button" onClick={() => loadSensitivity()}>Sample the knobs</button>
        <button className="key secondary" type="button" onClick={() => { setLoss(151.18); setEffect(0.5); setAssumptions({ inclusive_loss_per_first_treatment: 151.18, effectiveness: 0.5, labor_cost_per_hour: 18 }); }}>Reset defaults</button>
      </div>
      {sensitivity ? (
        <div>
          <div className="chart-frame tall">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sensitivity.points}>
                <XAxis dataKey="effectiveness" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="delta_vs_baseline" fill="var(--color-ink)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="note">Bars are projected cost differences for a hypothetical protocol, not confidence intervals. Positive means the protocol costs more under that assumption.</p>
        </div>
      ) : null}
    </div>
  );
}
