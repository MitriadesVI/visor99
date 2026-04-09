import { formatNumber, formatPercent } from "../../utils/format";

interface StatCardProps {
  label: string;
  value: number;
  tone?: "neutral" | "accent" | "green" | "amber";
  suffix?: "number" | "percent";
}

const toneMap = {
  neutral: "text-[var(--color-text-primary)]",
  accent: "text-[var(--color-accent)]",
  green: "text-[var(--color-green)]",
  amber: "text-[var(--color-amber)]",
};

export function StatCard({ label, value, tone = "neutral", suffix = "number" }: StatCardProps) {
  return (
    <div className="panel rounded-3xl p-5">
      <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--color-text-muted)]">
        {label}
      </p>
      <p className={`mt-3 font-mono text-3xl font-bold ${toneMap[tone]}`}>
        {suffix === "percent" ? formatPercent(value) : formatNumber(value)}
      </p>
    </div>
  );
}
