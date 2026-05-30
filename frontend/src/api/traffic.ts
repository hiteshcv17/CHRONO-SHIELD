import { getWithRetry } from "./client";

// ==============================================================================
// Response Interfaces (mirroring backend Pydantic models)
// ==============================================================================

export interface TrafficRecord {
  timestamp: string;
  corridor_id: string;
  bbox: string | null;
  flow_speed_kmh: number | null;
  free_flow_speed_kmh: number | null;
  jam_factor: number | null;
  congestion_level: string | null;
  incident_count: number | null;
  travel_time_seconds: number | null;
  confidence_score: number | null;
}

export interface CurrentTrafficResponse {
  success: boolean;
  fetched_at: string;
  records: TrafficRecord[];
}

export interface TrafficTrendsResponse {
  corridor: string;
  records: TrafficRecord[];
}

// ==============================================================================
// API Client Functions
// ==============================================================================

/**
 * Fetch the latest current traffic flow metrics for all configured highway corridors.
 */
export async function getCurrentTraffic(): Promise<CurrentTrafficResponse> {
  return getWithRetry<CurrentTrafficResponse>("/api/v1/traffic/current");
}

/**
 * Fetch the historical telemetry trends for a specific highway corridor.
 */
export async function getTrafficTrends(corridorId: string): Promise<TrafficTrendsResponse> {
  return getWithRetry<TrafficTrendsResponse>(`/api/v1/traffic/trends?corridor=${encodeURIComponent(corridorId)}`);
}
