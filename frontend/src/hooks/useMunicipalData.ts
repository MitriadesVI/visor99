import { useEffect, useState } from "react";

import { fetchJson } from "../api/client";
import type { FilterState, MunicipalComparisonResponse, MunicipalSort } from "../api/types";


export function useMunicipalData(filters: FilterState, sortBy: MunicipalSort, limit = 30) {
  const [data, setData] = useState<MunicipalComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!filters.dataset || !filters.contest || !filters.candidate) {
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    fetchJson<MunicipalComparisonResponse>(
      "/api/municipal/comparison",
      {
        ...filters,
        sort_by: sortBy,
        limit,
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
        setError(requestError instanceof Error ? requestError.message : "No se pudo cargar la comparación municipal.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [filters, sortBy, limit]);

  return { data, loading, error };
}
