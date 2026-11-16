"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { Snapshot } from "@/lib/types";

type Compare = {
  wording: string;
  plan_status: string;
  baseline: { total_cost: number; labor_cost: number; modeled_burden: number; labor_hours: number; antimicrobial_exposed_head: number };
  optimized: { total_cost: number; labor_cost: number; modeled_burden: number; labor_hours: number; antimicrobial_exposed_head: number; clinical_label: string };
  alternative: { total_cost: number; labor_cost: number; labor_hours: number; modeled_burden: number; antimicrobial_exposed_head: number; label: string };
  assumptions_visible: { inclusive_loss: number; effectiveness: number; labor: number };
  monitoring_changes_disease?: boolean;
  economics?: { monitoring_changes_disease?: boolean };
};

type LinkState = "connecting" | "ready" | "failed";

type WorkspaceValue = {
  snap: Snapshot | null;
  link: LinkState;
  busy: string;
  error: string;
  briefing: string[];
  answer: string;
  comparison: Compare | null;
  sensitivity: { points: { loss_scale: number; effectiveness: number; delta_vs_baseline: number }[] } | null;
  yard: string;
  setYard: (yard: string) => void;
  refresh: () => Promise<void>;
  solve: () => Promise<void>;
  setClock: (clock: string) => Promise<void>;
  setRole: (role: string) => Promise<void>;
  setCapacity: (patch: { staff?: number; chute?: number; vet?: number }) => Promise<void>;
  setAssumptions: (patch: Record<string, number>) => Promise<void>;
  ask: (question: string) => Promise<void>;
  loadBriefing: () => Promise<void>;
  loadCompare: () => Promise<void>;
  loadSensitivity: () => Promise<void>;
  addObservation: (body: { cohort_id: string; day: number; detected: number; note: string }) => Promise<void>;
  setReview: (body: { cohort_id: string; status: string }) => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

const SNAPSHOT_TIMEOUT_MS = 8000;

async function send(path: string, init?: RequestInit) {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

function snapshotFailure(reason: unknown) {
  if (reason instanceof Error && reason.name === "AbortError") {
    return "The yards did not answer within 8 seconds.";
  }
  if (reason instanceof Error && reason.message) return reason.message;
  return "The yards did not answer.";
}

async function fetchSnapshot() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SNAPSHOT_TIMEOUT_MS);
  try {
    const response = await fetch("/api/snapshot", { signal: controller.signal, headers: { Accept: "application/json" } });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || response.statusText);
    }
    return response.json() as Promise<Snapshot>;
  } finally {
    clearTimeout(timer);
  }
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [link, setLink] = useState<LinkState>("connecting");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const refreshTicket = useRef(0);
  const [briefing, setBriefing] = useState<string[]>([]);
  const [answer, setAnswer] = useState("");
  const [comparison, setComparison] = useState<Compare | null>(null);
  const [sensitivity, setSensitivity] = useState<WorkspaceValue["sensitivity"]>(null);
  const [yard, setYard] = useState("all");

  const refresh = useCallback(async () => {
    const ticket = refreshTicket.current + 1;
    refreshTicket.current = ticket;
    try {
      const next = await fetchSnapshot();
      if (ticket !== refreshTicket.current) return;
      setSnap(next);
      setError("");
      setLink("ready");
    } catch (reason) {
      if (ticket !== refreshTicket.current) return;
      const message = snapshotFailure(reason);
      setLink("failed");
      setError(message);
      throw new Error(message);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [refresh]);

  const run = useCallback(async (label: string, task: () => Promise<void>) => {
    setBusy(label);
    setError("");
    try {
      await task();
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Request failed");
    } finally {
      setBusy("");
    }
  }, [refresh]);

  const value = useMemo<WorkspaceValue>(() => ({
    snap, link, busy, error, briefing, answer, comparison, sensitivity, yard, setYard, refresh,
    solve: () => run("Scheduling the week", async () => { await send("/api/optimization/solve", { method: "POST" }); }),
    setClock: (clock) => run("Moving the clock", async () => { await send("/api/clock", { method: "POST", body: JSON.stringify({ clock }) }); }),
    setRole: (role) => run("Switching role", async () => { await send("/api/role", { method: "POST", body: JSON.stringify({ role }) }); }),
    setCapacity: (patch) => run("Re-planning capacity", async () => {
      await send("/api/scenarios/capacity", { method: "POST", body: JSON.stringify(patch) });
      await send("/api/optimization/solve", { method: "POST" });
    }),
    setAssumptions: (patch) => run("Recalculating assumptions", async () => {
      await send("/api/scenarios/assumptions", { method: "POST", body: JSON.stringify(patch) });
    }),
    ask: async (question) => {
      setBusy("Looking up the answer");
      try {
        const result = await send("/api/ask", { method: "POST", body: JSON.stringify({ question }) });
        setAnswer(result.answer);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Ask failed");
      } finally {
        setBusy("");
      }
    },
    loadBriefing: async () => {
      setBusy("Writing the briefing");
      try {
        const result = await send("/api/briefing", { method: "POST" });
        setBriefing(result.lines);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Request failed");
      } finally {
        setBusy("");
      }
    },
    loadCompare: async () => {
      setBusy("Comparing plans");
      try {
        setComparison(await send("/api/decisions/compare", { method: "POST" }));
        await refresh();
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Compare failed");
      } finally {
        setBusy("");
      }
    },
    loadSensitivity: async () => {
      setBusy("Sampling assumptions");
      try {
        setSensitivity(await send("/api/sensitivity/run", { method: "POST" }));
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Request failed");
      } finally {
        setBusy("");
      }
    },
    addObservation: (body) => run("Recording the count", async () => {
      await send("/api/observations", { method: "POST", body: JSON.stringify({ ...body, actor: snap?.meta.role || "manager" }) });
    }),
    setReview: (body) => run("Recording review status", async () => {
      await send("/api/reviews", { method: "POST", body: JSON.stringify(body) });
    }),
  }), [snap, link, busy, error, briefing, answer, comparison, sensitivity, yard, refresh, run]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("Workspace missing");
  return value;
}
