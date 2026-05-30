import { getWithRetry } from "./client";

export interface ForecastRecord {
  timestamp: string;
  actual: number | null;
  forecast: number;
  upper_bound: number;
  lower_bound: number;
  is_forecast: boolean;
}

export interface PredictedAnomaly {
  timestamp: string;
  predicted_value: number;
  severity: string;
  description: string;
}

export interface ExplainableForecasting {
  trend_direction: string;
  trend_summary: string;
  peak_day_of_week: string;
  peak_hour_of_day: number;
  analysis_notes: string[];
}

export interface ForecastResponse {
  success: boolean;
  metric_name: string;
  records: ForecastRecord[];
  predicted_anomalies: PredictedAnomaly[];
  explanation: ExplainableForecasting;
}

export async function getTelemetryForecast(
  metricId: string,
  horizonHours: number,
  city: string
): Promise<ForecastResponse> {
  return getWithRetry<ForecastResponse>(
    `/api/v1/forecasting/predict?metric_id=${encodeURIComponent(
      metricId
    )}&horizon_hours=${horizonHours}&city=${encodeURIComponent(city)}`
  );
}
