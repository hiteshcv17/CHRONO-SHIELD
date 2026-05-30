import { getWithRetry, postWithRetry } from "./client";

// ==============================================================================
// Response Types
// ==============================================================================

export interface ContributingFactor {
  factor_id: string;
  name: string;
  factor_type: "PRIMARY" | "AMPLIFIER" | "CORRELATE" | "ENVIRONMENTAL" | "TEMPORAL";
  description: string;
  confidence: number;
  weight: number;
  category: string;
  evidence: string[];
  metric_refs: string[];
}

export interface CorrelationLink {
  from_factor: string;
  to_factor: string;
  relationship: "CAUSED" | "AMPLIFIED" | "CORRELATED" | "PRECEDED" | "TRIGGERED";
  strength: number;
  lag_minutes: number;
}

export interface ReasoningStep {
  step_index: number;
  step_type: "OBSERVE" | "HYPOTHESIZE" | "CORRELATE" | "CONCLUDE" | "RECOMMEND";
  title: string;
  detail: string;
  confidence: number;
  supporting_factors: string[];
}

export interface AnomalyExplanation {
  anomaly_id: string;
  metric_name: string;
  severity: string;
  category: string;
  timestamp: string;
  district: string;
  score: number;
  headline: string;
  summary: string;
  causal_narrative: string;
  contributing_factors: ContributingFactor[];
  correlation_chain: CorrelationLink[];
  reasoning_steps: ReasoningStep[];
  overall_confidence: number;
  explanation_quality: "STRONG" | "MODERATE" | "SPECULATIVE";
  primary_cause: string;
  cascade_risk: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  impacted_systems: string[];
  recommended_actions: string[];
  ai_model_version: string;
  explanation_latency_ms: number;
}

export interface ExplainBatchResponse {
  explanations: AnomalyExplanation[];
  total_analyzed: number;
  high_confidence_count: number;
  cross_incident_patterns: string[];
  system_narrative: string;
}

export interface AnomalyExplainRequest {
  anomaly_id: string;
  metric_name: string;
  severity: string;
  category: string;
  score: number;
  timestamp: string;
  district: string;
  description?: string;
  related_ids?: string[];
}

// ==============================================================================
// API Functions
// ==============================================================================

export async function explainAnomaly(req: AnomalyExplainRequest): Promise<AnomalyExplanation> {
  return postWithRetry<AnomalyExplanation>("/api/v1/explain/anomaly", req);
}

export async function explainBatch(
  anomalies: AnomalyExplainRequest[]
): Promise<ExplainBatchResponse> {
  return postWithRetry<ExplainBatchResponse>("/api/v1/explain/batch", { anomalies });
}

export async function fetchExplainPreview(
  metric = "power_outage",
  severity = "CRITICAL",
  category = "POWER",
  score = 0.93,
  district = "East Industrial"
): Promise<AnomalyExplanation> {
  const params = new URLSearchParams({ metric, severity, category, score: String(score), district });
  return getWithRetry<AnomalyExplanation>(`/api/v1/explain/preview?${params}`);
}

// ==============================================================================
// Preset demo anomalies (from the replay dataset)
// ==============================================================================
export const DEMO_ANOMALIES: AnomalyExplainRequest[] = [
  { anomaly_id: "INC-005", metric_name: "power_outage",       severity: "CRITICAL", category: "POWER",                 score: 0.93, timestamp: "2026-05-28T02:15:00", district: "East Industrial", description: "Complete power outage — Industrial Block C, 4 facilities affected.", related_ids: ["INC-006"] },
  { anomaly_id: "INC-017", metric_name: "traffic_accident",   severity: "CRITICAL", category: "TRAFFIC",               score: 0.89, timestamp: "2026-05-28T08:00:00", district: "North District",  description: "Multi-vehicle collision — NH-8 northbound, lanes 1-3 blocked.",    related_ids: ["INC-018"] },
  { anomaly_id: "INC-029", metric_name: "internet_bandwidth", severity: "CRITICAL", category: "INTERNET",              score: 0.92, timestamp: "2026-05-28T13:40:00", district: "North District",  description: "Backbone saturation — CDN failover triggered, high packet loss.",  related_ids: ["INC-030"] },
  { anomaly_id: "INC-032", metric_name: "energy_demand",      severity: "CRITICAL", category: "POWER",                 score: 0.96, timestamp: "2026-05-28T14:14:00", district: "North District",  description: "Peak demand record — 4,820 MW, 12% above safety threshold.",      related_ids: ["INC-031"] },
  { anomaly_id: "INC-041", metric_name: "water_pressure",     severity: "CRITICAL", category: "WATER",                 score: 0.94, timestamp: "2026-05-28T18:45:00", district: "South Harbor",    description: "Critical pipe rupture — South Harbor Zone 6, 2000 residents affected.", related_ids: ["INC-042"] },
  { anomaly_id: "INC-002", metric_name: "grid_voltage",       severity: "WARNING",  category: "POWER",                 score: 0.61, timestamp: "2026-05-28T00:45:00", district: "North District",  description: "Voltage fluctuation detected during substation load balancing.", related_ids: [] },
  { anomaly_id: "INC-014", metric_name: "traffic_jam",        severity: "WARNING",  category: "TRAFFIC",               score: 0.72, timestamp: "2026-05-28T07:00:00", district: "Central Grid",    description: "Severe congestion at Central Business District crossroads.", related_ids: [] },
  { anomaly_id: "INC-034", metric_name: "water_pressure",     severity: "WARNING",  category: "WATER",                 score: 0.67, timestamp: "2026-05-28T15:00:00", district: "Central Grid",    description: "Pressure anomaly in main distribution trunk — possible pipe leak.", related_ids: [] },
  { anomaly_id: "INC-026", metric_name: "cpu_usage",          severity: "WARNING",  category: "INTERNET",              score: 0.77, timestamp: "2026-05-28T12:05:00", district: "Central Grid",    description: "API gateway CPU at 91% — lunchtime traffic spike.", related_ids: [] },
  { anomaly_id: "INC-022", metric_name: "infrastructure_defect", severity: "WARNING", category: "PUBLIC_INFRASTRUCTURE", score: 0.58, timestamp: "2026-05-28T10:20:00", district: "West Residential", description: "Pothole cluster reported — Sector 7B main road, 12 reports.", related_ids: [] },
];
