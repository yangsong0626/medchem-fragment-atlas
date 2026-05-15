import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchCleanAdmetDistribution, fetchFragment } from "../api/client";
import AdmetHeatmap from "../components/AdmetHeatmap";
import MoleculeGrid from "../components/MoleculeGrid";
import type { CleanAdmetDistribution, CleanAdmetSummaryRow, FragmentDetail } from "../types";

function fmt(value: number | null | undefined, digits = 1) {
  return value === null || value === undefined ? "NA" : value.toFixed(digits);
}

function DistributionPanel({
  distribution,
  loading,
  error
}: {
  distribution: CleanAdmetDistribution | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return <div className="mt-4 rounded-md border border-line bg-panel p-4 text-sm text-slate-600">Loading endpoint distribution...</div>;
  }
  if (error) {
    return <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  }
  if (!distribution) return null;

  const unitLabel = distribution.standard_units || "unitless";
  const histogramData = distribution.histogram.map((bin) => ({
    label: `${fmt(bin.bin_start, 2)}-${fmt(bin.bin_end, 2)}`,
    count: bin.count,
    start: bin.bin_start,
    end: bin.bin_end
  }));

  return (
    <div className="mt-4 rounded-md border border-line bg-panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{distribution.standard_type} Distribution</h3>
          <p className="mt-1 text-xs text-slate-600">
            {distribution.measurement_count} measurements across {distribution.molecule_count} TDC molecules, {unitLabel}.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-right text-xs sm:grid-cols-6">
          {[
            ["Median", distribution.median],
            ["Std", distribution.std],
            ["Mean", distribution.mean],
            ["P10", distribution.p10],
            ["P90", distribution.p90],
            ["Range", distribution.min != null && distribution.max != null ? `${fmt(distribution.min, 2)}-${fmt(distribution.max, 2)}` : "NA"]
          ].map(([label, value]) => (
            <div key={label} className="rounded-md border border-line bg-white px-3 py-2">
              <div className="text-[10px] uppercase text-slate-500">{label}</div>
              <div className="mt-1 font-semibold text-slate-900">{typeof value === "number" ? fmt(value, 2) : value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 h-64 rounded-md border border-line bg-white p-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={histogramData} margin={{ top: 8, right: 12, bottom: 28, left: 8 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              interval="preserveStartEnd"
              minTickGap={18}
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickLine={false}
              axisLine={{ stroke: "#cbd5e1" }}
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} width={36} />
            <Tooltip
              cursor={{ fill: "#eff6ff" }}
              formatter={(value) => [`${value}`, "Measurements"]}
              labelFormatter={(_, payload) => {
                const row = payload?.[0]?.payload;
                return row ? `${fmt(row.start, 3)} to ${fmt(row.end, 3)} ${unitLabel}` : unitLabel;
              }}
            />
            <Bar dataKey="count" fill="#2563eb" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-500">
        <span>{fmt(distribution.min, 2)}</span>
        <span>{unitLabel}</span>
        <span>{fmt(distribution.max, 2)}</span>
      </div>
      {distribution.task_breakdown.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {distribution.task_breakdown.slice(0, 6).map((task) => (
            <span key={task.tdc_task} className="rounded border border-line bg-white px-2 py-1 font-mono">
              {task.tdc_task}: {task.count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FragmentDetailPage({ fragmentId }: { fragmentId: string }) {
  const [fragment, setFragment] = useState<FragmentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCleanAdmet, setSelectedCleanAdmet] = useState<CleanAdmetSummaryRow | null>(null);
  const [distribution, setDistribution] = useState<CleanAdmetDistribution | null>(null);
  const [distributionLoading, setDistributionLoading] = useState(false);
  const [distributionError, setDistributionError] = useState<string | null>(null);

  useEffect(() => {
    setFragment(null);
    setError(null);
    setSelectedCleanAdmet(null);
    setDistribution(null);
    setDistributionError(null);
    fetchFragment(fragmentId).then(setFragment).catch((err) => setError(err.message));
  }, [fragmentId]);

  function showCleanAdmetDistribution(row: CleanAdmetSummaryRow) {
    setSelectedCleanAdmet(row);
    setDistribution(null);
    setDistributionError(null);
    setDistributionLoading(true);
    fetchCleanAdmetDistribution(fragmentId, row)
      .then(setDistribution)
      .catch((err) => setDistributionError(err.message))
      .finally(() => setDistributionLoading(false));
  }

  if (error) return <div className="rounded-xl border border-line bg-white p-5 text-sm shadow-sm">{error}</div>;
  if (!fragment) return <div className="rounded-xl border border-line bg-white p-5 text-sm shadow-sm">Loading fragment...</div>;

  const stats = [
    ["Parents", fragment.parent_count],
    ["ADMET rows", fragment.admet_measurement_count],
    ["ADMET endpoints", fragment.admet_endpoint_count],
    ["ADMET assays", fragment.admet_assay_count],
    ["Targets", fragment.admet_target_count],
    ["Frag MW", fmt(fragment.fragment_mw)],
    ["Frag LogP", fmt(fragment.fragment_clogp, 2)],
    ["Frag TPSA", fmt(fragment.fragment_tpsa)],
    ["Frag QED", fmt(fragment.fragment_qed, 2)]
  ];

  return (
    <div className="space-y-5">
      <a href="#" className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:border-signal hover:text-signal">
        <ArrowLeft size={16} />
        Back to search
      </a>
      <section className="grid gap-5 rounded-xl border border-white/70 bg-white p-5 shadow-xl shadow-slate-200/70 ring-1 ring-slate-900/5 lg:grid-cols-[340px_1fr]">
        <div>
          <div className="rounded-xl border border-line bg-white p-4 shadow-sm" dangerouslySetInnerHTML={{ __html: fragment.svg }} />
          <p className="mt-3 break-all font-mono text-sm">{fragment.display_smiles}</p>
          <p className="mt-1 break-all font-mono text-xs text-slate-500">{fragment.fragment_smiles}</p>
        </div>
        <div>
          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-7">
            {stats.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-line bg-panel p-3 shadow-sm">
                <div className="text-xs uppercase text-slate-500">{label}</div>
                <div className="mt-1 text-xl font-semibold">{value}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg border border-amber/40 bg-yellow-50 p-3 text-sm leading-6 text-slate-700">
            Fragment physicochemical properties are calculated from the BRICS fragment structure. ADMET endpoint statistics are aggregated from molecules containing this fragment.
          </div>
        </div>
      </section>
      {(fragment.clean_admet_summary?.length ?? 0) > 0 && (
        <AdmetHeatmap
          rows={fragment.clean_admet_summary ?? []}
          title="Clean TDC ADMET Heatmap"
          subtitle="Median clean TDC values are scored against endpoint-specific medicinal chemistry desirability targets. Blue means closer to the preferred range, red means less favorable."
        />
      )}
      {(fragment.clean_admet_summary?.length ?? 0) === 0 && (fragment.admet_summary?.length ?? 0) > 0 && <AdmetHeatmap rows={fragment.admet_summary ?? []} />}
      {(fragment.clean_admet_summary?.length ?? 0) > 0 && (
        <section className="rounded-xl border border-line bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-base font-semibold">Clean TDC ADMET Statistics</h2>
          <p className="mb-3 text-sm text-slate-600">Curated TDC benchmark measurements decomposed independently and matched to this BRICS fragment.</p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-panel text-left text-xs uppercase text-slate-600">
                <tr>
                  <th className="border-b border-line px-3 py-2">Endpoint</th>
                  <th className="border-b border-line px-3 py-2">Units</th>
                  <th className="border-b border-line px-3 py-2">Rows</th>
                  <th className="border-b border-line px-3 py-2">Molecules</th>
                  <th className="border-b border-line px-3 py-2">Median</th>
                  <th className="border-b border-line px-3 py-2">P10-P90</th>
                  <th className="border-b border-line px-3 py-2">TDC tasks</th>
                </tr>
              </thead>
              <tbody>
                {fragment.clean_admet_summary?.map((row) => (
                  <tr key={`${row.standard_type}-${row.standard_units}-${row.tdc_tasks}`} className="hover:bg-slate-50">
                    <td className="border-b border-line px-3 py-2">{row.standard_type}</td>
                    <td className="border-b border-line px-3 py-2">{row.standard_units || "NA"}</td>
                    <td className="border-b border-line px-3 py-2">{row.measurement_count}</td>
                    <td className="border-b border-line px-3 py-2">{row.molecule_count}</td>
                    <td className="border-b border-line px-3 py-2">
                      <button
                        className={`rounded px-2 py-1 font-semibold text-blue-700 underline underline-offset-2 hover:bg-blue-50 ${
                          selectedCleanAdmet === row ? "bg-blue-50" : ""
                        }`}
                        type="button"
                        onClick={() => showCleanAdmetDistribution(row)}
                      >
                        {fmt(row.median, 2)}
                      </button>
                    </td>
                    <td className="border-b border-line px-3 py-2">{fmt(row.p10, 2)}-{fmt(row.p90, 2)}</td>
                    <td className="border-b border-line px-3 py-2 font-mono text-xs">{row.tdc_tasks}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <DistributionPanel distribution={distribution} loading={distributionLoading} error={distributionError} />
        </section>
      )}
      {(fragment.admet_summary?.length ?? 0) > 0 && (
        <section className="rounded-md border border-line bg-white p-5">
          <h2 className="mb-3 text-base font-semibold">Raw ChEMBL Endpoint Statistics</h2>
          <p className="mb-3 text-sm text-slate-600">
            These are ChEMBL assay measurements from parent molecules containing this fragment, grouped by endpoint and units.
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-panel text-left text-xs uppercase text-slate-600">
                <tr>
                  <th className="border-b border-line px-3 py-2">Endpoint</th>
                  <th className="border-b border-line px-3 py-2">Units</th>
                  <th className="border-b border-line px-3 py-2">Rows</th>
                  <th className="border-b border-line px-3 py-2">Parents</th>
                  <th className="border-b border-line px-3 py-2">Mean</th>
                  <th className="border-b border-line px-3 py-2">Median</th>
                  <th className="border-b border-line px-3 py-2">P10-P90</th>
                </tr>
              </thead>
              <tbody>
                {fragment.admet_summary?.map((row) => (
                  <tr key={`${row.standard_type}-${row.standard_units}`} className="hover:bg-slate-50">
                    <td className="border-b border-line px-3 py-2">{row.standard_type}</td>
                    <td className="border-b border-line px-3 py-2">{row.standard_units || "NA"}</td>
                    <td className="border-b border-line px-3 py-2">{row.measurement_count}</td>
                    <td className="border-b border-line px-3 py-2">{row.parent_count}</td>
                    <td className="border-b border-line px-3 py-2">{fmt(row.mean, 2)}</td>
                    <td className="border-b border-line px-3 py-2">{fmt(row.median, 2)}</td>
                    <td className="border-b border-line px-3 py-2">{fmt(row.p10, 2)}-{fmt(row.p90, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {(fragment.admet_summary?.length ?? 0) === 0 && (
        <section className="rounded-md border border-line bg-white p-5 text-sm text-slate-600">
          No ChEMBL endpoint statistics are available for this fragment in the current prototype dataset.
        </section>
      )}
      <section>
        <h2 className="mb-3 text-base font-semibold">Representative Parent Molecules</h2>
        <MoleculeGrid molecules={fragment.representative_molecules ?? []} />
      </section>
      {(fragment.top_targets?.length ?? 0) > 0 && (
        <section className="rounded-md border border-line bg-white p-5">
          <h2 className="mb-3 text-base font-semibold">Top Targets</h2>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {fragment.top_targets?.map((target) => (
              <div key={target.target_chembl_id} className="rounded-md border border-line p-3 text-sm">
                <div className="font-semibold">{target.target_pref_name || target.target_chembl_id}</div>
                <div className="font-mono text-xs text-slate-500">{target.target_chembl_id}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
