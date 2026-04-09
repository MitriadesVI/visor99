import type { DatasetItem, FilterState } from "../../api/types";

interface FilterPanelProps {
  state: FilterState;
  datasets: DatasetItem[];
  contests: string[];
  departments: string[];
  municipalities: string[];
  parties: string[];
  candidates: string[];
  onChange: (field: keyof FilterState, value: string) => void;
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-[11px] uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-accent)]"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function FilterPanel({
  state,
  datasets,
  contests,
  departments,
  municipalities,
  parties,
  candidates,
  onChange,
}: FilterPanelProps) {
  return (
    <div className="space-y-5">
      <div>
        <p className="text-[11px] uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
          Dataset
        </p>
        <select
          value={state.dataset}
          onChange={(event) => onChange("dataset", event.target.value)}
          className="mt-2 w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-text-primary)] outline-none transition focus:border-[var(--color-accent)]"
        >
          {datasets.map((dataset) => (
            <option key={dataset.path} value={dataset.path}>
              {dataset.path}
            </option>
          ))}
        </select>
      </div>

      <SelectField label="Concurso" value={state.contest} options={contests} onChange={(value) => onChange("contest", value)} />
      <SelectField label="Departamento" value={state.department} options={departments} onChange={(value) => onChange("department", value)} />
      <SelectField label="Municipio" value={state.municipality} options={municipalities} onChange={(value) => onChange("municipality", value)} />
      <SelectField label="Partido / lista" value={state.party} options={parties} onChange={(value) => onChange("party", value)} />
      <SelectField label="Candidato" value={state.candidate} options={candidates} onChange={(value) => onChange("candidate", value)} />
    </div>
  );
}
