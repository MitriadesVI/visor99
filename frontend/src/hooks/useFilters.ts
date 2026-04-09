import { useEffect, useMemo, useState } from "react";

import { fetchJson } from "../api/client";
import type { DatasetItem, FilterOptionsResponse, FilterState } from "../api/types";

const DEFAULT_CANDIDATE = "GONZALO DIMAS BAUTE GONZALEZ";
const DEFAULT_CONTEST = "SENADO";

interface FilterCollections {
  datasets: DatasetItem[];
  contests: string[];
  departments: string[];
  municipalities: string[];
  parties: string[];
  candidates: string[];
}

function chooseValue(current: string, options: string[], preferred?: string): string {
  if (current && options.includes(current)) {
    return current;
  }
  if (preferred && options.includes(preferred)) {
    return preferred;
  }
  return options[0] ?? "";
}

export function useFilters() {
  const [state, setState] = useState<FilterState>({
    dataset: "",
    contest: "",
    department: "Todos",
    municipality: "Todos",
    party: "Todos",
    candidate: "",
  });
  const [options, setOptions] = useState<FilterCollections>({
    datasets: [],
    contests: [],
    departments: [],
    municipalities: [],
    parties: [],
    candidates: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);

    fetchJson<DatasetItem[]>("/api/datasets", undefined, controller.signal)
      .then((datasets) => {
        setOptions((previous) => ({ ...previous, datasets }));
        setState((previous) => ({
          ...previous,
          dataset: previous.dataset || datasets[0]?.path || "",
        }));
      })
      .catch((requestError) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "No se pudieron cargar los datasets.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!state.dataset) {
      return;
    }

    const controller = new AbortController();

    fetchJson<FilterOptionsResponse>(
      "/api/filters",
      {
        dataset: state.dataset,
        contest: state.contest || undefined,
        department: state.department,
        municipality: state.municipality,
        party: state.party,
      },
      controller.signal,
    )
      .then((payload) => {
        setOptions((previous) => ({
          ...previous,
          contests: payload.contests,
          departments: payload.departments,
          municipalities: payload.municipalities,
          parties: payload.parties,
          candidates: payload.candidates,
        }));

        setState((previous) => {
          const nextContest = chooseValue(previous.contest, payload.contests, DEFAULT_CONTEST);
          const nextDepartment = previous.department === "Todos" || payload.departments.includes(previous.department)
            ? previous.department
            : "Todos";
          const nextMunicipality =
            previous.municipality === "Todos" || payload.municipalities.includes(previous.municipality)
              ? previous.municipality
              : "Todos";
          const nextParty =
            previous.party === "Todos" || payload.parties.includes(previous.party)
              ? previous.party
              : "Todos";
          const nextCandidate = chooseValue(previous.candidate, payload.candidates, DEFAULT_CANDIDATE);

          if (
            nextContest === previous.contest &&
            nextDepartment === previous.department &&
            nextMunicipality === previous.municipality &&
            nextParty === previous.party &&
            nextCandidate === previous.candidate
          ) {
            return previous;
          }

          return {
            ...previous,
            contest: nextContest,
            department: nextDepartment,
            municipality: nextMunicipality,
            party: nextParty,
            candidate: nextCandidate,
          };
        });
        setError(null);
      })
      .catch((requestError) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "No se pudieron cargar los filtros.");
      });

    return () => controller.abort();
  }, [state.dataset, state.contest, state.department, state.municipality, state.party]);

  const setFilter = (field: keyof FilterState, value: string) => {
    setState((previous) => {
      if (field === "dataset") {
        return {
          dataset: value,
          contest: "",
          department: "Todos",
          municipality: "Todos",
          party: "Todos",
          candidate: "",
        };
      }

      if (field === "contest") {
        return {
          ...previous,
          contest: value,
          department: "Todos",
          municipality: "Todos",
          party: "Todos",
          candidate: "",
        };
      }

      if (field === "department") {
        return {
          ...previous,
          department: value,
          municipality: "Todos",
          party: "Todos",
          candidate: "",
        };
      }

      if (field === "municipality") {
        return {
          ...previous,
          municipality: value,
          party: "Todos",
          candidate: "",
        };
      }

      if (field === "party") {
        return {
          ...previous,
          party: value,
          candidate: "",
        };
      }

      return { ...previous, [field]: value };
    });
  };

  const collections = useMemo(
    () => ({
      datasets: options.datasets,
      contests: options.contests,
      departments: ["Todos", ...options.departments],
      municipalities: ["Todos", ...options.municipalities],
      parties: ["Todos", ...options.parties],
      candidates: options.candidates,
    }),
    [options],
  );

  return {
    state,
    options: collections,
    setFilter,
    loading,
    error,
  };
}
