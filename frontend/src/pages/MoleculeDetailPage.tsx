import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchMolecule } from "../api/client";
import type { Molecule } from "../types";

export default function MoleculeDetailPage({ chemblId }: { chemblId: string }) {
  const [molecule, setMolecule] = useState<Molecule | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMolecule(chemblId).then(setMolecule).catch((err) => setError(err.message));
  }, [chemblId]);

  if (error) return <div className="rounded-md border border-line bg-white p-5 text-sm">{error}</div>;
  if (!molecule) return <div className="rounded-md border border-line bg-white p-5 text-sm">Loading molecule...</div>;

  return (
    <div className="space-y-5">
      <a href="#" className="inline-flex items-center gap-2 text-sm text-slate-700">
        <ArrowLeft size={16} />
        Back to search
      </a>
      <section className="grid gap-5 rounded-md border border-line bg-white p-5 lg:grid-cols-[360px_1fr]">
        <div className="rounded-md border border-line bg-white p-4" dangerouslySetInnerHTML={{ __html: molecule.svg ?? "" }} />
        <div>
          <h2 className="text-lg font-semibold">{molecule.pref_name || molecule.chembl_id}</h2>
          <p className="font-mono text-xs text-slate-600">{molecule.chembl_id}</p>
          <p className="mt-3 break-all font-mono text-sm">{molecule.canonical_smiles}</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-4">
            <div className="rounded-md border border-line bg-panel p-3"><span className="text-xs text-slate-500">MW</span><br />{molecule.mw?.toFixed(1) ?? "NA"}</div>
            <div className="rounded-md border border-line bg-panel p-3"><span className="text-xs text-slate-500">LogP</span><br />{molecule.clogp?.toFixed(2) ?? "NA"}</div>
            <div className="rounded-md border border-line bg-panel p-3"><span className="text-xs text-slate-500">TPSA</span><br />{molecule.tpsa?.toFixed(1) ?? "NA"}</div>
            <div className="rounded-md border border-line bg-panel p-3"><span className="text-xs text-slate-500">QED</span><br />{molecule.qed?.toFixed(2) ?? "NA"}</div>
          </div>
        </div>
      </section>
      <section className="rounded-md border border-line bg-white p-5">
        <h3 className="mb-3 text-base font-semibold">BRICS Fragments</h3>
        <div className="grid gap-2 md:grid-cols-2">
          {(molecule.fragments ?? []).map((fragment) => (
            <a key={fragment.fragment_id} href={`#/fragments/${fragment.fragment_id}`} className="break-all rounded-md border border-line p-3 font-mono text-xs hover:border-signal">
              {fragment.display_smiles}
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
