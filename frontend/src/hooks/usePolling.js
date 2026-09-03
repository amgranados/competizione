import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Generic polling hook.
 *
 * Invokes `fetcher` on mount and then every `intervalMs` ms. Exposes
 * `{ data, error, loading, refresh }`. `refresh()` forces an immediate
 * extra fetch (used by pages after a local action so the user does not
 * have to wait for the next tick — see quickstart.md § Frontend patterns).
 */
export function usePolling(fetcher, intervalMs = 10000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const runOnce = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      if (cancelled) return;
      await runOnce();
    };

    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs, runOnce]);

  return { data, error, loading, refresh: runOnce };
}
