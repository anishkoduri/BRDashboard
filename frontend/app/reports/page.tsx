"use client";

import { useState } from "react";
import { WorkMark } from "@/components/WorkMark";
import { useWorkspace } from "@/components/workspace";

export default function ReportsPage() {
  const { snap, link, error, refresh } = useWorkspace();
  const [html, setHtml] = useState("");
  const [preparing, setPreparing] = useState(false);
  const [reportError, setReportError] = useState("");

  async function prepare() {
    setPreparing(true);
    setReportError("");
    try {
      const response = await fetch("/api/reports/generate", { method: "POST" });
      const body = await response.text();
      if (!response.ok) throw new Error(body || response.statusText);
      setHtml(body);
    } catch (reason) {
      setReportError(reason instanceof Error ? reason.message : "The summary did not generate.");
    } finally {
      setPreparing(false);
    }
  }

  const sentence = snap?.plan?.binding?.sentence?.trim() ?? "";
  const planMessage = snap?.plan?.message?.trim() ?? "";
  const hero = sentence || planMessage || "Prepare the summary after the week exists.";

  return (
    <div className="screen">
      <article className="focus-plate summary-plate">
        {!snap ? (
          link === "failed" ? (
            <>
              <p role="alert" className="alert">{error ? `The snapshot is unavailable. ${error}` : "The snapshot is unavailable."}</p>
              <button className="key secondary" type="button" onClick={() => refresh()}>Retry</button>
            </>
          ) : (
            <WorkMark label="Loading the snapshot." kind="sheet" />
          )
        ) : (
          <h1 className={sentence ? "sentence miss" : "sentence"}>{hero}</h1>
        )}
      </article>
      <button className="key" type="button" onClick={() => { void prepare(); }} disabled={!snap || preparing}>
        Prepare summary
      </button>
      {preparing ? <WorkMark label="Preparing the summary." kind="sheet" /> : null}
      {reportError ? <p role="alert" className="alert">{reportError}</p> : null}
      {html ? (
        <>
          <h2 className="subhead">Generated summary</h2>
          <iframe className="report-frame" title="Generated decision summary" sandbox="" srcDoc={html} data-rise="true" />
        </>
      ) : snap ? (
        <p className="note">The summary appears here after you prepare it.</p>
      ) : null}
      {snap ? <p className="note">{snap.meta.disclaimer} Clock {snap.clock}. Mode {snap.meta.data_mode}.</p> : null}
    </div>
  );
}
