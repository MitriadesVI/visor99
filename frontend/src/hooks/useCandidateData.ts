import { useEffect, useState } from "react";

import { fetchJson } from "../api/client";
import type { CandidateSummaryResponse, FilterState } from "../api/types";


export function useCandidateData(filters: FilterState) {
  const [data, setData] = useState<CandidateSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!filters.dataset || !filters.contest || !filters.candidate) {
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    fetchJson<CandidateSummaryResponse>(
      "/api/candidate/summary",
      { ...filters },
      controller.signal,
    )
      .then((payload) => {
        setData(payload);
        setError(null);
      })
      .catch((requestError) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "No se pudo cargar el resumen del candidato.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [filters]);

  return { data, loading, error };
}
