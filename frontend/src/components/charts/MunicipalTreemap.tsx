import { ResponsiveContainer, Tooltip, Treemap } from "recharts";

import type { MunicipalRow, MunicipalSort } from "../../api/types";
import { colors } from "../../styles/tokens";
import { formatNumber, formatPercent } from "../../utils/format";

type TreemapDatum = MunicipalRow & {
  name: string;
  size: number;
  fill: string;
  metric_label: string;
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function toVotesColor(value: number, min: number, max: number) {
  const ratio = max === min ? 0.5 : clamp((value - min) / (max - min), 0, 1);
  const red = Math.round(22 + ratio * 37);
  const green = Math.round(47 + ratio * 90);
  const blue = Math.round(94 + ratio * 151);
  return `rgb(${red}, ${green}, ${blue})`;
}

function toEfficiencyColor(value: number) {
  if (value > 1.5) {
    return colors.green;
  }
  if (value >= 1.0) {
    return colors.amber;
  }
  return colors.red;
}

function toCoverageColor(value: number) {
  if (value > 20) {
    return colors.green;
  }
  if (value >= 10) {
    return colors.amber;
  }
  return colors.red;
}

function CustomTreemapCell(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  value?: number;
  fill?: string;
  payload?: TreemapDatum;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name = "", value = 0, fill = colors.accent, payload } = props;
  if (width < 60 || height < 36) {
    return <g />;
  }

  const votes = payload?.total_votes ?? payload?.size ?? value ?? 0;

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={12} fill={fill} fillOpacity={0.88} />
      <text x={x + 10} y={y + 22} fill="#ffffff" fontSize={12} fontWeight={700}>
        {name}
      </text>
      {height > 58 && (
        <text x={x + 10} y={y + 40} fill="rgba(255,255,255,0.82)" fontSize={11}>
          {formatNumber(votes)} votos
        </text>
      )}
      {height > 78 && payload?.metric_label && (
        <text x={x + 10} y={y + 56} fill="rgba(255,255,255,0.72)" fontSize={10}>
          {payload.metric_label}
        </text>
      )}
    </g>
  );
}

function getMetricLabel(item: MunicipalRow, sortBy: MunicipalSort) {
  if (sortBy === "efficiency") {
    return `Eficiencia ${item.efficiency.toFixed(2)}`;
  }
  if (sortBy === "coverage") {
    return `Cobertura ${formatPercent(item.coverage_pct, 1)}`;
  }
  return `${formatNumber(item.total_votes)} votos`;
}

export function MunicipalTreemap({
  municipalities,
  sortBy,
}: {
  municipalities: MunicipalRow[];
  sortBy: MunicipalSort;
}) {
  if (!municipalities.length) {
    return (
      <div className="panel rounded-3xl p-5">
        <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
          Mapa de rendimiento
        </p>
        <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
          Municipios por votos y señal territorial
        </h3>
        <p className="mt-4 text-sm text-[var(--color-text-secondary)]">
          No hay municipios con votos para renderizar este mapa.
        </p>
      </div>
    );
  }

  const voteValues = municipalities.map((item) => item.total_votes);
  const minVotes = Math.min(...voteValues);
  const maxVotes = Math.max(...voteValues);
  const data: TreemapDatum[] = municipalities.map((item) => ({
    ...item,
    name: item.municipality_name,
    size: Math.max(item.total_votes, 1),
    fill:
      sortBy === "efficiency"
        ? toEfficiencyColor(item.efficiency)
        : sortBy === "coverage"
          ? toCoverageColor(item.coverage_pct)
          : toVotesColor(item.total_votes, minVotes, maxVotes),
    metric_label: getMetricLabel(item, sortBy),
  }));

  return (
    <div className="panel rounded-3xl p-5">
      <div className="mb-5">
        <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
          Mapa de rendimiento
        </p>
        <h3 className="mt-2 text-xl font-bold text-[var(--color-text-primary)]">
          Municipios por votos y señal territorial
        </h3>
      </div>

      <div className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap data={data} dataKey="size" stroke="rgba(255,255,255,0.08)" content={<CustomTreemapCell />}>
            <Tooltip
              contentStyle={{
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 18,
                color: colors.textPrimary,
              }}
              formatter={(_, __, item) => [
                `${formatNumber(item.payload.total_votes)} votos · ${formatPercent(item.payload.coverage_pct, 1)} cobertura`,
                `${item.payload.municipality_name} · ${item.payload.metric_label}`,
              ]}
            />
          </Treemap>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
