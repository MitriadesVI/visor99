import { useMemo, useState } from "react";

import type { CompetitiveResponse, HeadToHeadPoint } from "../../api/types";
import { formatNumber } from "../../utils/format";

type SortKey = "difference" | "candidate" | "rival";

function winnerTone(candidateName: string, winnerName: string) {
  if (winnerName === candidateName) {
    return "text-[var(--color-accent)]";
  }
  if (winnerName === "Empate") {
    return "text-[var(--color-text-secondary)]";
  }
  return "text-[var(--color-red)]";
}

export function CaraACaraTable({
  data,
  selectedRival,
}: {
  data: CompetitiveResponse;
  selectedRival: string;
}) {
  const [sortBy, setSortBy] = useState<SortKey>("difference");
  const [zoneFilter, setZoneFilter] = useState("Todas");

  const availableZones = useMemo(
    () =>
      Array.from(
        new Set(
          data.head_to_head
            .filter((row) => row.rival_name === selectedRival)
            .map((row) => row.zone_code || "S/N"),
        ),
      ).sort((left, right) => left.localeCompare(right)),
    [data.head_to_head, selectedRival],
  );

  const rows = useMemo(() => {
    const filtered = data.head_to_head.filter((row) => {
      if (row.rival_name !== selectedRival) {
        return false;
      }
      if (zoneFilter === "Todas") {
        return true;
      }
      return (row.zone_code || "S/N") === zoneFilter;
    });

    const sorters: Record<SortKey, (left: HeadToHeadPoint, right: HeadToHeadPoint) => number> = {
      difference: (left, right) =>
        left.vote_difference - right.vote_difference || right.candidate_votes - left.candidate_votes,
      candidate: (left, right) =>
        right.candidate_votes - left.candidate_votes || left.vote_difference - right.vote_difference,
      rival: (left, right) =>
        right.rival_votes - left.rival_votes || left.vote_difference - right.vote_difference,
    };

    return [...filtered].sort(sorters[sortBy]);
  }, [data.head_to_head, selectedRival, sortBy, zoneFilter]);

  return (
    <div className="panel rounded-3xl p-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
            Mesa a mesa
          </p>
          <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
            Donde gana, pierde o empata el duelo actual
          </h3>
        </div>

        <div className="flex flex-col gap-3 md:flex-row">
          <label className="flex flex-col gap-2 text-sm text-[var(--color-text-secondary)]">
            Filtrar zona
            <select
              value={zoneFilter}
              onChange={(event) => setZoneFilter(event.target.value)}
              className="rounded-2xl border border-[var(--color-border)] bg-white/[0.04] px-4 py-3 text-[var(--color-text-primary)] outline-none"
            >
              <option value="Todas">Todas</option>
              {availableZones.map((zone) => (
                <option key={zone} value={zone}>
                  Zona {zone}
                </option>
              ))}
            </select>
          </label>

          <div className="flex gap-2 self-end">
            {[
              { key: "difference", label: "Diferencia" },
              { key: "candidate", label: "Votos Baute" },
              { key: "rival", label: "Votos rival" },
            ].map((control) => (
              <button
                key={control.key}
                type="button"
                onClick={() => setSortBy(control.key as SortKey)}
                className={`rounded-full border px-4 py-2 text-sm ${
                  sortBy === control.key
                    ? "border-[var(--color-accent)] bg-[var(--color-accent)]/15 text-[var(--color-text-primary)]"
                    : "border-[var(--color-border)] text-[var(--color-text-secondary)]"
                }`}
              >
                {control.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-2">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.26em] text-[var(--color-text-muted)]">
              <th className="pb-2">Zona</th>
              <th className="pb-2">Puesto</th>
              <th className="pb-2">Mesa</th>
              <th className="pb-2">Baute</th>
              <th className="pb-2">Rival</th>
              <th className="pb-2">Diferencia</th>
              <th className="pb-2">Ganador</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.rival_name}-${row.table_key}`} className="bg-white/[0.02]">
                <td className="rounded-l-2xl px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                  {row.zone_code ?? "S/N"}
                </td>
                <td className="px-4 py-3 text-sm text-[var(--color-text-primary)]">
                  {row.polling_place_name ?? row.polling_place_code ?? "Sin puesto"}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                  {row.table_code ?? row.table_key}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-primary)]">
                  {formatNumber(row.candidate_votes)}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-primary)]">
                  {formatNumber(row.rival_votes)}
                </td>
                <td
                  className={`px-4 py-3 font-mono text-sm ${
                    row.vote_difference >= 0 ? "text-[var(--color-green)]" : "text-[var(--color-red)]"
                  }`}
                >
                  {row.vote_difference > 0 ? "+" : ""}
                  {formatNumber(row.vote_difference)}
                </td>
                <td
                  className={`rounded-r-2xl px-4 py-3 text-sm font-semibold ${winnerTone(
                    data.candidate.name,
                    row.winner_name,
                  )}`}
                >
                  {row.winner_name}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
