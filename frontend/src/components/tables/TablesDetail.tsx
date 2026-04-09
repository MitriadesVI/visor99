import { useMemo, useState } from "react";

import type { CandidateSummaryResponse, TableSummary } from "../../api/types";
import { formatNumber, formatPercent } from "../../utils/format";

type TableMode = "top" | "won" | "lost";

function rowTone(mode: TableMode, row: TableSummary) {
  if (mode === "won") {
    return "text-[var(--color-green)]";
  }
  return row.margin < 0 ? "text-[var(--color-red)]" : "text-[var(--color-green)]";
}

function progressWidth(value: number) {
  return `${Math.max(0, Math.min(value, 100))}%`;
}

export function TablesDetail({ data }: { data: CandidateSummaryResponse }) {
  const [mode, setMode] = useState<TableMode>("top");

  const rows = useMemo(() => {
    if (mode === "won") {
      return data.tables_won;
    }
    if (mode === "lost") {
      return data.tables_lost_narrow;
    }
    return data.top_tables;
  }, [data, mode]);

  const subtitle = useMemo(() => {
    if (mode === "won") {
      const pct = data.stats.tables_with_votes
        ? (data.stats.winning_tables / data.stats.tables_with_votes) * 100
        : 0;
      return `${formatNumber(data.stats.winning_tables)} mesas ganadas de ${formatNumber(data.stats.tables_with_votes)} (${pct.toFixed(1)}%)`;
    }
    if (mode === "lost") {
      return `${formatNumber(data.stats.narrow_loss_tables)} mesas perdidas por margen <= ${formatNumber(
        data.stats.narrow_loss_margin_threshold,
      )} votos`;
    }
    return `Mostrando las ${formatNumber(rows.length)} mesas con más votos de ${formatNumber(
      data.stats.tables_with_votes,
    )} con presencia`;
  }, [data.stats.narrow_loss_margin_threshold, data.stats.narrow_loss_tables, data.stats.tables_with_votes, data.stats.winning_tables, mode, rows.length]);

  return (
    <div className="panel rounded-3xl p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
            Detalle operativo
          </p>
          <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
            Mesas clave del alcance actual
          </h3>
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">{subtitle}</p>
        </div>
        <div className="flex gap-2">
          {[
            { key: "top", label: "Top mesas" },
            { key: "won", label: "Ganadas" },
            { key: "lost", label: "Perdidas por poco" },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setMode(item.key as TableMode)}
              className={`rounded-full border px-4 py-2 text-sm ${
                mode === item.key
                  ? "border-[var(--color-accent)] bg-[var(--color-accent)]/15 text-[var(--color-text-primary)]"
                  : "border-[var(--color-border)] text-[var(--color-text-secondary)]"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-2">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.26em] text-[var(--color-text-muted)]">
              <th className="pb-2">Municipio</th>
              <th className="pb-2">Zona</th>
              <th className="pb-2">Puesto</th>
              <th className="pb-2">Mesa</th>
              <th className="pb-2">Votos</th>
              <th className="pb-2">Total mesa</th>
              <th className="pb-2">% mesa</th>
              <th className="pb-2">Margen</th>
              <th className="pb-2">Rival</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${mode}-${row.table_key}`} className="bg-white/[0.02]">
                <td className="rounded-l-2xl px-4 py-3 text-sm text-[var(--color-text-primary)]">
                  {row.municipality_name}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                  {row.zone_code ?? "S/N"}
                </td>
                <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                  {row.polling_place_name}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                  {row.table_code}
                </td>
                <td className="px-4 py-3 font-mono text-sm font-semibold text-[var(--color-accent)]">
                  {formatNumber(row.votes)}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                  {formatNumber(row.total_table_votes)}
                </td>
                <td className="px-4 py-3">
                  <div className="font-mono text-sm text-[var(--color-text-primary)]">
                    {formatPercent(row.pct, 2)}
                  </div>
                  <div className="mt-2 h-1.5 w-24 overflow-hidden rounded-full bg-[var(--color-border)]">
                    <div
                      className="h-full rounded-full bg-[var(--color-accent)]"
                      style={{ width: progressWidth(row.pct) }}
                    />
                  </div>
                </td>
                <td className={`px-4 py-3 font-mono text-sm ${rowTone(mode, row)}`}>
                  {row.margin > 0 ? `+${formatNumber(row.margin)}` : formatNumber(row.margin)}
                </td>
                <td className="rounded-r-2xl px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                  <div className="text-[var(--color-text-primary)]">{row.rival_name ?? "N/D"}</div>
                  <div className="mt-1 font-mono text-xs text-[var(--color-text-muted)]">
                    {formatNumber(row.rival_votes ?? 0)} votos
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
