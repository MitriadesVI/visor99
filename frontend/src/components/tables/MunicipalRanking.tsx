import type { MunicipalComparisonResponse, MunicipalSort } from "../../api/types";
import { formatNumber, formatPercent } from "../../utils/format";

export function MunicipalRanking({
  data,
  sortBy,
  onSortChange,
}: {
  data: MunicipalComparisonResponse;
  sortBy: MunicipalSort;
  onSortChange: (sort: MunicipalSort) => void;
}) {
  const controls: { key: MunicipalSort; label: string }[] = [
    { key: "votes", label: "Votos" },
    { key: "efficiency", label: "Eficiencia" },
    { key: "coverage", label: "Cobertura" },
  ];

  return (
    <div className="panel rounded-3xl p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
            Ranking municipal
          </p>
          <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
            Municipios que sí rinden y los que no
          </h3>
        </div>
        <div className="flex gap-2">
          {controls.map((control) => (
            <button
              key={control.key}
              type="button"
              onClick={() => onSortChange(control.key)}
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

      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-2">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.26em] text-[var(--color-text-muted)]">
              <th className="pb-2">Municipio</th>
              <th className="pb-2">Departamento</th>
              <th className="pb-2">Votos</th>
              <th className="pb-2">Mesas activas</th>
              <th className="pb-2">Cobertura</th>
              <th className="pb-2">Eficiencia</th>
              <th className="pb-2">Rival principal</th>
            </tr>
          </thead>
          <tbody>
            {data.municipalities.map((municipality, index) => (
              <tr
                key={`${municipality.department_name}-${municipality.municipality_name}`}
                className={index < 3 ? "bg-[var(--color-accent)]/10" : "bg-white/[0.02]"}
              >
                <td className="rounded-l-2xl px-4 py-3 text-sm font-semibold text-[var(--color-text-primary)]">
                  {municipality.municipality_name}
                </td>
                <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                  {municipality.department_name}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-primary)]">
                  {formatNumber(municipality.total_votes)}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                  {formatNumber(municipality.tables_with_votes)}/{formatNumber(municipality.total_tables)}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-text-secondary)]">
                  {formatPercent(municipality.coverage_pct, 1)}
                </td>
                <td className="px-4 py-3 font-mono text-sm text-[var(--color-accent)]">
                  {municipality.efficiency.toFixed(2)}
                </td>
                <td className="rounded-r-2xl px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                  {municipality.top_rival_name ?? "Sin dato"} · {formatNumber(municipality.top_rival_votes)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
