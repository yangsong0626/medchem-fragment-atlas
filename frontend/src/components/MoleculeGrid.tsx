import { fragmentSvgUrl } from "../api/client";
import type { Molecule } from "../types";

function fmt(value: number | null | undefined, digits = 1) {
  return value === null || value === undefined ? "NA" : value.toFixed(digits);
}

export default function MoleculeGrid({ molecules }: { molecules: Molecule[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {molecules.map((molecule) => (
        <a key={molecule.chembl_id} href={`#/molecules/${molecule.chembl_id}`} className="rounded-md border border-line bg-white p-3 hover:border-signal">
          <img className="h-32 w-full rounded border border-line bg-white object-contain" src={fragmentSvgUrl(molecule.canonical_smiles)} alt="" />
          <div className="mt-2 text-sm font-semibold">{molecule.pref_name || molecule.chembl_id}</div>
          <div className="font-mono text-xs text-slate-600">{molecule.chembl_id}</div>
          <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-700">
            <span>MW {fmt(molecule.mw)}</span>
            <span>LogP {fmt(molecule.clogp, 2)}</span>
            <span>QED {fmt(molecule.qed, 2)}</span>
          </div>
        </a>
      ))}
    </div>
  );
}
