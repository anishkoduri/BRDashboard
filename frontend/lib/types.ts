export type Cohort = {
  cohort_id: string;
  yard_id: string;
  pen_id: string;
  arrival_date: string;
  sex_group: string;
  source_type: string;
  vaccination_history: string;
  arrival_season: string;
  head: number;
  weight: number | null;
  sources: number | null;
  transport: number | null;
  area_per_head: number | null;
  day_on_feed: number;
  past_window: boolean;
  active: boolean;
  observed_first: number;
  subsequent: number;
  deaths_observed: number;
  expected_remaining: number;
  expected_per_100: number;
  p_exceed_15: number;
  band_low: number;
  band_high: number;
  band_label: string;
  factors: { factor: string; log_odds: number; note: string; label: string }[];
  missing: string[];
  insufficient: boolean;
  clinical_obligation: boolean;
  incomplete_history: boolean;
  priority_reason: string;
  distance_to_trigger?: number | null;
  distance_sentence?: string;
  priority_score: number;
  completeness: number;
  versus_yard: number;
  yard_reference_per_100: number;
  review: { status: string; actor: string; note: string };
  respiratory_flags: number;
  research_threshold_note: string;
};

export type Plan = {
  solver_status: string;
  clinical_label: string;
  assignments: Record<string, string>;
  unmet_clinical: string[];
  usage: {
    yard_id: string;
    day_index: number;
    staff_hours: number;
    staff_capacity: number;
    vet_slots: number;
    vet_capacity: number;
    chute_head: number;
    chute_capacity: number;
  }[];
  shortages: { yard_id: string; resource: string; gap?: number; gap_hours?: number }[];
  message: string;
  solve_seconds: number;
  proved_optimal: boolean;
  binding?: {
    yard_id: string;
    day_index: number;
    resource: string;
    sentence: string;
  } | null;
  diff?: {
    cohort_id: string;
    before: string | null;
    after: string | null;
    entered_unmet: boolean;
    left_unmet: boolean;
  }[];
  economics?: {
    totals: Record<string, number>;
    monitoring_changes_disease?: boolean;
  };
};

export type Snapshot = {
  meta: {
    data_mode: string;
    model_version: string;
    seed: number;
    clock: string;
    role: string;
    disclaimer: string;
    tagline: string;
    updated: string;
  };
  clock: string;
  assumptions: {
    inclusive_loss_per_first_treatment: number;
    effectiveness: number;
    labor_cost_per_hour: number;
    metaphylaxis_cost_per_head: number;
  };
  multipliers: { staff: number; chute: number; vet: number };
  yards: {
    yard_id: string;
    name: string;
    region: string;
    staff_hours_per_day: number;
    chute_head_per_day: number;
    vet_slots_per_day: number;
    hospital_pens: number;
    active_cohorts: number;
    head: number;
    observed_first?: number;
    observed_per_100?: number;
    expected_remaining?: number;
    current_approach_cost?: number;
    staff_slack_hours: number;
    baseline_staff_day0: number;
  }[];
  cohorts: Cohort[];
  metrics: {
    head: number;
    cohorts: number;
    attention_cohorts: number;
    observed_first: number;
    projected_remaining: number;
    vet_queue: number;
    staff_available_today: number;
    baseline_staff_day0: number;
    deaths_observed: number;
  };
  plan: Plan | null;
  since_yesterday: string;
};
