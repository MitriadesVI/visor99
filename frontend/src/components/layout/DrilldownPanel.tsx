import { useEffect, useMemo, useState } from "react";

import { fetchJson } from "../../api/client";
import type {
  CandidateDrilldownResponse,
  DrilldownLevel,
  FilterState,
  PollingPlaceDrilldownItem,
  TableDrilldownItem,
  ZoneDrilldownItem,
} from "../../api/types";
import { formatNumber, formatPercent } from "../../utils/format";

function BreadcrumbButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  if (active || !onClick) {
    return <span className={active ? "text-[var(--color-text-primary)]" : "text-[var(--color-text-secondary)]"}>{label}</span>;
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="text-[var(--color-text-secondary)] transition hover:text-[var(--color-text-primary)]"
    >
      {label}
    </button>
  );
}

function ZoneCard({
  zone,
  onSelect,
}: {
  zone: ZoneDrilldownItem;
  onSelect: (zoneCode: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(zone.zone_code ?? "")}
      className="rounded-[28px] border border-[var(--color-border)] bg-white/[0.03] p-5 text-left transition hover:border-[var(--color-accent)] hover:bg-[var(--color-accent)]/10"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-[var(--color-text-muted)]">Zona</p>
          <h4 className="mt-2 text-2xl font-bold text-[var(--color-text-primary)]">
            {zone.zone_code ?? "S/N"}
          </h4>
        </div>
        <span className="rounded-full border border-[var(--color-border)] px-3 py-1 text-xs text-[var(--color-text-secondary)]">
          Rank #{zone.rank_in_zone || "-"}
        </span>
      </div>

      <div className="mt-5 grid gap-3 text-sm text-[var(--color-text-secondary)]">
        <div className="flex items-center justify-between">
          <span>Votos del candidato</span>
          <span className="font-mono text-[var(--color-text-primary)]">{formatNumber(zone.candidate_votes)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Participación</span>
          <span className="font-mono text-[var(--color-text-primary)]">{formatPercent(zone.candidate_pct, 2)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Mesas activas</span>
          <span className="font-mono text-[var(--color-text-primary)]">
            {formatNumber(zone.tables_with_votes)}/{formatNumber(zone.tables_total)}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Puestos</span>
          <span className="font-mono text-[var(--color-text-primary)]">{formatNumber(zone.places_count)}</span>
        </div>
      </div>

      <div className="mt-5 border-t border-[var(--color-border)] pt-4 text-sm text-[var(--color-text-secondary)]">
        Gana: <span className="font-semibold text-[var(--color-text-primary)]">{zone.zone_winner ?? "N/D"}</span>
      </div>
    </button>
  );
}

function PollingPlaceTable({
  items,
  onSelect,
}: {
  items: PollingPlaceDrilldownItem[];
  onSelect: (placeCode: string) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-y-2">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-[0.26em] text-[var(--color-text-muted)]">
            <th className="pb-2">Puesto</th>
            <th className="pb-2">Votos candidato</th>
            <th className="pb-2">Total votos</th>
            <th className="pb-2">% candidato</th>
            <th className="pb-2">Mesas</th>
            <th className="pb-2">Ganador</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.polling_place_code ?? item.polling_place_name}
              className="cursor-pointer bg-white/[0.02] transition hover:bg-[var(--color-accent)]/10"
              onClick={() => onSelect(item.polling_place_code ?? "")}
            >
              <td className="rounded-l-2xl px-4 py-3 text-sm font-semibold text-[var(--color-text-primary)]">
                <div>{item.polling_place_name ?? "Sin nombre"}</div>
                <div className="mt-1 font-mono text-xs text-[var(--color-text-muted)]">
                  Código {item.polling_place_code ?? "S/N"}
                </div>
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-primary)]">
                {formatNumber(item.candidate_votes)}
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                {formatNumber(item.total_votes)}
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                {formatPercent(item.candidate_pct, 2)}
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                {formatNumber(item.tables_with_votes)}/{formatNumber(item.tables_total)}
              </td>
              <td className="rounded-r-2xl px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                {item.place_winner ?? "N/D"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TableDrilldownTable({ items }: { items: TableDrilldownItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-y-2">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-[0.26em] text-[var(--color-text-muted)]">
            <th className="pb-2">Mesa</th>
            <th className="pb-2">Votos candidato</th>
            <th className="pb-2">Total mesa</th>
            <th className="pb-2">% candidato</th>
            <th className="pb-2">Ganador</th>
            <th className="pb-2">Margen</th>
            <th className="pb-2">Top rivales</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.table_code ?? `${item.rank_in_table}-${item.candidate_votes}`} className="bg-white/[0.02] align-top">
              <td className="rounded-l-2xl px-4 py-3 font-mono text-sm text-[var(--color-text-primary)]">
                {item.table_code ?? "S/N"}
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-primary)]">
                {formatNumber(item.candidate_votes)}
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                {formatNumber(item.total_votes)}
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                {formatPercent(item.candidate_pct, 2)}
              </td>
              <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                <div className="font-semibold text-[var(--color-text-primary)]">{item.table_winner ?? "N/D"}</div>
                <div className="mt-1 font-mono text-xs text-[var(--color-text-muted)]">
                  {formatNumber(item.table_winner_votes)} votos
                </div>
              </td>
              <td className="px-4 py-3 font-mono text-sm text-[var(--color-green)]">
                {formatNumber(item.margin_vs_second)}
              </td>
              <td className="rounded-r-2xl px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                <div className="space-y-2">
                  {item.top_rivals.map((rival) => (
                    <div key={`${item.table_code}-${rival.name}`} className="rounded-2xl bg-white/[0.04] px-3 py-2">
                      <div className="font-semibold text-[var(--color-text-primary)]">{rival.name}</div>
                      <div className="mt-1 font-mono text-xs text-[var(--color-text-muted)]">
                        {formatNumber(rival.votes)} votos · {formatPercent(rival.pct, 2)}
                      </div>
                    </div>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DrilldownPanel({ filters }: { filters: FilterState }) {
  const [selectedZone, setSelectedZone] = useState("");
  const [selectedPlaceCode, setSelectedPlaceCode] = useState("");
  const [data, setData] = useState<CandidateDrilldownResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const level: DrilldownLevel = useMemo(() => {
    if (selectedPlaceCode) {
      return "table";
    }
    if (selectedZone) {
      return "polling_place";
    }
    return "zone";
  }, [selectedPlaceCode, selectedZone]);

  useEffect(() => {
    setSelectedZone("");
    setSelectedPlaceCode("");
  }, [filters.dataset, filters.contest, filters.department, filters.municipality, filters.party, filters.candidate]);

  useEffect(() => {
    if (!filters.dataset || !filters.contest || !filters.candidate || filters.municipality === "Todos") {
      setData(null);
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    fetchJson<CandidateDrilldownResponse>(
      "/api/candidate/drilldown",
      {
        ...filters,
        level,
        zone_code: selectedZone || undefined,
        polling_place_code: selectedPlaceCode || undefined,
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
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudo cargar el drilldown territorial.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [filters, level, selectedPlaceCode, selectedZone]);

  if (filters.municipality === "Todos") {
    return (
      <div className="panel rounded-3xl p-5">
        <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
          Centro de mando territorial
        </p>
        <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
          Drilldown zona → puesto → mesa
        </h3>
        <p className="mt-4 text-sm text-[var(--color-text-secondary)]">
          Selecciona un municipio en los filtros para habilitar la navegación profunda por zona, puesto y mesa.
        </p>
      </div>
    );
  }

  return (
    <div className="panel rounded-3xl p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
            Centro de mando territorial
          </p>
          <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
            Drilldown zona → puesto → mesa
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <BreadcrumbButton
            label={filters.municipality}
            active={!selectedZone}
            onClick={selectedZone ? () => { setSelectedZone(""); setSelectedPlaceCode(""); } : undefined}
          />
          {selectedZone && <span className="text-[var(--color-text-muted)]">&gt;</span>}
          {selectedZone && (
            <BreadcrumbButton
              label={`Zona ${selectedZone}`}
              active={!selectedPlaceCode}
              onClick={selectedPlaceCode ? () => setSelectedPlaceCode("") : undefined}
            />
          )}
          {selectedPlaceCode && <span className="text-[var(--color-text-muted)]">&gt;</span>}
          {selectedPlaceCode && (
            <BreadcrumbButton
              label={data?.context.polling_place_name ?? `Puesto ${selectedPlaceCode}`}
              active
            />
          )}
        </div>
      </div>

      {error && (
        <div className="mt-5 rounded-[24px] border border-[var(--color-red)]/40 bg-[var(--color-red)]/10 p-4 text-sm text-[var(--color-text-primary)]">
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="mt-5 rounded-[24px] bg-white/[0.03] p-6 text-sm text-[var(--color-text-secondary)]">
          Cargando detalle territorial...
        </div>
      ) : null}

      {data?.level === "zone" && (
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.items.map((zone) => (
            <ZoneCard key={zone.zone_code ?? "S/N"} zone={zone} onSelect={setSelectedZone} />
          ))}
        </div>
      )}

      {data?.level === "polling_place" && (
        <div className="mt-5">
          <PollingPlaceTable
            items={data.items}
            onSelect={(placeCode) => setSelectedPlaceCode(placeCode)}
          />
        </div>
      )}

      {data?.level === "table" && (
        <div className="mt-5">
          <TableDrilldownTable items={data.items} />
        </div>
      )}
    </div>
  );
}
