import apiClient, { getWithRetry } from "./client";
import { Anomaly, AnomalyCreatePayload, AnomalyUpdatePayload } from "../types/domain";
import { ApiResponse, PaginatedResponse } from "../types/api";

export interface AnomalyQueryParams {
  metric?: string;
  severity?: string;
  page?: number;
  page_size?: number;
}

// ==============================================================================
// API Functions
// ==============================================================================

/**
 * Fetch list of anomaly records with optional filters.
 */
export async function fetchAnomalies(
  params?: AnomalyQueryParams
): Promise<PaginatedResponse<Anomaly>> {
  return getWithRetry<PaginatedResponse<Anomaly>>("/api/v1/anomaly/", { params });
}

/**
 * Register a new anomaly record from client-side / AI pipeline result.
 */
export async function createAnomaly(
  payload: AnomalyCreatePayload
): Promise<Anomaly> {
  const res = await apiClient.post<ApiResponse<Anomaly>>("/api/v1/anomaly/", payload);
  if (res.data.success && res.data.data) {
    return res.data.data;
  }
  throw new Error(res.data.error?.message || "Failed to create anomaly");
}

/**
 * Acknowledge or update an existing anomaly incident status.
 */
export async function acknowledgeAnomaly(
  anomalyId: string,
  payload: AnomalyUpdatePayload
): Promise<Anomaly> {
  const res = await apiClient.put<ApiResponse<Anomaly>>(
    `/api/v1/anomaly/${anomalyId}`,
    payload
  );
  if (res.data.success && res.data.data) {
    return res.data.data;
  }
  throw new Error(res.data.error?.message || "Failed to acknowledge anomaly");
}

