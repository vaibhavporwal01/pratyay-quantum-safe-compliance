"use client";

import { useCallback, useEffect, useState } from "react";
import { api, failureMessage } from "./api/client";

type State<T> = { key: string | null; data?: T; error?: string };

/**
 * GET a path and track loading, data and error. Pass null to wait (for example until a param
 * is known). `reload` fetches again.
 */
export function useApi<T>(path: string | null) {
  const [tick, setTick] = useState(0);
  const key = path === null ? null : `${path}#${tick}`;
  const [state, setState] = useState<State<T>>({ key: null });

  useEffect(() => {
    if (path === null || key === null) return;
    let live = true;
    api
      .get<T>(path)
      .then((data) => live && setState({ key, data }))
      .catch((e) => live && setState({ key, error: failureMessage(e) }));
    return () => {
      live = false;
    };
  }, [path, key]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  const current = state.key === key;
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : undefined,
    loading: key !== null && !current,
    reload,
  };
}
