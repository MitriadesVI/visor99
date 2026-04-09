import type { DatasetItem, FilterState } from "../../api/types";
import { FilterPanel } from "../filters/FilterPanel";

interface SidebarProps {
  state: FilterState;
  datasets: DatasetItem[];
  contests: string[];
  departments: string[];
  municipalities: string[];
  parties: string[];
  candidates: string[];
  onChange: (field: keyof FilterState, value: string) => void;
}

export function Sidebar(props: SidebarProps) {
  return (
    <aside className="w-full border-b border-[var(--color-border)] p-4 md:sticky md:top-0 md:h-screen md:w-[280px] md:border-b-0 md:border-r md:p-6">
      <div className="panel rounded-[28px] p-5">
        <p className="text-xs uppercase tracking-[0.35em] text-[var(--color-text-muted)]">
          Sala de control
        </p>
        <h2 className="mt-3 text-2xl font-extrabold text-[var(--color-text-primary)]">
          Visor 99
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Ajusta territorio, lista y candidato para refrescar todo el tablero en paralelo.
        </p>

        <div className="mt-6">
          <FilterPanel {...props} />
        </div>
      </div>
    </aside>
  );
}
