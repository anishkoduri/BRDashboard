export type WorkKind = "yards" | "week" | "file" | "sheet";

const YARDS = ["PN", "HS", "WK", "PC"] as const;
const DAYS = ["d1", "d2", "d3", "d4", "d5", "d6", "d7"] as const;

export function workKind(label: string): WorkKind {
  if (label === "Loading the four yards.") return "yards";
  if (label === "Scheduling the week" || label === "Re-planning capacity" || label === "Loading the week.") return "week";
  if (label === "Preparing the summary." || label === "Loading the snapshot.") return "sheet";
  return "file";
}

export function WorkMark({ label, kind }: { label: string; kind: WorkKind }) {
  return (
    <div className="work" data-kind={kind}>
      <p className="wait" role="status">{label}</p>
      {kind === "yards" ? (
        <ol className="work-ticks" aria-hidden="true">
          {YARDS.map((id, index) => (
            <li key={id} style={{ animationDelay: `${index * 140}ms` }}>{id}</li>
          ))}
        </ol>
      ) : null}
      {kind === "week" ? (
        <ol className="work-ticks" aria-hidden="true">
          {DAYS.map((id, index) => (
            <li key={id} style={{ animationDelay: `${index * 70}ms` }}>{id}</li>
          ))}
        </ol>
      ) : null}
      {kind === "file" ? <span className="work-file" aria-hidden="true" /> : null}
      {kind === "sheet" ? <span className="work-sheet" aria-hidden="true" /> : null}
    </div>
  );
}
