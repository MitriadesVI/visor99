import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ZoneSummary } from "../../api/types";
import { colors } from "../../styles/tokens";
import { formatCompact, formatPercent } from "../../utils/format";

const palette = ["#3B82F6", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"];

export function ZonesBarChart({ zones }: { zones: ZoneSummary[] }) {
  return (
    <div className="panel rounded-3xl p-5">
      <div className="mb-5">
        <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
          Intensidad territorial
        </p>
        <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
          Zonas con más votos
        </h3>
      </div>

      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={zones}>
            <CartesianGrid stroke="rgba(148,163,184,0.08)" vertical={false} />
            <XAxis
              dataKey="zone_label"
              tick={{ fill: colors.textMuted, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: colors.textMuted, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(59,130,246,0.08)" }}
              contentStyle={{
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 18,
                color: colors.textPrimary,
              }}
              formatter={(value: number, _name, entry) => [
                formatCompact(Number(value)),
                `${entry.payload.municipality_name} · ${formatPercent(entry.payload.participation, 2)}`,
              ]}
            />
            <Bar dataKey="votes" radius={[10, 10, 0, 0]}>
              {zones.map((zone, index) => (
                <Cell key={zone.zone_label} fill={palette[index % palette.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
