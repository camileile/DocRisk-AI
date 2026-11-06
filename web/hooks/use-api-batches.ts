"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchApiBatches, type ApiBatch } from "@/lib/api-client";

export function useApiBatches(token: string) {
  const [items, setItems] = useState<ApiBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  const refresh = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setError("");
    fetchApiBatches(token, controller.signal).then((batches) => {
      if (active) setItems(batches);
    }).catch((reason: unknown) => {
      if (active) {
        setItems([]);
        setError(reason instanceof Error ? reason.message : "Falha ao consultar lotes.");
      }
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [token, revision]);

  return { items, loading, error, refresh };
}
