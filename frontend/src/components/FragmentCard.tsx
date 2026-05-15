import { ExternalLink } from "lucide-react";
import { fragmentSvgUrl } from "../api/client";
import type { FragmentRow } from "../types";

function fmt(value: number | null | undefined, digits = 1) {
  return value === null || value === undefined ? "NA" : value.toFixed(digits);
}

export default function FragmentCard({ fragment }: { fragment: FragmentRow }) {
  return (
    <a href={`#/fragments/${fragment.fragment_id}`} className="block rounded-xl border border-line bg-white p-3 shadow-sm transition hover:border-signal hover:shadow-md">
      <div className="flex gap-3">
        <img className="h-24 w-36 rounded-lg border border-line bg-white object-contain shadow-sm" src={fragmentSvgUrl(fragment.fragment_smiles)} alt="" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="break-all font-mono text-xs text-ink">{fragment.display_smiles}</p>
              <span className="mt-1 inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-800">
                {fragment.source ?? "ChEMBL"}
              </span>
            </div>
            <ExternalLink size={15} className="shrink-0 text-slate-500" />
          </div>
          <div className="mt-3 grid grid-cols-4 gap-2 text-xs text-slate-600">
            <span className="rounded-md bg-panel p-2"><b className="text-slate-950">{fragment.parent_count}</b><br />parents</span>
            <span className="rounded-md bg-panel p-2"><b className="text-slate-950">{fragment.tdc_measurement_count ?? 0}</b><br />TDC rows</span>
            <span className="rounded-md bg-panel p-2"><b className="text-slate-950">{fmt(fragment.fragment_mw)}</b><br />Frag MW</span>
            <span className="rounded-md bg-panel p-2"><b className="text-slate-950">{fmt(fragment.fragment_clogp, 2)}</b><br />Frag LogP</span>
          </div>
        </div>
      </div>
    </a>
  );
}
