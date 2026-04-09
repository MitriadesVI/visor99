import { useEffect, useState } from "react";

import type {
  CandidateSummaryResponse,
  CompetitiveResponse,
  FilterState,
  MunicipalComparisonResponse,
  MunicipalSort,
} from "../../api/types";
import { CaraACaraSummary } from "../cards/CaraACaraSummary";
import { CandidateHeader } from "../cards/CandidateHeader";
import { StatCard } from "../cards/StatCard";
import { ZoneCard } from "../cards/ZoneCard";
import { CoverageDonut } from "../charts/CoverageDonut";
import { MunicipalTreemap } from "../charts/MunicipalTreemap";
import { ZonesBarChart } from "../charts/ZonesBarChart";
import { DrilldownPanel } from "./DrilldownPanel";
import { CaraACaraTable } from "../tables/CaraACaraTable";
import { MunicipalRanking } from "../tables/MunicipalRanking";
import { TablesDetail } from "../tables/TablesDetail";
import { formatNumber } from "../../utils/format";

interface MainContentProps {
  candidateData: CandidateSummaryResponse | null;
  competitiveData: CompetitiveResponse | null;
  municipalData: MunicipalComparisonResponse | null;
  filters: FilterState;
  candidateLoading: boolean;
  competitiveLoading: boolean;
  municipalLoading: boolean;
  candidateError: string | null;
  competitiveError: string | null;
  municipalError: string | null;
  municipalSort: MunicipalSort;
  onMunicipalSortChange: (sort: MunicipalSort) => void;
}

function LoadingState() {
  return (
    <div className="panel rounded-[32px] p-8 text-center text-[var(--color-text-secondary)]">
      Cargando tablero territorial...
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-[32px] border border-[var(--color-red)]/40 bg-[var(--color-red)]/10 p-6 text-sm text-[var(--color-text-primary)]">
      {message}
    </div>
  );
}

export function MainContent({
  candidateData,
  competitiveData,
  municipalData,
  filters,
  candidateLoading,
  competitiveLoading,
  municipalLoading,
  candidateError,
  competitiveError,
  municipalError,
  municipalSort,
  onMunicipalSortChange,
}: MainContentProps) {
  const [selectedRival, setSelectedRival] = useState("");

  useEffect(() => {
    const defaultRival = competitiveData?.rivals[0]?.rival_name ?? "";
    if (!competitiveData) {
      return;
    }
    if (!selectedRival || !competitiveData.rivals.some((rival) => rival.rival_name === selectedRival)) {
      setSelectedRival(defaultRival);
    }
  }, [competitiveData, selectedRival]);

  if (candidateLoading && !candidateData) {
    return (
      <main className="flex-1 p-4 md:p-8">
        <LoadingState />
      </main>
    );
  }

  if (candidateError) {
    return (
      <main className="flex-1 p-4 md:p-8">
        <ErrorState message={candidateError} />
      </main>
    );
  }

  if (!candidateData) {
    return (
      <main className="flex-1 p-4 md:p-8">
        <ErrorState message="Todavía no hay datos suficientes para renderizar el tablero." />
      </main>
    );
  }

  return (
    <main className="flex-1 p-4 md:p-8">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-6">
        <CandidateHeader data={candidateData} />

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Votos totales" value={candidateData.stats.total_votes} tone="accent" />
          <StatCard label="Mesas con votos" value={candidateData.stats.tables_with_votes} />
          <StatCard label="Cobertura" value={candidateData.stats.coverage_pct} suffix="percent" tone="amber" />
          <StatCard label="Participación prom." value={candidateData.stats.avg_participation} suffix="percent" />
          <StatCard label="Mesas ganadas" value={candidateData.stats.winning_tables} tone="green" />
        </section>

        <section className="grid gap-4 xl:grid-cols-4">
          {candidateData.top_zones.slice(0, 4).map((zone) => (
            <ZoneCard key={`${zone.municipality_name}-${zone.zone_code}`} zone={zone} />
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
          <ZonesBarChart zones={candidateData.top_zones} />
          <CoverageDonut stats={candidateData.stats} />
        </section>

        <TablesDetail data={candidateData} />
        <DrilldownPanel filters={filters} />

        <section className="grid gap-6">
          {competitiveError ? (
            <ErrorState message={competitiveError} />
          ) : competitiveLoading && !competitiveData ? (
            <LoadingState />
          ) : competitiveData ? (
            <>
              <CaraACaraSummary
                data={competitiveData}
                selectedRival={selectedRival}
                onSelectRival={setSelectedRival}
              />
              <CaraACaraTable data={competitiveData} selectedRival={selectedRival} />
            </>
          ) : null}
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          {municipalError ? (
            <ErrorState message={municipalError} />
          ) : municipalLoading && !municipalData ? (
            <LoadingState />
          ) : municipalData ? (
            <>
              <div className="space-y-6">
                <MunicipalTreemap municipalities={municipalData.municipalities} sortBy={municipalSort} />
                <div className="panel rounded-3xl p-5">
                  <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
                    Resumen municipal
                  </p>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm text-[var(--color-text-secondary)]">Municipios con votos</p>
                      <p className="mt-2 font-mono text-3xl font-bold text-[var(--color-text-primary)]">
                        {formatNumber(municipalData.summary.total_municipalities)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-text-secondary)]">Municipios disponibles</p>
                      <p className="mt-2 font-mono text-3xl font-bold text-[var(--color-text-primary)]">
                        {formatNumber(municipalData.summary.total_municipalities_available)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-text-secondary)]">Mejor municipio por votos</p>
                      <p className="mt-2 text-lg font-semibold text-[var(--color-text-primary)]">
                        {municipalData.summary.best_municipality?.municipality_name ?? "N/D"}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-text-secondary)]">Más eficiente</p>
                      <p className="mt-2 text-lg font-semibold text-[var(--color-text-primary)]">
                        {municipalData.summary.most_efficient_municipality?.municipality_name ?? "N/D"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <MunicipalRanking
                data={municipalData}
                sortBy={municipalSort}
                onSortChange={onMunicipalSortChange}
              />
            </>
          ) : null}
        </section>
      </div>
    </main>
  );
}
