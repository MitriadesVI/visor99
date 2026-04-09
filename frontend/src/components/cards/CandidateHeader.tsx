import type { CandidateSummaryResponse } from "../../api/types";

export function CandidateHeader({ data }: { data: CandidateSummaryResponse }) {
  const territory = data.scope.municipality ?? data.scope.department ?? "Cobertura nacional";

  return (
    <section className="panel relative overflow-hidden rounded-[32px] border border-[var(--color-border)] px-6 py-7">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.24),transparent_32%)]" />
      <div className="relative">
        <p className="text-xs uppercase tracking-[0.35em] text-[var(--color-text-muted)]">
          Visor 99
        </p>
        <h1 className="mt-3 max-w-4xl text-3xl font-extrabold text-[var(--color-text-primary)] md:text-5xl">
          {data.candidate.name}
        </h1>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)] md:text-base">
          {data.candidate.party} · {data.candidate.contest} · {territory}
        </p>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Dataset activo: {data.scope.dataset}
        </p>
      </div>
    </section>
  );
}
