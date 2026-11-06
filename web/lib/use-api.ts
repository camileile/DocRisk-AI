"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, getToken } from "./api";
import { getDemoRole } from "./offline-demo";

/* Cada resposta pertence ao recurso e à sessão que iniciaram a requisição. */
export function useApi<T>(
  path: string | null,
  options: { pollMs?: number; shouldPoll?: (data: T) => boolean } = {},
) {
  const key = JSON.stringify([path, getDemoRole(), getToken()]);
  const currentKey = useRef(key);
  currentKey.current = key;
  const [state, setState] = useState<{ key: string; data: T | null; error: string | null; loading: boolean }>({ key, data: null, error: null, loading: Boolean(path) });
  const [attempt, setAttempt] = useState(0);
  const request = useRef<{ sequence: number; controller?: AbortController }>({ sequence: 0 });
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const reload = useCallback(async () => {
    if (!path || currentKey.current !== key) return;
    request.current.controller?.abort();
    const controller = new AbortController();
    const sequence = ++request.current.sequence;
    request.current.controller = controller;
    const current = () => !controller.signal.aborted && currentKey.current === key && request.current.sequence === sequence;
    try {
      const result = await api<T>(path, { signal: controller.signal });
      if (current()) setState({ key, data: result, error: null, loading: false });
    } catch (err) {
      if (current()) setState((previous) => ({ key, data: previous.key === key ? previous.data : null, error: err instanceof Error ? err.message : "Falha ao carregar", loading: false }));
    } finally {
      if (current()) setAttempt((value) => value + 1);
    }
  }, [path, key]);

  useEffect(() => {
    setState({ key, data: null, error: null, loading: Boolean(path) });
    void reload();
    return () => { request.current.controller?.abort(); request.current.sequence++; };
  }, [reload, path, key]);

  useEffect(() => {
    const { pollMs, shouldPoll } = optionsRef.current;
    if (state.key !== key || !pollMs || !state.data || !shouldPoll?.(state.data)) return;
    const timer = window.setTimeout(() => void reload(), pollMs);
    return () => window.clearTimeout(timer);
  }, [state, attempt, key, reload]);

  const visible = state.key === key ? state : { data: null, error: null, loading: Boolean(path) };
  return { data: visible.data, error: visible.error, loading: visible.loading, reload };
}
