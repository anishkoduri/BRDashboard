"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { InkIcon, type InkName } from "./InkIcon";
import { WorkMark, workKind } from "./WorkMark";
import { WorkspaceProvider, useWorkspace } from "./workspace";

const ICONS: Record<string, InkName> = {
  Morning: "morning",
  Plan: "plan",
  Summary: "summary",
  Evidence: "evidence",
  Data: "data",
  Clock: "clock",
  Scenarios: "scenarios",
  Decisions: "decisions",
};

const MORNING = [
  ["/", "Morning"],
  ["/planner", "Plan"],
  ["/reports", "Summary"],
] as const;

const REST = [
  ["/evidence", "Evidence"],
  ["/data", "Data"],
  ["/timeline", "Clock"],
  ["/scenarios", "Scenarios"],
  ["/decisions", "Decisions"],
] as const;

function Item({ href, label, path }: { href: string; label: string; path: string }) {
  const active = path === href;
  return (
    <Link href={href} data-active={active ? "true" : "false"} aria-current={active ? "page" : undefined}>
      <InkIcon name={ICONS[label]} />
      {label}
    </Link>
  );
}

function Frame({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const { snap, link, busy, error, setRole } = useWorkspace();
  return (
    <>
      <header className="banner">
        <span>Demonstration data. Not Merck records. Not a diagnosis. Not a prescription.</span>
        <span className="figure">{snap ? `${snap.meta.model_version} · ${snap.meta.updated}` : link === "failed" ? "Not connected" : "Connecting"}</span>
      </header>
      <div className="app-shell">
        <nav className="nav" aria-label="Sections">
          <p className="brand">BRD</p>
          <div className="nav-main">
            {MORNING.map(([href, label]) => <Item key={href} href={href} label={label} path={path} />)}
          </div>
          <div className="nav-rest">
            {REST.map(([href, label]) => <Item key={href} href={href} label={label} path={path} />)}
          </div>
          <label className="field" htmlFor="role-lens">
            <span className="note">Role lens</span>
            <select id="role-lens" name="role" value={snap?.meta.role || "manager"} onChange={(event) => setRole(event.target.value)} aria-label="Role lens">
              <option value="manager">Manager</option>
              <option value="rider">Pen rider</option>
              <option value="veterinarian">Veterinarian</option>
            </select>
          </label>
        </nav>
        <main className="main">
          {busy ? <WorkMark label={busy} kind={workKind(busy)} /> : null}
          {error && !(link === "failed" && !snap) ? <p role="alert" className="alert">{error}</p> : null}
          {children}
        </main>
      </div>
    </>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <Frame>{children}</Frame>
    </WorkspaceProvider>
  );
}
