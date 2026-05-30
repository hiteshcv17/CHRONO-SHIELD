/**
 * useInterval — Typed, safe setInterval with automatic cleanup
 *
 * @param callback  Function to call on each tick
 * @param delay     Interval in milliseconds (pass null to pause)
 * @param immediate If true, fires callback immediately on mount
 *
 * @example
 *   useInterval(() => refetchMetrics(), 5000, true);
 */
import { useEffect, useRef } from "react";

export function useInterval(
  callback: () => void,
  delay: number | null,
  immediate = false
): void {
  const savedCallback = useRef<() => void>(callback);

  // Keep the ref current after every render so the callback always sees
  // the latest closure without restarting the interval.
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;

    if (immediate) {
      savedCallback.current();
    }

    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay, immediate]);
}
