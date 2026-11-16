export type InkName =
  | "morning"
  | "plan"
  | "summary"
  | "evidence"
  | "data"
  | "clock"
  | "scenarios"
  | "decisions"
  | "pen";

export function InkIcon({ name }: { name: InkName }) {
  return (
    <svg className="ink-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      {mark(name)}
    </svg>
  );
}

function mark(name: InkName) {
  if (name === "morning") {
    return (
      <>
        <circle cx="8" cy="8" r="2.2" />
        <path d="M8 2.2v1.6M8 12.2v1.6M2.2 8h1.6M12.2 8h1.6M4 4l1.1 1.1M10.9 10.9 12 12M12 4l-1.1 1.1M5.1 10.9 4 12" />
      </>
    );
  }
  if (name === "plan") return <path d="M3 4h10M3 8h10M3 12h6" />;
  if (name === "summary") return <path d="M4 2.5h5.5L12 5v8.5H4zM9.5 2.5V5H12M6 8h4M6 10.5h4" />;
  if (name === "evidence") return <path d="M3 3.5h4.2c.8 0 1.5.4 1.8 1.1.3-.7 1-1.1 1.8-1.1H13V12h-2.2c-.8 0-1.5.3-1.8.9-.3-.6-1-1-1.8-1H3z" />;
  if (name === "data") return <path d="M3 4.5h10M3 8h10M3 11.5h10" />;
  if (name === "clock") return <><circle cx="8" cy="8" r="5" /><path d="M8 5.2V8l2 1.4" /></>;
  if (name === "scenarios") return <path d="M3 4.5h10M3 11.5h10M6 3.2v2.6M10 10.2v2.6" />;
  if (name === "decisions") return <path d="M8 2.5v11M3.5 5h3M9.5 5h3M4 8.5h2.5M9.5 8.5H12" />;
  return <path d="M5 2.5h4.2L11 4.2V13.5H5zM9.2 2.5V4.2H11" />;
}
