import { getWithRetry, postWithRetry } from "./client";

export interface ReportSummaryMetrics {
  total_anomalies: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  peak_score: number;
  total_alerts: number;
  resolved_alerts: number;
  sla_violations: number;
  system_health_avg: number;
  lowest_health_sector: string | null;
  lowest_health_score: number | null;
  forecast_mae: number | null;
  forecast_rmse: number | null;
  forecast_trend: string | null;
}

export interface ReportResponse {
  id: string;
  title: string;
  report_type: "DAILY" | "WEEKLY";
  start_date: string;
  end_date: string;
  status: "GENERATING" | "READY" | "FAILED";
  summary: string | null; // JSON string representing ReportSummaryMetrics
  pdf_path: string | null;
  csv_path: string | null;
  created_at: string;
}

export async function getReports(limit = 50): Promise<ReportResponse[]> {
  return getWithRetry<ReportResponse[]>(`/api/v1/reports?limit=${limit}`);
}

export async function generateReport(payload: {
  report_type: "DAILY" | "WEEKLY";
  start_date: string;
  end_date: string;
}): Promise<ReportResponse> {
  return postWithRetry<ReportResponse>("/api/v1/reports/generate", payload);
}

export function getReportDownloadUrl(reportId: string, format: "pdf" | "csv"): string {
  // Returns absolute path for download link routing
  return `/api/v1/reports/${reportId}/download/${format}`;
}
