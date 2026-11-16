import type { Cohort } from "@/lib/types";

const NAME: Record<string, string> = {
  light_weight_per_100lb: "Arrival weight",
  extra_source: "Source",
  commingled: "Source",
  transport_per_4h_over_8: "Transport",
  fall_or_winter: "Season",
  dense_pen: "Pen space",
  bulls: "Sex",
  recorded_vaccination: "Vaccination record",
  scenario_yard_offset: "Yard shift",
};

function observed(cohort: Cohort, factor: string) {
  if (factor === "light_weight_per_100lb") return cohort.weight == null ? "Weight is missing" : `Observed ${cohort.weight} lb`;
  if (factor === "transport_per_4h_over_8") return cohort.transport == null ? "Transport is missing" : `Observed ${cohort.transport} h`;
  if (factor === "commingled" || factor === "extra_source") {
    return `Observed ${cohort.source_type}${cohort.sources == null ? "" : `, ${cohort.sources} sources`}`;
  }
  if (factor === "fall_or_winter") return `Observed season ${cohort.arrival_season || "missing"}`;
  if (factor === "dense_pen") return cohort.area_per_head == null ? "Pen area is missing" : `Observed ${cohort.area_per_head} area per head`;
  if (factor === "bulls") return `Observed sex ${cohort.sex_group}`;
  if (factor === "recorded_vaccination") return `Record ${cohort.vaccination_history}`;
  return "Assumed yard shift. Not an estimated yard effect.";
}

export function Drivers({ cohort }: { cohort: Cohort }) {
  const ranked = [...cohort.factors].sort((left, right) => Math.abs(right.log_odds) - Math.abs(left.log_odds));
  const driving = ranked.filter((item) => Math.abs(item.log_odds) > 0).slice(0, 3);
  const low = (cohort.band_low * 100).toFixed(1);
  const high = (cohort.band_high * 100).toFixed(1);
  return (
    <div className="drivers">
      <h2 className="subhead">Why this lot</h2>
      <p className="note">Observed first treatments {cohort.observed_first}. That count updated the rate. It is not a drug input.</p>
      {driving.length ? (
        <ul className="driver-list">
          {driving.map((item) => (
            <li key={item.factor}>
              <span>{NAME[item.factor] ?? item.factor}</span>
              <span className="note">{observed(cohort, item.factor)}</span>
              <span className="note">Assumed shift {item.log_odds}. {item.note}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="note">No assumed arrival shift is above zero.</p>
      )}
      <p className="note">Uncertainty: {cohort.band_label}, {low} to {high} first treatments per 100 head.</p>
    </div>
  );
}
