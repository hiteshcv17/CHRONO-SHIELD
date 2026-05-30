import axios, {
  AxiosInstance,
  AxiosError,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from "axios";
import { v4 as uuidv4 } from "uuid";

// ==============================================================================
// Typed API Error
// ==============================================================================
export interface ApiError {
  code: string;
  message: string;
  trace_id?: string;
  status: number;
}

// ==============================================================================
// Latency Store — shared mutable reference (not reactive, updated by interceptor)
// ==============================================================================
export const latencyStore = {
  latencyMs: 0,
  lastChecked: null as Date | null,
};

// ==============================================================================
// Axios Client Factory
// ==============================================================================
const BASE_URL = import.meta.env.VITE_API_URL ?? "";

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 500;

const sleep = (ms: number) => new Promise((res) => setTimeout(res, ms));

let activeAccessToken: string | null = null;

export function setAccessToken(token: string | null) {
  activeAccessToken = token;
}

export function getAccessToken(): string | null {
  return activeAccessToken;
}

function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL: BASE_URL,
    timeout: 10_000,
    withCredentials: true,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  });

  // --------------------------------------------------------------------------
  // REQUEST interceptor — inject Correlation ID + timestamp + auth token
  // --------------------------------------------------------------------------
  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const correlationId = uuidv4();
    config.headers["X-Correlation-ID"] = correlationId;
    if (activeAccessToken) {
      config.headers["Authorization"] = `Bearer ${activeAccessToken}`;
    }
    // Store start time on config so the response interceptor can calculate latency
    (config as any)._requestStartedAt = Date.now();
    return config;
  });

  // --------------------------------------------------------------------------
  // RESPONSE interceptor — measure latency + normalize errors + refresh token
  // --------------------------------------------------------------------------
  client.interceptors.response.use(
    (response) => {
      const started = (response.config as any)._requestStartedAt;
      if (started) {
        latencyStore.latencyMs = Date.now() - started;
        latencyStore.lastChecked = new Date();
      }
      return response;
    },
    async (error: AxiosError) => {
      const originalRequest = error.config;

      // Handle silent token refresh on 401 Unauthorized
      if (
        error.response?.status === 401 &&
        originalRequest &&
        !(originalRequest as any)._retry &&
        originalRequest.url &&
        !originalRequest.url.includes("/auth/login") &&
        !originalRequest.url.includes("/auth/refresh")
      ) {
        (originalRequest as any)._retry = true;
        try {
          const refreshRes = await client.post<{ access_token: string }>("/api/v1/auth/refresh");
          const token = refreshRes.data.access_token;
          setAccessToken(token);

          // Update header and retry original request
          originalRequest.headers["Authorization"] = `Bearer ${token}`;
          return client(originalRequest);
        } catch (refreshErr) {
          setAccessToken(null);
          if (typeof window !== "undefined") {
            window.dispatchEvent(new Event("auth-session-expired"));
          }
        }
      }

      const apiErr: ApiError = {
        code: "UNKNOWN_ERROR",
        message: "An unexpected error occurred.",
        status: error.response?.status ?? 0,
      };

      if (error.response?.data && typeof error.response.data === "object") {
        const data = error.response.data as any;
        if (data.error) {
          apiErr.code = data.error.code ?? apiErr.code;
          apiErr.message = data.error.message ?? apiErr.message;
          apiErr.trace_id = data.error.trace_id;
        } else if (data.detail) {
          apiErr.message = data.detail;
          apiErr.code = "VALIDATION_ERROR";
        }
      } else if (error.code === "ECONNABORTED") {
        apiErr.code = "TIMEOUT";
        apiErr.message = "Request timed out. The backend may be unavailable.";
      } else if (!error.response) {
        apiErr.code = "NETWORK_ERROR";
        apiErr.message = "Cannot reach the backend. Check your connection.";
      }

      return Promise.reject(apiErr);
    }
  );

  return client;
}

const apiClient = createClient();

// ==============================================================================
// Retry-capable GET wrapper (exponential back-off, idempotent only)
// ==============================================================================
export async function getWithRetry<T>(
  url: string,
  config?: AxiosRequestConfig,
  retries = MAX_RETRIES
): Promise<T> {
  let attempt = 0;
  while (attempt <= retries) {
    try {
      const res = await apiClient.get<T>(url, config);
      return res.data;
    } catch (err) {
      const isNetworkOrTimeout =
        (err as ApiError).code === "NETWORK_ERROR" ||
        (err as ApiError).code === "TIMEOUT";

      if (isNetworkOrTimeout && attempt < retries) {
        await sleep(RETRY_DELAY_MS * Math.pow(2, attempt)); // exponential back-off
        attempt++;
      } else {
        throw err;
      }
    }
  }
  throw new Error("Max retries exceeded");
}

// ==============================================================================
// PUT wrapper (non-retried — state-mutating, caller decides on retry)
// ==============================================================================
export async function putWithRetry<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  const res = await apiClient.put<T>(url, data, config);
  return res.data;
}

// ==============================================================================
// POST wrapper (non-retried — state-mutating, caller decides on retry)
// ==============================================================================
export async function postWithRetry<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  const res = await apiClient.post<T>(url, data, config);
  return res.data;
}

export default apiClient;

