/**
 * useDebounce — Debounce a rapidly-changing value
 *
 * Returns the debounced value which only updates after `delay` ms of
 * inactivity. Ideal for search inputs and slider-driven API calls.
 *
 * @example
 *   const debouncedSearch = useDebounce(searchTerm, 400);
 *   useEffect(() => { if (debouncedSearch) fetchResults(debouncedSearch); }, [debouncedSearch]);
 */
import { useState, useEffect } from "react";

export function useDebounce<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
