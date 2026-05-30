import { getWithRetry } from "./client";

export interface CorrelationMatrixResponse {
  success: boolean;
  variables: string[];
  matrix: number[][];
}

export interface GraphNode {
  id: string;
  label: string;
  group: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

export interface CorrelationGraphResponse {
  success: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface TimeOverlayResponse {
  success: boolean;
  timestamps: string[];
  series: Record<string, (number | null)[]>;
}

export interface ActivityIntensityResponse {
  success: boolean;
  days: string[];
  hours: number[];
  matrix: number[][];
}

export interface AnomalyConcentrationResponse {
  success: boolean;
  days: string[];
  hours: number[];
  matrix: number[][];
}

export interface SynchronizedAnomaly {
  id: string;
  timestamp: string;
  metrics: Record<string, number>;
  severity: string;
  description: string;
}

export interface SynchronizedAnomaliesResponse {
  success: boolean;
  anomalies: SynchronizedAnomaly[];
}

export interface LagCorrelation {
  metric_a: string;
  metric_b: string;
  lag_minutes: number;
  correlation: number;
  description: string;
}

export interface LagAnalysisResponse {
  success: boolean;
  relationships: LagCorrelation[];
}

export async function getCorrelationMatrix(city: string, windowDays?: number): Promise<CorrelationMatrixResponse> {
  const query = windowDays ? `&window_days=${windowDays}` : "";
  return getWithRetry<CorrelationMatrixResponse>(`/api/v1/correlation/matrix?city=${encodeURIComponent(city)}${query}`);
}

export async function getCorrelationGraph(city: string, threshold = 0.3, windowDays?: number): Promise<CorrelationGraphResponse> {
  const query = windowDays ? `&window_days=${windowDays}` : "";
  return getWithRetry<CorrelationGraphResponse>(`/api/v1/correlation/graph?city=${encodeURIComponent(city)}&threshold=${threshold}${query}`);
}

export async function getCorrelationOverlays(city: string, windowDays?: number): Promise<TimeOverlayResponse> {
  const query = windowDays ? `&window_days=${windowDays}` : "";
  return getWithRetry<TimeOverlayResponse>(`/api/v1/correlation/overlays?city=${encodeURIComponent(city)}${query}`);
}

export async function getActivityIntensity(city: string): Promise<ActivityIntensityResponse> {
  return getWithRetry<ActivityIntensityResponse>(`/api/v1/correlation/intensity?city=${encodeURIComponent(city)}`);
}

export async function getAnomalyConcentration(city: string): Promise<AnomalyConcentrationResponse> {
  return getWithRetry<AnomalyConcentrationResponse>(`/api/v1/correlation/concentration?city=${encodeURIComponent(city)}`);
}

export async function getSynchronizedAnomalies(city: string): Promise<SynchronizedAnomaliesResponse> {
  return getWithRetry<SynchronizedAnomaliesResponse>(`/api/v1/correlation/synchronized-anomalies?city=${encodeURIComponent(city)}`);
}

export async function getLagAnalysis(city: string): Promise<LagAnalysisResponse> {
  return getWithRetry<LagAnalysisResponse>(`/api/v1/correlation/lag-analysis?city=${encodeURIComponent(city)}`);
}
