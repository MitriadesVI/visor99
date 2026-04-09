import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { CandidateStats } from "../../api/types";
import { colors } from "../../styles/tokens";
import { formatNumber, formatPercent } from "../../utils/format";

export function CoverageDonut({ stats }: { stats: CandidateStats }) {
  const data = [
    { name: "Mesas con votos", value: stats.tables_with_votes, color: colors.accent },
    { name: "Mesas sin votos", value: stats.tables_without_votes, color: colors.border },
  ];

  return (
    <div className="panel rounded-3xl p-5">
      <div className="mb-5">
        <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
          Cobertura
        </p>
        <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
          Presencia sobre mesas observadas
        </h3>
      </div>

      <div className="relative h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              contentStyle={{
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 18,
                color: colors.textPrimary,
              }}
              formatter={(value: number) => formatNumber(value)}
            />
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={85}
              outerRadius={110}
              paddingAngle={6}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
            Cobertura actual
          </p>
          <p className="mt-3 font-mono text-4xl font-bold text-[var(--color-text-primary)]">
            {formatPercent(stats.coverage_pct, 1)}
          </p>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
            {stats.winning_tables} mesas ganadas
          </p>
        </div>
      </div>
    </div>
  );
}
