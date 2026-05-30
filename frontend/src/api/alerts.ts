import apiClient, { getWithRetry } from "./client";
import { PrioritizedAlert, AnomalyCreatePayload } from "../types/domain";
import { ApiResponse, PaginatedResponse } from "../types/api";

/**
 * Fetch the prioritized alerts queue with pagination and filters.
 */
export async function getAlertsQueue(
  statusFilter?: string,
  severityFilter?: string,
  page = 1,
  pageSize = 50
): Promise<PaginatedResponse<PrioritizedAlert>> {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (statusFilter && statusFilter !== "ALL") {
    params.status_filter = statusFilter;
  }
  if (severityFilter && severityFilter !== "ALL") {
    params.severity = severityFilter;
  }
  return getWithRetry<PaginatedResponse<PrioritizedAlert>>("/api/v1/alerts/queue", { params });
}

/**
 * Acknowledge an active or escalated alert, initiating a cooldown block.
 */
export async function acknowledgePrioritizedAlert(alertId: string): Promise<PrioritizedAlert> {
  const res = await apiClient.put<ApiResponse<PrioritizedAlert>>(`/api/v1/alerts/${alertId}/acknowledge`);
  if (res.data.success && res.data.data) {
    return res.data.data;
  }
  throw new Error(res.data.error?.message || "Failed to acknowledge prioritized alert");
}

/**
 * Resolve an active or escalated alert, closing the incident block.
 */
export async function resolvePrioritizedAlert(alertId: string): Promise<PrioritizedAlert> {
  const res = await apiClient.put<ApiResponse<PrioritizedAlert>>(`/api/v1/alerts/${alertId}/resolve`);
  if (res.data.success && res.data.data) {
    return res.data.data;
  }
  throw new Error(res.data.error?.message || "Failed to resolve prioritized alert");
}

/**
 * Manually inject an anomaly to run through the prioritizer queue.
 */
export async function injectPrioritizedIncident(
  payload: AnomalyCreatePayload
): Promise<PrioritizedAlert> {
  const res = await apiClient.post<ApiResponse<PrioritizedAlert>>("/api/v1/alerts/inject", payload);
  if (res.data.success && res.data.data) {
    return res.data.data;
  }
  throw new Error(res.data.error?.message || "Failed to inject prioritized alert");
}

