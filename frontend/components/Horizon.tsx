export function Horizon({ day, actionDay, detail }: { day: number; actionDay: number | null; detail: string }) {
  const elapsed = Math.min(Math.max(day, 0), 45);
  return (
    <div className="horizon">
      <div className="horizon-track" role="img" aria-label={detail}>
        <i style={{ width: `${(elapsed / 45) * 100}%` }} />
        {actionDay != null ? <span className="horizon-mark" style={{ left: `${(actionDay / 45) * 100}%` }} /> : null}
      </div>
      <p className="note">{detail}</p>
    </div>
  );
}
