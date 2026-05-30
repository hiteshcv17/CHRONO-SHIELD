import { getWithRetry, putWithRetry, postWithRetry } from "./client";

export interface NotificationChannelConfigResponse {
  id: string;
  channel_type: "EMAIL" | "TELEGRAM" | "WEBHOOK";
  config: string; // JSON-serialized config
  enabled: boolean;
}

export interface NotificationDeliveryLogResponse {
  id: string;
  alert_id: string | null;
  channel: "EMAIL" | "TELEGRAM" | "WEBHOOK";
  recipient: string;
  title: string;
  message: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: "PENDING" | "SENT" | "FAILED";
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  timestamp: string;
  sent_at: string | null;
}

export async function getChannels(): Promise<NotificationChannelConfigResponse[]> {
  return getWithRetry<NotificationChannelConfigResponse[]>("/api/v1/notifications/channels");
}

export async function updateChannel(
  channelType: string,
  payload: { config?: string; enabled?: boolean }
): Promise<NotificationChannelConfigResponse> {
  return putWithRetry<NotificationChannelConfigResponse>(
    `/api/v1/notifications/channels/${channelType}`,
    payload
  );
}

export async function triggerTestDispatch(
  channelType: string,
  payload: { channel: string; recipient: string; message: string }
): Promise<NotificationDeliveryLogResponse> {
  return postWithRetry<NotificationDeliveryLogResponse>(
    `/api/v1/notifications/channels/${channelType}/test`,
    payload
  );
}

export async function getDeliveryLogs(filters?: {
  channel?: string;
  status?: string;
  alert_id?: string;
  limit?: number;
}): Promise<NotificationDeliveryLogResponse[]> {
  let query = "";
  const params: string[] = [];
  if (filters?.channel && filters.channel !== "ALL") {
    params.push(`channel=${filters.channel}`);
  }
  if (filters?.status && filters.status !== "ALL") {
    params.push(`status=${filters.status}`);
  }
  if (filters?.alert_id) {
    params.push(`alert_id=${filters.alert_id}`);
  }
  if (filters?.limit) {
    params.push(`limit=${filters.limit}`);
  }
  if (params.length > 0) {
    query = `?${params.join("&")}`;
  }
  return getWithRetry<NotificationDeliveryLogResponse[]>(`/api/v1/notifications/logs${query}`);
}
