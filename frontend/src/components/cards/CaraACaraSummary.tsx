import { useEffect, useMemo, useState } from "react";

import { formatNumber } from "../../utils/format";
import type { CompetitiveResponse } from "../../api/types";

export function CaraACaraSummary({
  data,
  selectedRival,
  onSelectRival,
}: {
  data: CompetitiveResponse;
  selectedRival: string;
  onSelectRival: (rival: string) => void;
}) {
  const rival = data.rivals.find((item) => item.rival_name === selectedRival) ?? data.rivals[0];
  const [query, setQuery] = useState("");

  const filteredRivals = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return data.rivals;
    }
    return data.rivals.filter((item) => item.rival_name.toLowerCase().includes(normalized));
  }, [data.rivals, query]);

  useEffect(() => {
    if (!data.rivals.length || data.rivals.length <= 10) {
      return;
    }
    if (filteredRivals.some((item) => item.rival_name === selectedRival)) {
      return;
    }
    const next = filteredRivals[0]?.rival_name ?? data.rivals[0]?.rival_name;
    if (next && next !== selectedRival) {
      onSelectRival(next);
    }
  }, [data.rivals, filteredRivals, onSelectRival, selectedRival]);

  if (!rival) {
    return null;
  }

  const duelTables = rival.tables_candidate_wins + rival.tables_rival_wins + rival.tables_tied;
  const candidateWidth = duelTables ? (rival.tables_candidate_wins / duelTables) * 100 : 0;
  const tiedWidth = duelTables ? (rival.tables_tied / duelTables) * 100 : 0;
  const rivalWidth = duelTables ? (rival.tables_rival_wins / duelTables) * 100 : 0;

  return (
    <div className="panel rounded-3xl p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
            Cara a cara
          </p>
          <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
            Duelo directo por mesa
          </h3>
        </div>
        <label className="flex flex-col gap-2 text-sm text-[var(--color-text-secondary)]">
          Rival a comparar
          {data.rivals.length > 10 ? (
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar rival..."
              className="rounded-2xl border border-[var(--color-border)] bg-white/[0.04] px-4 py-3 text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)]"
            />
          ) : null}
          <select
            value={filteredRivals.some((item) => item.rival_name === rival.rival_name) ? rival.rival_name : ""}
            onChange={(event) => onSelectRival(event.target.value)}
            className="rounded-2xl border border-[var(--color-border)] bg-white/[0.04] px-4 py-3 text-[var(--color-text-primary)] outline-none"
          >
            {!filteredRivals.length ? (
              <option value="" disabled>
                Sin coincidencias
              </option>
            ) : null}
            {filteredRivals.map((item) => (
              <option key={item.rival_name} value={item.rival_name}>
                {item.rival_name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
        <div>
          <p className="text-sm text-[var(--color-text-secondary)]">Candidato foco</p>
          <p className="mt-2 text-lg font-bold text-[var(--color-text-primary)]">{data.candidate.name}</p>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {formatNumber(rival.candidate_votes)} votos en mesas compartidas
          </p>
        </div>

        <div className="hidden text-xs uppercase tracking-[0.26em] text-[var(--color-text-muted)] lg:block">
          vs
        </div>

        <div className="lg:text-right">
          <p className="text-sm text-[var(--color-text-secondary)]">Rival seleccionado</p>
          <p className="mt-2 text-lg font-bold text-[var(--color-text-primary)]">{rival.rival_name}</p>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {formatNumber(rival.rival_votes)} votos en mesas compartidas
          </p>
        </div>
      </div>

      <div className="mt-6 h-4 overflow-hidden rounded-full bg-[var(--color-border)]">
        <div className="flex h-full">
          <div className="h-full bg-[var(--color-accent)]" style={{ width: `${candidateWidth}%` }} />
          <div className="h-full bg-white/15" style={{ width: `${tiedWidth}%` }} />
          <div className="h-full bg-[var(--color-red)]" style={{ width: `${rivalWidth}%` }} />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-4 text-sm text-[var(--color-text-secondary)]">
        <span>Baute gana {formatNumber(rival.tables_candidate_wins)} mesas</span>
        <span>Rival gana {formatNumber(rival.tables_rival_wins)} mesas</span>
        <span>Empate {formatNumber(rival.tables_tied)} mesas</span>
      </div>
    </div>
  );
}
