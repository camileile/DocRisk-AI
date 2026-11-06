"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

/* Carrega um recurso da API com estados de carregamento e erro.
 * `path = null` não carrega nada; `pollMs` recarrega enquanto `shouldPoll(data)`. */
export function useApi<T>(
  path: string | null,
  options: { pollMs?: number; shouldPoll?: (data: T) => boolean } = {},
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const reload = useCallback(async () => {
    if (!path) return;
    try {
      const result = await api<T>(path);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    setLoading(Boolean(path));
    setData(null);
    void reload();
  }, [reload, path]);

  useEffect(() => {
    const { pollMs, shouldPoll } = optionsRef.current;
    if (!pollMs || !data || !shouldPoll?.(data)) return;
    const timer = window.setTimeout(() => void reload(), pollMs);
    return () => window.clearTimeout(timer);
  }, [data, reload]);

  return { data, error, loading, reload };
}
