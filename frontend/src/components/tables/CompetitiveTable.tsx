import type { CompetitiveResponse } from "../../api/types";
import { formatNumber, formatPercent } from "../../utils/format";

export function CompetitiveTable({
  data,
  selectedRival,
  onSelectRival,
}: {
  data: CompetitiveResponse;
  selectedRival: string;
  onSelectRival: (rival: string) => void;
}) {
  return (
    <div className="panel rounded-3xl p-5">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
            Bloque competitivo
          </p>
          <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
            ¿Quién gana donde Baute pierde?
          </h3>
        </div>
        <div className="text-sm text-[var(--color-text-secondary)]">
          {data.total_candidate_tables} mesas compartidas con votos
        </div>
      </div>

      <div className="space-y-3">
        {data.rivals.map((rival) => {
          const total = rival.rival_votes + rival.candidate_votes;
          const rivalWidth = total ? (rival.rival_votes / total) * 100 : 0;
          const candidateWidth = total ? (rival.candidate_votes / total) * 100 : 0;

          return (
            <button
              key={rival.rival_name}
              type="button"
              onClick={() => onSelectRival(rival.rival_name)}
              className={`w-full rounded-3xl border p-4 text-left transition ${
                selectedRival === rival.rival_name
                  ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10"
                  : "border-[var(--color-border)] bg-white/[0.02]"
              }`}
            >
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <h4 className="text-lg font-bold text-[var(--color-text-primary)]">
                    {rival.rival_name}
                  </h4>
                  <p className="text-sm text-[var(--color-text-secondary)]">{rival.rival_party}</p>
                </div>
                <div className="grid gap-1 text-sm text-[var(--color-text-secondary)] md:text-right">
                  <span>Rival: {formatNumber(rival.rival_votes)} votos</span>
                  <span>Baute: {formatNumber(rival.candidate_votes)} votos</span>
                  <span>{rival.tables_rival_wins} mesas ganadas por el rival</span>
                </div>
              </div>

              <div className="mt-4 h-3 overflow-hidden rounded-full bg-[var(--color-border)]">
                <div className="flex h-full">
                  <div
                    className="h-full bg-[var(--color-accent)]"
                    style={{ width: `${candidateWidth}%` }}
                  />
                  <div
                    className="h-full bg-[var(--color-red)]"
                    style={{ width: `${rivalWidth}%` }}
                  />
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-4 text-xs uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                <span>Baute {formatPercent(rival.avg_candidate_participation, 2)}</span>
                <span>Rival {formatPercent(rival.avg_rival_participation, 2)}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
