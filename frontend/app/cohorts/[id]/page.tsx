"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { InkIcon } from "@/components/InkIcon";
import { WorkMark } from "@/components/WorkMark";
import { useWorkspace } from "@/components/workspace";

export default function CohortPage() {
  const params = useParams<{ id: string }>();
  const { snap, link, error, refresh, setReview } = useWorkspace();
  const [explanation, setExplanation] = useState<{ why_prioritized: string; how_this_differs_from_baseline: string; missing: string[]; not_a_diagnosis: string; could_change_the_decision: string[] } | null>(null);
  const cohort = snap?.cohorts.find((row) => row.cohort_id === params.id);

  useEffect(() => {
    if (!params.id) return;
    fetch(`/api/cohorts/${params.id}`).then((response) => response.json()).then(setExplanation);
  }, [params.id, snap?.clock]);

  if (!snap) {
    if (link === "failed") {
      return (
        <div className="screen">
          <p role="alert" className="alert">{error ? `The snapshot is unavailable. ${error}` : "The snapshot is unavailable."}</p>
          <button className="key" type="button" onClick={() => refresh()}>Retry</button>
        </div>
      );
    }
    return <WorkMark label={`Opening ${params.id}.`} kind="file" />;
  }
  if (!cohort) return <p>That lot is not on feed at this clock.</p>;

  const unmet = snap.plan?.unmet_clinical.includes(cohort.cohort_id) ?? false;
  const status = unmet
    ? "This lot does not fit the week."
    : cohort.clinical_obligation
      ? "This lot needs a person today."
      : "Routine check.";
  const yardName = snap.yards.find((item) => item.yard_id === cohort.yard_id)?.name ?? cohort.yard_id;
  const missing = cohort.missing.length ? cohort.missing.join(", ") : "The file is complete enough to rank";

  return (
    <div className="screen">
      <article className="focus-plate">
        <p className="kicker"><InkIcon name="pen" />{yardName} · pen {cohort.pen_id} · day {cohort.day_on_feed}</p>
        <h1 className="hero">{cohort.cohort_id}</h1>
        <p className={unmet ? "rank miss" : "rank"}>{status}</p>
        {cohort.insufficient ? <p className="thin">This file is not enough for a confident recommendation.</p> : null}
        <dl className="honesty">
          <div>
            <dt>Observed</dt>
            <dd className="rank"><span className="figure">{cohort.observed_first}</span> of <span className="figure">{cohort.head}</span></dd>
          </div>
          <div>
            <dt>Estimated</dt>
            <dd className="rank">
              <span className="figure">{cohort.expected_remaining.toFixed(1)}</span>
              {cohort.distance_sentence?.trim() ? ` ${cohort.distance_sentence.trim()}` : null}
            </dd>
          </div>
          <div>
            <dt>Missing</dt>
            <dd className="rank">{missing}</dd>
          </div>
        </dl>
        <p className="note">{cohort.research_threshold_note}</p>
      </article>
      <section>
        <p>Status: {cohort.review.status.replaceAll("_", " ")}</p>
        {snap.meta.role === "veterinarian" ? (
          <button className="key" type="button" onClick={() => setReview({ cohort_id: cohort.cohort_id, status: "awaiting_veterinary_authorization" })}>Mark awaiting authorization</button>
        ) : (
          <p className="note">Switch the role lens to veterinarian to record a simulated status. That status is not a real approval.</p>
        )}
        {explanation?.not_a_diagnosis ? <p className="note">{explanation.not_a_diagnosis}</p> : null}
        {explanation?.could_change_the_decision?.length ? (
          <ul>{explanation.could_change_the_decision.map((line) => <li key={line}>{line}</li>)}</ul>
        ) : null}
      </section>
      <Link className="text-link" href="/planner">See the week.</Link>
    </div>
  );
}
