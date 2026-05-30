import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { fetchHealth, fetchVersion } from "../api/diagnostics";
import { latencyStore } from "../api/client";

// ==============================================================================
// Types
// ==============================================================================
export interface ApiStatus {
  connected: boolean;
  latencyMs: number;
  version: string | null;
  environment: string | null;
  lastChecked: Date | null;
  checking: boolean;
}

interface ApiStatusContextValue extends ApiStatus {
  /** Manually trigger a health re-check outside of the polling cycle */
  refresh: () => Promise<void>;
}

// ==============================================================================
// Context
// ==============================================================================
const ApiStatusContext = createContext<ApiStatusContextValue>({
  connected: false,
  latencyMs: 0,
  version: null,
  environment: null,
  lastChecked: null,
  checking: true,
  refresh: async () => {},
});

const POLL_INTERVAL_MS = 15_000;

// ==============================================================================
// Provider
// ==============================================================================
export const ApiStatusProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [status, setStatus] = useState<ApiStatus>({
    connected: false,
    latencyMs: 0,
    version: null,
    environment: null,
    lastChecked: null,
    checking: true,
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const check = useCallback(async () => {
    setStatus((prev) => ({ ...prev, checking: true }));
    try {
      // Fire health + version concurrently for efficiency
      const [health, ver] = await Promise.all([fetchHealth(), fetchVersion()]);

      setStatus({
        connected: health.status === "healthy",
        latencyMs: latencyStore.latencyMs,
        version: ver.version,
        environment: health.environment,
        lastChecked: new Date(),
        checking: false,
      });
    } catch {
      setStatus((prev) => ({
        ...prev,
        connected: false,
        latencyMs: 0,
        checking: false,
        lastChecked: new Date(),
      }));
    }
  }, []);

  // Initial check + polling every 15 s
  useEffect(() => {
    check();
    intervalRef.current = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [check]);

  return (
    <ApiStatusContext.Provider value={{ ...status, refresh: check }}>
      {children}
    </ApiStatusContext.Provider>
  );
};

// ==============================================================================
// Hook
// ==============================================================================
export function useApiStatusContext(): ApiStatusContextValue {
  return useContext(ApiStatusContext);
}
