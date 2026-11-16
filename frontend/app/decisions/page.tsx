"use client";

import { useWorkspace } from "@/components/workspace";
import { money } from "@/lib/utils";

function extraChecksLeaveDisease(
  comparison: { monitoring_changes_disease?: boolean; economics?: { monitoring_changes_disease?: boolean } } | null,
  economics: { monitoring_changes_disease?: boolean } | undefined,
) {
  return comparison?.monitoring_changes_disease === false
    || comparison?.economics?.monitoring_changes_disease === false
    || economics?.monitoring_changes_disease === false;
}

export default function DecisionsPage() {
  const { comparison, loadCompare, busy, snap } = useWorkspace();
  const checksLeaveDisease = extraChecksLeaveDisease(comparison, snap?.plan?.economics);
  return (
    <div className="screen">
      <h1 className="page-title">Current, proposed, and hypothetical</h1>
      <p className="note">The schedule does not reduce modeled disease. The hypothetical stays unexecuted.</p>
      {checksLeaveDisease ? <p>Extra pen checks do not change the disease total.</p> : null}
      <button className="key" type="button" onClick={() => loadCompare()} disabled={Boolean(busy)}>Compare with the baseline</button>
      {comparison ? (
        <>
          <div className="totals">
            <Total title="Current" cost={comparison.baseline.total_cost} burden={comparison.baseline.modeled_burden} labor={comparison.baseline.labor_hours} exposed={comparison.baseline.antimicrobial_exposed_head} note="Usual pen checks. No group medication." />
            <Total title="Proposed" cost={comparison.optimized.total_cost} burden={comparison.optimized.modeled_burden} labor={comparison.optimized.labor_hours} exposed={comparison.optimized.antimicrobial_exposed_head} note={managerLabel(comparison.optimized.clinical_label)} />
            <Total title="Hypothetical" quiet cost={comparison.alternative.total_cost} burden={comparison.alternative.modeled_burden} labor={comparison.alternative.labor_hours} exposed={comparison.alternative.antimicrobial_exposed_head} note={comparison.alternative.label} />
          </div>
          <p className="note">{comparison.wording}</p>
          <p className="note">Inclusive loss ${comparison.assumptions_visible.inclusive_loss.toFixed(2)} (Rojas historical figure). Effectiveness assumption {comparison.assumptions_visible.effectiveness}. Labor ${comparison.assumptions_visible.labor}/hour. Group-protocol price ${snap?.assumptions.metaphylaxis_cost_per_head.toFixed(2)} per head, also from Rojas. That price changes the hypothetical total. It does not change which package is scheduled.</p>
        </>
      ) : (
        <p className="note">The three totals appear after the comparison.</p>
      )}
    </div>
  );
}

function managerLabel(label: string) {
  if (label === "infeasible") return "The week does not fit.";
  if (label === "unmet_care") return "Some reviews do not fit.";
  if (label === "optimal") return "Every listed review has a slot.";
  if (label === "feasible_not_proved") return "Feasible, not proved.";
  return label.replaceAll("_", " ");
}

function Total({ title, cost, burden, labor, exposed, note, quiet }: { title: string; cost: number; burden: number; labor: number; exposed: number; note: string; quiet?: boolean }) {
  return (
    <div className={quiet ? "hypothetical" : undefined}>
      <h2>{title}</h2>
      <p className="figure total">{money(cost)}</p>
      <p className="note">Projected total under the assumptions. Not money already saved.</p>
      <p className="figure">{exposed}</p>
      <p className="note">Courses. One course is one animal on a group protocol. Review slots are not doses. Current and proposed stay at 0 unless a package administers a drug.</p>
      <p className="note">Modeled burden {burden.toFixed(1)} first treatments. Labor {typeof labor === "number" ? labor.toFixed(1) : labor}.</p>
      <p className="note">{note}</p>
    </div>
  );
}
