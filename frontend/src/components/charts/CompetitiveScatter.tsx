import {
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { CompetitiveResponse, HeadToHeadPoint } from "../../api/types";
import { colors } from "../../styles/tokens";
import { formatPercent } from "../../utils/format";

const palette = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6"];

function groupByZone(points: HeadToHeadPoint[]) {
  return points.reduce<Record<string, HeadToHeadPoint[]>>((accumulator, point) => {
    const key = point.zone_code || "S/N";
    accumulator[key] ??= [];
    accumulator[key].push(point);
    return accumulator;
  }, {});
}

export function CompetitiveScatter({
  data,
  selectedRival,
}: {
  data: CompetitiveResponse;
  selectedRival: string;
}) {
  const filtered = data.head_to_head.filter((point) => point.rival_name === selectedRival);
  const grouped = groupByZone(filtered);

  return (
    <div className="panel rounded-3xl p-5">
      <div className="mb-5">
        <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
          Cara a cara
        </p>
        <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
          Participación mesa a mesa vs. {selectedRival}
        </h3>
      </div>

      <div className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 16, bottom: 12, left: 0 }}>
            <CartesianGrid stroke="rgba(148,163,184,0.08)" />
            <XAxis
              type="number"
              dataKey="candidate_pct"
              name="Baute"
              tick={{ fill: colors.textMuted, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="number"
              dataKey="rival_pct"
              name="Rival"
              tick={{ fill: colors.textMuted, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 18,
                color: colors.textPrimary,
              }}
              formatter={(value: number, label) => [formatPercent(value, 2), label]}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.table_key ?? "Mesa"}
            />
            <Legend />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 100, y: 100 }]} stroke={colors.textMuted} strokeDasharray="4 4" />
            {Object.entries(grouped).map(([zoneCode, points], index) => (
              <Scatter
                key={zoneCode}
                name={`Zona ${zoneCode}`}
                data={points}
                fill={palette[index % palette.length]}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
