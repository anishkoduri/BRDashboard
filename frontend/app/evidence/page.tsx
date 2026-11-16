"use client";

import { useEffect, useState } from "react";

type Entry = {
  id: string;
  source: string;
  file: string;
  used_for: string;
  claims: string[];
  not_used_as: string;
  doi?: string;
  kind?: string;
  label?: string;
  group?: string;
  status?: string;
};

const KIND_KEYS = ["kind", "label", "group", "status"] as const;

function rowKind(entry: Entry) {
  for (const key of KIND_KEYS) {
    const value = entry[key];
    if (typeof value === "string" && /observed|estimated|assumed/i.test(value)) return value;
  }
  return "";
}

export default function EvidencePage() {
  const [ledger, setLedger] = useState<Entry[] | null>(null);
  const [failed, setFailed] = useState("");

  useEffect(() => {
    fetch("/api/evidence")
      .then(async (response) => {
        if (!response.ok) throw new Error("The ledger did not load.");
        return response.json();
      })
      .then((payload) => setLedger(Array.isArray(payload?.ledger) ? payload.ledger : []))
      .catch((reason) => setFailed(reason instanceof Error ? reason.message : "The ledger did not load."));
  }, []);

  const kinds = ledger?.map(rowKind) ?? [];
  const labeled = kinds.some(Boolean);

  return (
    <div className="screen">
      <h1 className="page-title">What is known</h1>
      {ledger && !labeled ? (
        <p className="legend">
          <strong>Observed</strong> is a recorded count. <strong>Estimated</strong> is a projection. <strong>Assumed</strong> is a research input. The rows below are the ledger as stored.
        </p>
      ) : null}
      {failed ? <p role="alert" className="alert">{failed}</p> : null}
      {ledger === null && !failed ? <p className="wait" role="status">Opening the ledger.</p> : null}
      {ledger && ledger.length === 0 && !failed ? <p>The ledger is empty.</p> : null}
      {ledger?.length ? (
        <ul className="ledger">
          {ledger.map((entry, index) => (
            <li key={entry.id}>
              {kinds[index] ? <p className="note">{kinds[index]}</p> : null}
              <h2 className="subhead">{entry.source}</h2>
              <p className="note">{entry.file}{entry.doi ? ` · ${entry.doi}` : ""}</p>
              <p>{entry.used_for}</p>
              <ul>{entry.claims.map((claim) => <li key={claim}>{claim}</li>)}</ul>
              <p className="note">Not used as: {entry.not_used_as}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
