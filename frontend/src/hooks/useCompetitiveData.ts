import { useEffect, useState } from "react";

import { fetchJson } from "../api/client";
import type { CompetitiveResponse, FilterState } from "../api/types";


export function useCompetitiveData(filters: FilterState, topN = 15) {
  const [data, setData] = useState<CompetitiveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!filters.dataset || !filters.contest || !filters.candidate) {
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    fetchJson<CompetitiveResponse>(
      "/api/competitive/rivals",
      {
        ...filters,
        top_n: topN,
      },
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
        setError(requestError instanceof Error ? requestError.message : "No se pudo cargar el análisis competitivo.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [filters, topN]);

  return { data, loading, error };
}
