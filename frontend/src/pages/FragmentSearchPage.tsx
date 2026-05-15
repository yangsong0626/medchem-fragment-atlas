import { GitCompareArrows, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchFragments } from "../api/client";
import FragmentCard from "../components/FragmentCard";
import FragmentTable from "../components/FragmentTable";
import SearchFilters from "../components/SearchFilters";
import type { FragmentQuery, FragmentRow } from "../types";

export default function FragmentSearchPage() {
  const [query, setQuery] = useState<FragmentQuery>({ page: 1, page_size: 25, sort_by: "parent_count", sort_dir: "desc" });
  const [rows, setRows] = useState<FragmentRow[]>([]);
  const [compareSelection, setCompareSelection] = useState<FragmentRow[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchFragments(query)
      .then((data) => {
        setRows(data.items);
        setTotal(data.total);
        setError(null);
      })
      .catch((err) => setError(err.message));
  }, [query]);

  function sort(column: string) {
    setQuery((prev) => ({
      ...prev,
      sort_by: column,
      sort_dir: prev.sort_by === column && prev.sort_dir === "desc" ? "asc" : "desc"
    }));
  }

  function toggleCompare(fragment: FragmentRow) {
    setCompareSelection((prev) => {
      if (prev.some((item) => item.fragment_id === fragment.fragment_id)) {
        return prev.filter((item) => item.fragment_id !== fragment.fragment_id);
      }
      return prev.length >= 2 ? prev : [...prev, fragment];
    });
  }

  const compareHref =
    compareSelection.length === 2 ? `#/compare/${compareSelection[0].fragment_id}/${compareSelection[1].fragment_id}` : "#";
  const sourceLabel = query.source === "chembl" ? "ChEMBL" : query.source === "tdc" ? "TDC" : query.source === "both" ? "ChEMBL+TDC" : "All";

  return (
    <div className="overflow-hidden rounded-xl border border-white/70 bg-white shadow-xl shadow-slate-200/70 ring-1 ring-slate-900/5">
      <div className="border-b border-line bg-slate-950 px-5 py-4 text-white">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Fragment dictionary</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-normal">Search and compare ADMET-associated fragments</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-300">
              Filter Rule-of-3 fragments, inspect clean TDC endpoint statistics, and compare two motifs with side-by-side ADMET box plots.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-right sm:grid-cols-3">
            <div className="rounded-lg border border-white/10 bg-white/10 px-3 py-2">
              <div className="text-[10px] uppercase tracking-wide text-slate-300">Visible</div>
              <div className="text-xl font-semibold">{total.toLocaleString()}</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/10 px-3 py-2">
              <div className="text-[10px] uppercase tracking-wide text-slate-300">Mode</div>
              <div className="text-sm font-semibold">{query.fragment_like ?? true ? "Fragment-like" : "All BRICS"}</div>
            </div>
            <div className="hidden rounded-lg border border-white/10 bg-white/10 px-3 py-2 sm:block">
              <div className="text-[10px] uppercase tracking-wide text-slate-300">Source</div>
              <div className="text-sm font-semibold">{sourceLabel}</div>
            </div>
          </div>
        </div>
      </div>
      <div className="grid min-h-[720px] lg:grid-cols-[290px_1fr]">
      <SearchFilters query={query} onChange={setQuery} />
      <section className="min-w-0 bg-white">
        <div className="border-b border-line bg-white p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <label className="relative block flex-1">
              <Search className="absolute left-3 top-3 text-slate-500" size={18} />
              <input
                className="w-full rounded-lg border border-line bg-slate-50 py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-signal focus:bg-white focus:ring-4 focus:ring-emerald-100"
                placeholder="Search fragment SMILES or attachment patterns"
                value={query.q ?? ""}
                onChange={(event) => setQuery({ ...query, q: event.target.value, page: 1 })}
              />
            </label>
            <div className="rounded-md border border-line bg-panel px-3 py-2 text-sm font-semibold text-slate-700">{total.toLocaleString()} fragments</div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-line bg-panel p-2 text-sm">
            <span className="inline-flex items-center gap-2 rounded-md bg-white px-2 py-1 font-semibold text-slate-700 shadow-sm">
              <GitCompareArrows size={15} />
              Compare
            </span>
            {compareSelection.length === 0 && <span className="px-1 text-slate-500">Select two fragments from the table</span>}
            {compareSelection.map((fragment) => (
              <button
                key={fragment.fragment_id}
                className="inline-flex max-w-[280px] items-center gap-2 rounded-md border border-emerald-200 bg-white px-2 py-1 font-mono text-xs text-slate-800 shadow-sm hover:border-signal"
                type="button"
                onClick={() => toggleCompare(fragment)}
              >
                <span className="truncate">{fragment.display_smiles}</span>
                <X size={13} />
              </button>
            ))}
            <a
              className={`ml-auto inline-flex items-center gap-2 rounded-md px-3 py-1.5 font-semibold shadow-sm transition ${
                compareSelection.length === 2 ? "bg-signal text-white hover:bg-emerald-800" : "cursor-not-allowed bg-slate-200 text-slate-500 shadow-none"
              }`}
              href={compareHref}
              onClick={(event) => {
                if (compareSelection.length !== 2) event.preventDefault();
              }}
            >
              <GitCompareArrows size={15} />
              Compare ADMET
            </a>
          </div>
        </div>
        {error ? (
          <div className="m-4 rounded-md border border-amber/40 bg-yellow-50 p-4 text-sm text-slate-700">
            {error.includes("503") ? "Build the sample atlas with `make fragment-sample` before searching." : error}
          </div>
        ) : (
          <>
            <div className="grid gap-3 p-4 lg:hidden">
              {rows.map((fragment) => <FragmentCard key={fragment.fragment_id} fragment={fragment} />)}
            </div>
            <div className="hidden lg:block">
              <FragmentTable
                rows={rows}
                sortBy={query.sort_by ?? "parent_count"}
                sortDir={query.sort_dir ?? "desc"}
                selectedIds={compareSelection.map((fragment) => fragment.fragment_id)}
                onSort={sort}
                onToggleCompare={toggleCompare}
              />
            </div>
          </>
        )}
      </section>
      </div>
    </div>
  );
}
