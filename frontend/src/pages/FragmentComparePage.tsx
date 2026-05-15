import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchFragmentAdmetComparison } from "../api/client";
import type { FragmentAdmetComparison } from "../types";

function fmt(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "NA";
  if (Math.abs(value) >= 100) return value.toFixed(0);
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(digits);
}

type BoxStats = FragmentAdmetComparison["endpoints"][number]["fragments"][string];

function BoxGlyph({
  stats,
  domainMin,
  domainMax,
  color
}: {
  stats: BoxStats;
  domainMin: number;
  domainMax: number;
  color: string;
}) {
  if (!stats || stats.count === 0 || stats.min == null || stats.max == null || stats.q1 == null || stats.q3 == null || stats.median == null) {
    return <div className="grid h-16 place-items-center rounded border border-dashed border-line text-xs text-slate-500">No data</div>;
  }
  const span = domainMax === domainMin ? 1 : domainMax - domainMin;
  const x = (value: number) => `${Math.max(0, Math.min(100, ((value - domainMin) / span) * 100))}%`;
  const boxLeft = x(stats.q1);
  const boxWidth = `${Math.max(1, ((stats.q3 - stats.q1) / span) * 100)}%`;

  return (
    <div className="relative h-16 rounded border border-line bg-white px-3">
      <div className="absolute left-3 right-3 top-1/2 h-px bg-slate-300" />
      <div className="absolute top-[21px] h-5 rounded-sm border-2 bg-white" style={{ left: boxLeft, width: boxWidth, borderColor: color }} />
      <div className="absolute top-[18px] h-8 w-px" style={{ left: x(stats.min), backgroundColor: color }} />
      <div className="absolute top-[18px] h-8 w-px" style={{ left: x(stats.max), backgroundColor: color }} />
      <div className="absolute top-[15px] h-11 w-0.5" style={{ left: x(stats.median), backgroundColor: color }} />
      {stats.mean != null && <div className="absolute top-[27px] h-3 w-3 -translate-x-1.5 rounded-full border-2 bg-white" style={{ left: x(stats.mean), borderColor: color }} />}
    </div>
  );
}

function EndpointBoxPlot({
  endpoint,
  fragmentIds
}: {
  endpoint: FragmentAdmetComparison["endpoints"][number];
  fragmentIds: string[];
}) {
  const statsA = endpoint.fragments[fragmentIds[0]];
  const statsB = endpoint.fragments[fragmentIds[1]];
  const domainMin = Math.min(statsA?.min ?? 0, statsB?.min ?? 0, endpoint.domain.min ?? 0);
  const domainMax = Math.max(statsA?.max ?? 1, statsB?.max ?? 1, endpoint.domain.max ?? 1);
  const unit = endpoint.standard_units || "unitless";

  return (
    <section className="rounded-xl border border-line bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{endpoint.standard_type}</h2>
          <p className="mt-1 text-xs text-slate-600">
            {unit} | {endpoint.tdc_tasks}
          </p>
        </div>
        <div className="rounded-md border border-line bg-panel px-2 py-1 text-xs text-slate-500">
          axis {fmt(domainMin)} to {fmt(domainMax)}
        </div>
      </div>

      <div className="space-y-3">
        {fragmentIds.map((fragmentId, index) => {
          const stats = endpoint.fragments[fragmentId];
          const color = index === 0 ? "#2563eb" : "#c43c39";
          return (
            <div key={fragmentId} className="grid gap-2 lg:grid-cols-[150px_1fr_360px] lg:items-center">
              <div className="text-xs font-semibold text-slate-700">Fragment {index + 1}</div>
              <BoxGlyph stats={stats} domainMin={domainMin} domainMax={domainMax} color={color} />
              <div className="grid grid-cols-4 gap-2 text-xs sm:grid-cols-8 lg:grid-cols-4 xl:grid-cols-8">
                {[
                  ["n", stats?.count],
                  ["min", stats?.min],
                  ["Q1", stats?.q1],
                  ["median", stats?.median],
                  ["Q3", stats?.q3],
                  ["max", stats?.max],
                  ["mean", stats?.mean],
                  ["std", stats?.std]
                ].map(([label, value]) => (
                  <div key={label} className="rounded border border-line bg-panel px-2 py-1">
                    <div className="text-[10px] uppercase text-slate-500">{label}</div>
                    <div className="font-semibold">{typeof value === "number" ? fmt(value) : value ?? "NA"}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function FragmentComparePage({ fragmentA, fragmentB }: { fragmentA: string; fragmentB: string }) {
  const [comparison, setComparison] = useState<FragmentAdmetComparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setComparison(null);
    setError(null);
    fetchFragmentAdmetComparison(fragmentA, fragmentB)
      .then(setComparison)
      .catch((err) => setError(err.message));
  }, [fragmentA, fragmentB]);

  if (error) return <div className="rounded-xl border border-line bg-white p-5 text-sm shadow-sm">{error}</div>;
  if (!comparison) return <div className="rounded-xl border border-line bg-white p-5 text-sm shadow-sm">Loading ADMET comparison...</div>;

  const fragmentIds = comparison.fragments.map((fragment) => fragment.fragment_id);

  return (
    <div className="space-y-5">
      <a href="#" className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:border-signal hover:text-signal">
        <ArrowLeft size={16} />
        Back to search
      </a>

      <section className="rounded-xl border border-white/70 bg-slate-950 p-5 text-white shadow-xl shadow-slate-200/70 ring-1 ring-slate-900/5">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-xl font-semibold">Fragment ADMET Comparison</h1>
            <p className="mt-1 text-sm text-slate-300">
              Box plots use clean TDC parent-molecule endpoint distributions for molecules containing each BRICS fragment.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-300">
            <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm bg-blue-600" /> Fragment 1</span>
            <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm bg-red-600" /> Fragment 2</span>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {comparison.fragments.map((fragment, index) => (
          <div key={fragment.fragment_id} className="rounded-xl border border-line bg-white p-4 shadow-sm">
            <div className="mb-2 text-xs font-semibold uppercase text-slate-500">Fragment {index + 1}</div>
            <div className="rounded-xl border border-line bg-white p-3 shadow-sm" dangerouslySetInnerHTML={{ __html: fragment.svg }} />
            <a className="mt-3 block break-all font-mono text-sm text-blue-700 underline underline-offset-2" href={`#/fragments/${fragment.fragment_id}`}>
              {fragment.display_smiles}
            </a>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg border border-line bg-panel p-2">
                <div className="uppercase text-slate-500">Parents</div>
                <div className="font-semibold">{fragment.parent_count}</div>
              </div>
              <div className="rounded-lg border border-line bg-panel p-2">
                <div className="uppercase text-slate-500">ADMET rows</div>
                <div className="font-semibold">{fragment.admet_measurement_count}</div>
              </div>
            </div>
          </div>
        ))}
      </section>

      {comparison.endpoints.length === 0 ? (
        <section className="rounded-md border border-line bg-white p-5 text-sm text-slate-600">
          No shared clean TDC ADMET endpoints were found for these two fragments.
        </section>
      ) : (
        <div className="space-y-4">
          {comparison.endpoints.map((endpoint) => (
            <EndpointBoxPlot
              key={`${endpoint.standard_type}-${endpoint.standard_units}-${endpoint.tdc_tasks}`}
              endpoint={endpoint}
              fragmentIds={fragmentIds}
            />
          ))}
        </div>
      )}
    </div>
  );
}
