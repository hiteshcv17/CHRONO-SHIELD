import { getWithRetry } from "./client";

export interface NodeHealthReport {
  name: string;
  node_type: string;
  uptime: string;
  cpu_load: number;
  memory_saturation: number;
  health_score: number;
  failure_probability: number;
  remaining_useful_life_days: number;
  risk_tier: string;
  explanation: string;
}

export interface InfrastructureHealthResponse {
  overall_health_score: number;
  active_risks_count: number;
  reports: NodeHealthReport[];
}

export interface ComponentHealthReport {
  category: string;
  health_score: number;
  risk_level: string;
  confidence_score: number;
  metrics: Record<string, any>;
  penalties_breakdown: {
    anomaly_penalty: number;
    social_penalty: number;
    physical_penalty: number;
  };
  explanation: string;
}

export interface CityHealthResponse {
  success: boolean;
  reports: ComponentHealthReport[];
}

export async function getInfrastructureHealth(): Promise<InfrastructureHealthResponse> {
  return getWithRetry<InfrastructureHealthResponse>("/api/v1/health/diagnose");
}

export async function getCityInfrastructureHealth(): Promise<CityHealthResponse> {
  return getWithRetry<CityHealthResponse>("/api/v1/health/components");
}

