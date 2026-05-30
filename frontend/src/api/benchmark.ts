import { getWithRetry, postWithRetry } from "./client";

// ==============================================================================
// Response Types
// ==============================================================================

export interface ModelMetrics {
  model_name: string;
  dataset_name: string;
  metric_type: string;
  mae: number;
  rmse: number;
  mape: number;
  r2_score: number;
  training_time_ms: number;
  inference_time_ms: number;
  total_time_ms: number;
  n_train: number;
  n_test: number;
  horizon_steps: number;
  converged: boolean;
  error_message: string | null;
}

export interface ModelComparison {
  winner: string;
  loser: string;
  metric_name: string;
  winner_value: number;
  loser_value: number;
  improvement_pct: number;
  is_significant: boolean;
}

export interface BenchmarkRun {
  run_id: string;
  timestamp: string;
  models_evaluated: string[];
  datasets_evaluated: string[];
  results: ModelMetrics[];
  aggregate: Record<string, Record<string, number>>;
  comparisons: ModelComparison[];
  ranking_by_mae: string[];
  ranking_by_rmse: string[];
  ranking_by_mape: string[];
  ranking_by_speed: string[];
  overall_winner: string;
  overall_winner_reason: string;
  report_summary: string;
  recommendations: string[];
  total_benchmark_time_ms: number;
}

export interface DatasetPreview {
  metric_type: string;
  description: string;
  n_samples: number;
  train_size: number;
  test_size: number;
  seasonality_period: number;
  values: number[];
  train_values: number[];
  test_values: number[];
  stats: { mean: number; std: number; min: number; max: number };
}

export interface BenchmarkRequest {
  metric_types: string[];
  horizon_steps: number;
  n_samples: number;
  include_ets: boolean;
}

// ==============================================================================
// API Functions
// ==============================================================================

export async function runBenchmark(req: BenchmarkRequest): Promise<BenchmarkRun> {
  return postWithRetry<BenchmarkRun>("/api/v1/benchmark/run", req);
}

export async function runQuickBenchmark(
  metric_type = "power",
  n_samples = 120,
  horizon = 12
): Promise<BenchmarkRun> {
  return getWithRetry<BenchmarkRun>(
    `/api/v1/benchmark/quick?metric_type=${metric_type}&n_samples=${n_samples}&horizon=${horizon}`
  );
}

export async function fetchDatasetPreview(
  metric_type: string,
  n_samples = 200
): Promise<DatasetPreview> {
  return getWithRetry<DatasetPreview>(
    `/api/v1/benchmark/preview/${metric_type}?n_samples=${n_samples}`
  );
}

// ==============================================================================
// Colour palette (shared with component)
// ==============================================================================
export const MODEL_COLORS: Record<string, string> = {
  Prophet: "#a855f7",
  ARIMA:   "#00e5ff",
  ETS:     "#22c55e",
};

export const MODEL_ICONS: Record<string, string> = {
  Prophet: "🔮",
  ARIMA:   "📈",
  ETS:     "📊",
};

export const METRIC_LABELS: Record<string, string> = {
  mae:  "MAE",
  rmse: "RMSE",
  mape: "MAPE (%)",
  r2:   "R² Score",
};
