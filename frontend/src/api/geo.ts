import { getWithRetry } from "./client";

// ==============================================================================
// Response Types (mirroring backend Pydantic schemas)
// ==============================================================================

export interface GeoAnomalyPoint {
  id: string;
  lat: number;
  lng: number;
  severity: "CRITICAL" | "WARNING" | "INFO";
  category: "POWER" | "TRAFFIC" | "WATER" | "INTERNET" | "PUBLIC_INFRASTRUCTURE";
  score: number;
  metric_name: string;
  description: string;
  timestamp: string;
  district: string;
  acknowledged: boolean;
}

export interface GeoRegionStatus {
  region_id: string;
  name: string;
  centroid_lat: number;
  centroid_lng: number;
  health_score: number;
  risk_level: "NOMINAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  anomaly_count: number;
  critical_count: number;
  dominant_category: string | null;
  polygon: number[][];
}

export interface GeoHeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;
}

export interface GeoMapResponse {
  anomaly_points: GeoAnomalyPoint[];
  regions: GeoRegionStatus[];
  heatmap_points: GeoHeatmapPoint[];
  total_anomalies: number;
  critical_count: number;
  most_affected_region: string | null;
  last_updated: string;
}

export interface GeoAnomalyQueryParams {
  severity?: string;
  category?: string;
  district?: string;
  limit?: number;
}

// ==============================================================================
// API Functions
// ==============================================================================

/**
 * Fetch the complete geospatial map payload.
 */
export async function fetchGeoMap(): Promise<GeoMapResponse> {
  return getWithRetry<GeoMapResponse>("/api/v1/geo/map");
}

/**
 * Fetch per-region infrastructure health status with polygon boundaries.
 */
export async function fetchGeoRegions(): Promise<GeoRegionStatus[]> {
  return getWithRetry<GeoRegionStatus[]>("/api/v1/geo/regions");
}

/**
 * Fetch filtered geolocated anomaly points.
 */
export async function fetchGeoAnomalyPoints(
  params?: GeoAnomalyQueryParams
): Promise<GeoAnomalyPoint[]> {
  return getWithRetry<GeoAnomalyPoint[]>("/api/v1/geo/anomaly-points", { params });
}

/**
 * Fetch heatmap intensity grid points.
 */
export async function fetchGeoHeatmap(): Promise<GeoHeatmapPoint[]> {
  return getWithRetry<GeoHeatmapPoint[]>("/api/v1/geo/heatmap");
}
