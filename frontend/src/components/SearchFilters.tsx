import { SlidersHorizontal } from "lucide-react";
import type { FragmentQuery } from "../types";

type Props = {
  query: FragmentQuery;
  onChange: (query: FragmentQuery) => void;
};

const fields = [
  ["min_count", "Min count"],
  ["min_mw", "Min MW"],
  ["max_mw", "Max MW"],
  ["min_logp", "Min LogP"],
  ["max_logp", "Max LogP"],
  ["min_tpsa", "Min TPSA"],
  ["max_tpsa", "Max TPSA"],
  ["min_hbd", "Min HBD"],
  ["max_hbd", "Max HBD"],
  ["min_hba", "Min HBA"],
  ["max_hba", "Max HBA"],
  ["min_rotb", "Min RotB"],
  ["max_rotb", "Max RotB"],
  ["min_fsp3", "Min Fsp3"],
  ["max_fsp3", "Max Fsp3"],
  ["min_qed", "Min QED"],
  ["max_qed", "Max QED"],
  ["min_admet_measurements", "Min ADMET rows"]
] as const;

const sourceLabels = {
  all: "All fragments",
  tdc: "TDC ADMET",
  chembl: "ChEMBL",
  both: "ChEMBL + TDC"
} as const;

export default function SearchFilters({ query, onChange }: Props) {
  function setNumber(key: keyof FragmentQuery, value: string) {
    onChange({ ...query, [key]: value === "" ? undefined : Number(value), page: 1 });
  }

  return (
    <aside className="border-r border-line bg-slate-50/80 p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-white text-signal shadow-sm ring-1 ring-line">
            <SlidersHorizontal size={17} />
          </span>
          Filters
        </div>
        <button
          className="rounded-md px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-white hover:text-signal"
          type="button"
          onClick={() => onChange({ page: 1, page_size: query.page_size, sort_by: query.sort_by, sort_dir: query.sort_dir, fragment_like: true })}
        >
          Reset
        </button>
      </div>
      <div className="space-y-3">
        <div className="rounded-lg border border-line bg-white p-3 shadow-sm">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Source</div>
          <div className="grid grid-cols-2 gap-1">
            {(Object.keys(sourceLabels) as NonNullable<FragmentQuery["source"]>[]).map((source) => (
              <button
                key={source}
                className={`rounded-md border px-2 py-1.5 text-xs font-semibold transition ${
                  (query.source ?? "all") === source
                    ? "border-signal bg-emerald-50 text-signal"
                    : "border-transparent bg-slate-50 text-slate-600 hover:border-line hover:bg-white"
                }`}
                type="button"
                onClick={() => onChange({ ...query, source, page: 1 })}
              >
                {sourceLabels[source]}
              </button>
            ))}
          </div>
        </div>
        <label className="flex items-start gap-2 rounded-lg border border-line bg-white p-3 text-xs font-medium text-slate-700 shadow-sm">
          <input
            checked={query.fragment_like ?? true}
            className="mt-0.5 h-4 w-4 rounded border-line text-signal"
            type="checkbox"
            onChange={(event) => onChange({ ...query, fragment_like: event.target.checked, page: 1 })}
          />
          <span>
            Fragment-like only
            <span className="mt-1 block font-normal leading-5 text-slate-500">Rule-of-3: MW {"<="} 300, clogP {"<="} 3, HBD {"<="} 3, HBA {"<="} 3, RotB {"<="} 3.</span>
          </span>
        </label>
        <div className="rounded-lg border border-line bg-white p-3 shadow-sm">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Numeric filters</div>
          <div className="grid grid-cols-2 gap-2">
            {fields.map(([key, label]) => (
              <label key={key} className="block text-xs font-medium text-slate-600">
                {label}
                <input
                  className="mt-1 w-full rounded-md border border-line bg-slate-50 px-2 py-1.5 text-sm text-ink outline-none transition focus:border-signal focus:bg-white focus:ring-2 focus:ring-emerald-100"
                  type="number"
                  value={(query[key] as number | undefined) ?? ""}
                  onChange={(event) => setNumber(key, event.target.value)}
                />
              </label>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-5 rounded-lg border border-amber/40 bg-yellow-50 p-3 text-xs leading-5 text-slate-700">
        Physicochemical filters use calculated fragment descriptors. ADMET endpoint statistics are aggregated from molecules containing each fragment.
      </div>
    </aside>
  );
}
