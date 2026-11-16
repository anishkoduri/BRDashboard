"use client";

import { useState } from "react";
import { useWorkspace } from "@/components/workspace";

type Report = { ok: boolean; errors: { row: number; column: string; message: string }[]; preview: Record<string, string>[]; row_count: number };

export default function DataPage() {
  const { snap, refresh, link, error } = useWorkspace();
  const [report, setReport] = useState<Report | null>(null);
  const [message, setMessage] = useState("");

  async function validate(file: File) {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch("/api/data/validate", { method: "POST", body });
    const payload = await response.json();
    setReport(payload);
    setMessage(payload.ok ? `Valid, ${payload.row_count} lots. Commit to make this the file the planner reads. The demo files stay on disk.` : "Import failed. Working data was not replaced.");
  }

  const failed = link === "failed" && !snap;

  return (
    <div className="screen">
      <h1 className="page-title">Where the numbers came from</h1>
      {failed ? <p role="alert" className="alert">{error ? `The snapshot is unavailable. ${error}` : "The snapshot is unavailable."}</p> : null}
      <p>Mode: <strong className="display">{snap?.meta.data_mode ?? "not loaded"}</strong>. Seed {snap?.meta.seed ?? "—"}. {snap?.meta.disclaimer}</p>
      <p className="note">A committed file replaces the lots Generate today&apos;s plan reads. A failed file leaves the working set in place.</p>
      <p><a className="text-link" href="/api/template">Download a cohort template</a></p>
      <label className="field crew">
        <span className="note">CSV or XLSX</span>
        <input type="file" accept=".csv,.xlsx" aria-label="Cohort file" onChange={(event) => { const file = event.target.files?.[0]; if (file) validate(file); }} />
      </label>
      {message ? <p role={report && !report.ok ? "alert" : "status"} className={report && !report.ok ? "alert" : undefined}>{message}</p> : null}
      {report?.errors?.length ? (
        <ul>{report.errors.slice(0, 12).map((item) => <li key={`${item.row}-${item.column}`}>{`Row ${item.row}, ${item.column}: ${item.message}`}</li>)}</ul>
      ) : null}
      <div className="button-row">
        {report?.ok ? <button className="key" type="button" onClick={async () => { await fetch("/api/data/import", { method: "POST" }); setMessage("Imported. Morning and Generate today's plan now read these lots."); await refresh(); }}>Commit import</button> : null}
        <button className={report?.ok ? "key secondary" : "key"} type="button" onClick={async () => { await fetch("/api/data/demo", { method: "POST" }); setMessage("Demonstration data reloaded."); await refresh(); }}>Load demonstration data</button>
      </div>
    </div>
  );
}
