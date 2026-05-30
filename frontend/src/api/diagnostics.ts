import { getWithRetry } from "./client";

// ==============================================================================
// Response Types (mirroring backend Pydantic schemas)
// ==============================================================================
export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
}

export interface DependencyStatus {
  name: string;
  connected: boolean;
  latency_ms: number;
}

export interface StatusResponse {
  status: string;
  dependencies: DependencyStatus[];
  system_metrics: Record<string, unknown>;
}

export interface VersionResponse {
  service: string;
  version: string;
  api_v1_prefix: string;
}

// ==============================================================================
// API Functions
// ==============================================================================

/**
 * Ping the backend health gateway.
 * Used for continuous connection monitoring (15-second polling).
 */
export async function fetchHealth(): Promise<HealthResponse> {
  return getWithRetry<HealthResponse>("/health");
}

/**
 * Fetch full status report including dependency pings.
 */
export async function fetchStatus(): Promise<StatusResponse> {
  return getWithRetry<StatusResponse>("/status");
}

/**
 * Retrieve API version metadata.
 */
export async function fetchVersion(): Promise<VersionResponse> {
  return getWithRetry<VersionResponse>("/version");
}
