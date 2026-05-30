import { getWithRetry } from "./client";

// ==============================================================================
// Response Types
// ==============================================================================

export interface SeverityDistribution {
  CRITICAL: number;
  WARNING: number;
  INFO: number;
}

export interface CategoryDistribution {
  POWER: number;
  TRAFFIC: number;
  WATER: number;
  INTERNET: number;
  PUBLIC_INFRASTRUCTURE: number;
}

export interface TimelineBucket {
  bucket_index: number;
  timestamp_start: string;
  timestamp_end: string;
  label: string;
  anomaly_count: number;
  critical_count: number;
  severity_distribution: SeverityDistribution;
  category_distribution: CategoryDistribution;
  peak_score: number;
  health_delta: number;
  event_ids: string[];
}

export interface IncidentRecord {
  id: string;
  timestamp: string;
  metric_name: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  category: "POWER" | "TRAFFIC" | "WATER" | "INTERNET" | "PUBLIC_INFRASTRUCTURE";
  score: number;
  description: string;
  district: string;
  acknowledged: boolean;
  duration_minutes: number;
  cascaded: boolean;
  related_ids: string[];
  root_cause_hint: string | null;
  resolution_hint: string | null;
  bucket_index: number;
}

export interface ReplayTimelineResponse {
  buckets: TimelineBucket[];
  incidents: IncidentRecord[];
  time_range_hours: number;
  bucket_duration_minutes: number;
  total_incidents: number;
  total_critical: number;
  peak_bucket_index: number;
  timeline_start: string;
  timeline_end: string;
}

export interface ReplayFrame {
  bucket: TimelineBucket;
  active_incidents: IncidentRecord[];
  cumulative_critical: number;
  cumulative_total: number;
  system_health: number;
  dominant_category: string | null;
  alert_level: "NOMINAL" | "ELEVATED" | "HIGH" | "CRISIS";
}

export interface IncidentComparisonResponse {
  incident_a: IncidentRecord;
  incident_b: IncidentRecord;
  similarity_score: number;
  shared_categories: string[];
  shared_districts: string[];
  time_delta_minutes: number;
  likely_correlated: boolean;
  severity_diff: string;
  score_diff: number;
  combined_risk: "MODERATE" | "HIGH" | "EXTREME";
}

// ==============================================================================
// API Functions
// ==============================================================================

export async function fetchReplayTimeline(hours = 24): Promise<ReplayTimelineResponse> {
  return getWithRetry<ReplayTimelineResponse>(`/api/v1/replay/timeline?hours=${hours}`);
}

export async function fetchReplayFrame(bucketIndex: number, hours = 24): Promise<ReplayFrame> {
  return getWithRetry<ReplayFrame>(`/api/v1/replay/frame/${bucketIndex}?hours=${hours}`);
}

export async function fetchIncidentComparison(
  idA: string,
  idB: string,
  hours = 24
): Promise<IncidentComparisonResponse> {
  return getWithRetry<IncidentComparisonResponse>(
    `/api/v1/replay/compare?id_a=${idA}&id_b=${idB}&hours=${hours}`
  );
}
