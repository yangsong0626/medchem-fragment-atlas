import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { ArrowDownUp } from "lucide-react";
import { fragmentSvgUrl } from "../api/client";
import type { FragmentRow } from "../types";

type Props = {
  rows: FragmentRow[];
  sortBy: string;
  sortDir: "asc" | "desc";
  onSort: (column: string) => void;
  selectedIds?: string[];
  onToggleCompare?: (fragment: FragmentRow) => void;
};

function fmt(value: number | null | undefined, digits = 1) {
  return value === null || value === undefined ? "NA" : value.toFixed(digits);
}

const helper = createColumnHelper<FragmentRow>();

function sourceClass(source: string | undefined) {
  if (source === "ChEMBL+TDC") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (source === "TDC") return "border-blue-200 bg-blue-50 text-blue-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export default function FragmentTable({ rows, sortBy, sortDir, onSort, selectedIds = [], onToggleCompare }: Props) {
  const columns = [
    helper.display({
      id: "compare",
      header: "Compare",
      cell: (info) => {
        const selected = selectedIds.includes(info.row.original.fragment_id);
        const disabled = !selected && selectedIds.length >= 2;
        return (
          <input
            aria-label={`Compare ${info.row.original.display_smiles}`}
            checked={selected}
            className="h-4 w-4 rounded border-line text-signal accent-emerald-700"
            disabled={disabled}
            type="checkbox"
            onChange={() => onToggleCompare?.(info.row.original)}
          />
        );
      }
    }),
    helper.accessor("fragment_smiles", {
      header: "Fragment",
      cell: (info) => (
        <a href={`#/fragments/${info.row.original.fragment_id}`} className="group flex items-center gap-3">
          <img className="h-16 w-24 rounded-lg border border-line bg-white object-contain shadow-sm transition group-hover:border-signal" src={fragmentSvgUrl(info.getValue())} alt="" />
          <span className="max-w-[320px]">
            <span className="block break-all font-mono text-xs text-slate-900 group-hover:text-signal">{info.row.original.display_smiles}</span>
          </span>
        </a>
      )
    }),
    helper.accessor("source", {
      header: "Source",
      cell: (info) => <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${sourceClass(info.getValue())}`}>{info.getValue() ?? "ChEMBL"}</span>
    }),
    helper.accessor("parent_count", { header: "Parents", cell: (info) => info.getValue() }),
    helper.accessor("tdc_measurement_count", { header: "TDC rows", cell: (info) => info.getValue() ?? 0 }),
    helper.accessor("tdc_endpoint_count", { header: "TDC endpoints", cell: (info) => info.getValue() ?? 0 }),
    helper.accessor("fragment_mw", { header: "Frag MW", cell: (info) => fmt(info.getValue()) }),
    helper.accessor("fragment_clogp", { header: "Frag LogP", cell: (info) => fmt(info.getValue(), 2) }),
    helper.accessor("fragment_tpsa", { header: "Frag TPSA", cell: (info) => fmt(info.getValue()) }),
    helper.accessor("fragment_hbd", { header: "Frag HBD", cell: (info) => fmt(info.getValue(), 0) }),
    helper.accessor("fragment_hba", { header: "Frag HBA", cell: (info) => fmt(info.getValue(), 0) }),
    helper.accessor("fragment_rotb", { header: "Frag RotB", cell: (info) => fmt(info.getValue(), 0) }),
    helper.accessor("fragment_fsp3", { header: "Frag Fsp3", cell: (info) => fmt(info.getValue(), 2) }),
    helper.accessor("fragment_qed", { header: "Frag QED", cell: (info) => fmt(info.getValue(), 2) }),
    helper.accessor("assay_count", { header: "Assays", cell: (info) => info.getValue() }),
    helper.accessor("target_count", { header: "Targets", cell: (info) => info.getValue() }),
    helper.accessor("admet_measurement_count", { header: "ADMET rows", cell: (info) => info.getValue() }),
    helper.accessor("admet_endpoint_count", { header: "ADMET endpoints", cell: (info) => info.getValue() })
  ];

  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() });

  return (
    <div className="overflow-x-auto bg-white">
      <table className="min-w-full border-separate border-spacing-0 text-sm">
        <thead className="sticky top-0 z-10 bg-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-600">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const key = header.column.id;
                const sortable = key !== "assay_count" && key !== "target_count" && key !== "compare";
                return (
                  <th key={header.id} className="border-b border-line px-3 py-3 font-semibold">
                    <button
                      disabled={!sortable}
                      className="inline-flex whitespace-nowrap items-center gap-1 disabled:cursor-default"
                      onClick={() => sortable && onSort(key === "fragment_smiles" ? "fragment_smiles" : key)}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sortable && <ArrowDownUp size={13} className={sortBy === key ? "text-signal" : "text-slate-400"} />}
                      {sortBy === key && <span className="sr-only">{sortDir}</span>}
                    </button>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="transition hover:bg-emerald-50/40">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="border-b border-line px-3 py-2.5 align-middle text-slate-700">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
