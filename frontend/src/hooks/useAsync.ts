/**
 * useAsync — Generic async data-fetching hook
 *
 * Manages loading / data / error state for any async operation.
 * Automatically aborts on dependency change and on unmount.
 *
 * @example
 *   const { data, loading, error, refetch } = useAsync(
 *     () => fetchAnomalies({ page: 1 }),
 *     [page]
 *   );
 */
import { useState, useEffect, useRef, useCallback, DependencyList } from "react";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  /** Imperatively re-trigger the async function (increments a counter that is a dep) */
  refetch: () => void;
}

export function useAsync<T>(
  fn: () => Promise<T>,
  deps: DependencyList = []
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [rev, setRev] = useState(0);

  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fnRef
      .current()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [...deps, rev]);

  const refetch = useCallback(() => setRev((r) => r + 1), []);

  return { data, loading, error, refetch };
}
