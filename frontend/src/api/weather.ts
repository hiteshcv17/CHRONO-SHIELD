import { getWithRetry } from "./client";

// ==============================================================================
// Response Interfaces (mirroring backend Pydantic models)
// ==============================================================================

export interface WeatherRecord {
  timestamp: string;
  location: string;
  latitude: number;
  longitude: number;
  temperature_c: number | null;
  humidity_pct: number | null;
  wind_speed_ms: number | null;
  precipitation_mm: number | null;
}

export interface CurrentWeatherResponse {
  success: boolean;
  fetched_at: string;
  records: WeatherRecord[];
}

export interface WeatherTrendsResponse {
  city: string;
  records: WeatherRecord[];
}

// ==============================================================================
// API Client Functions
// ==============================================================================

/**
 * Fetch the latest current atmospheric observations for all configured locations.
 */
export async function getCurrentWeather(): Promise<CurrentWeatherResponse> {
  return getWithRetry<CurrentWeatherResponse>("/api/v1/weather/current");
}

/**
 * Fetch the historical telemetry trends for a specific city.
 */
export async function getWeatherTrends(city: string): Promise<WeatherTrendsResponse> {
  return getWithRetry<WeatherTrendsResponse>(`/api/v1/weather/trends?city=${encodeURIComponent(city)}`);
}
