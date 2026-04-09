import { useState } from "react";

import { MainContent } from "./components/layout/MainContent";
import { Sidebar } from "./components/layout/Sidebar";
import { useCandidateData } from "./hooks/useCandidateData";
import { useCompetitiveData } from "./hooks/useCompetitiveData";
import { useFilters } from "./hooks/useFilters";
import { useMunicipalData } from "./hooks/useMunicipalData";
import type { MunicipalSort } from "./api/types";

export default function App() {
  const filters = useFilters();
  const [municipalSort, setMunicipalSort] = useState<MunicipalSort>("votes");

  const candidate = useCandidateData(filters.state);
  const competitive = useCompetitiveData(filters.state, 15);
  const municipal = useMunicipalData(filters.state, municipalSort, 30);

  return (
    <div className="min-h-screen bg-transparent text-[var(--color-text-primary)]">
      <div className="mx-auto min-h-screen max-w-[1800px] md:flex">
        <Sidebar
          state={filters.state}
          datasets={filters.options.datasets}
          contests={filters.options.contests}
          departments={filters.options.departments}
          municipalities={filters.options.municipalities}
          parties={filters.options.parties}
          candidates={filters.options.candidates}
          onChange={filters.setFilter}
        />
        <MainContent
          candidateData={candidate.data}
          competitiveData={competitive.data}
          municipalData={municipal.data}
          filters={filters.state}
          candidateLoading={candidate.loading || filters.loading}
          competitiveLoading={competitive.loading}
          municipalLoading={municipal.loading}
          candidateError={filters.error || candidate.error}
          competitiveError={competitive.error}
          municipalError={municipal.error}
          municipalSort={municipalSort}
          onMunicipalSortChange={setMunicipalSort}
        />
      </div>
    </div>
  );
}
