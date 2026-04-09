import type { ZoneSummary } from "../../api/types";
import { formatCompact, formatPercent } from "../../utils/format";

export function ZoneCard({ zone }: { zone: ZoneSummary }) {
  return (
    <div className="panel rounded-3xl p-4 transition hover:-translate-y-0.5 hover:bg-[var(--color-surface-hover)]">
      <p className="text-xs uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
        {zone.zone_label}
      </p>
      <h3 className="mt-2 text-lg font-bold text-[var(--color-text-primary)]">
        {zone.municipality_name}
      </h3>
      <p className="mt-1 font-mono text-2xl font-bold text-[var(--color-accent)]">
        {formatCompact(zone.votes)}
      </p>
      <div className="mt-4 flex items-center justify-between text-sm text-[var(--color-text-secondary)]">
        <span>{formatPercent(zone.participation, 2)} de la zona</span>
        <span>{zone.tables} mesas</span>
      </div>
    </div>
  );
}
