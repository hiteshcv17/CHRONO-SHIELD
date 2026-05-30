import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchAnomalies, acknowledgeAnomaly, AnomalyQueryParams } from "../api/anomalies";
import { Anomaly } from "../types/domain";
import { ApiError } from "../api/client";

// ==============================================================================
// Fallback placeholder data shown when backend is unreachable
// ==============================================================================
const PLACEHOLDER_ANOMALIES: Anomaly[] = [
  {
    id: "ANM-201",
    timestamp: new Date(Date.now() - 14 * 60000).toISOString(),
    metric_name: "CPU Core Load",
    severity: "CRITICAL",
    score: 0.94,
    description: "Spike exceeded weekly baseline limit. High CPU lock contention detected on fastapi-01.",
    acknowledged: false,
  },
  {
    id: "ANM-202",
    timestamp: new Date(Date.now() - 40 * 60000).toISOString(),
    metric_name: "Database Latency",
    severity: "WARNING",
    score: 0.81,
    description: "SQL connection pool starvation triggered. Outlier transaction latency of 1420ms.",
    acknowledged: false,
  },
  {
    id: "ANM-203",
    timestamp: new Date(Date.now() - 75 * 60000).toISOString(),
    metric_name: "Disk Write Spikes",
    severity: "INFO",
    score: 0.68,
    description: "Temporary read-write saturation during database compaction execution.",
    acknowledged: true,
  },
  {
    id: "ANM-204",
    timestamp: new Date(Date.now() - 90 * 60000).toISOString(),
    metric_name: "Memory Heap Bounds",
    severity: "WARNING",
    score: 0.88,
    description: "Sliding sequence memory delta surpassed weekly rolling deviation bounds.",
    acknowledged: false,
  },
  {
    id: "ANM-205",
    timestamp: new Date(Date.now() - 168 * 60000).toISOString(),
    metric_name: "API Core Gateway Errors",
    severity: "CRITICAL",
    score: 0.96,
    description: "Clustered gateway node restarted. Raised connection errors for 45s.",
    acknowledged: true,
  },
];

interface UseAnomaliesResult {
  data: Anomaly[];
  loading: boolean;
  error: ApiError | null;
  isPlaceholder: boolean;
  refetch: () => void;
  acknowledge: (id: string) => Promise<void>;
}

export function useAnomalies(params?: AnomalyQueryParams): UseAnomaliesResult {
  const [data, setData] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [isPlaceholder, setIsPlaceholder] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Stable serialised key — avoids JSON.stringify inside useCallback deps
  const paramsKey = useMemo(() => JSON.stringify(params ?? {}), [params]);

  const load = useCallback(async () => {
    // Cancel any in-flight request
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);
    setIsPlaceholder(false);

    try {
      const result = await fetchAnomalies(params);
      const items = result && Array.isArray(result)
        ? result
        : (result && Array.isArray((result as any).items) ? (result as any).items : []);
      setData(items);
    } catch (err) {
      const apiErr = err as ApiError;
      // If network error, silently fall back to placeholder data
      if (apiErr.code === "NETWORK_ERROR" || apiErr.code === "TIMEOUT") {
        setData(PLACEHOLDER_ANOMALIES);
        setIsPlaceholder(true);
        setError(null); // Don't show error — just show placeholder with banner
      } else {
        setError(apiErr);
        setData([]);
      }
    } finally {
      setLoading(false);
    }
  }, [paramsKey]);

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, [load]);

  const acknowledge = useCallback(async (id: string) => {
    try {
      const updated = await acknowledgeAnomaly(id, { acknowledged: true });
      setData((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a))
      );
    } catch {
      // If backend is down, update local state optimistically
      setData((prev) =>
        prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a))
      );
    }
  }, []);

  return { data, loading, error, isPlaceholder, refetch: load, acknowledge };
}
