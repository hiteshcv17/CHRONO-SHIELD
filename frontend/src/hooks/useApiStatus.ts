import { useApiStatusContext } from "../context/ApiStatusContext";

/**
 * Hook that exposes current backend connection state to any component.
 *
 * @example
 * const { connected, latencyMs, version } = useApiStatus();
 */
export function useApiStatus() {
  return useApiStatusContext();
}
