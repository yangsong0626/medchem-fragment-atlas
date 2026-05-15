import type {
  CleanAdmetDistribution,
  CleanAdmetSummaryRow,
  FragmentAdmetComparison,
  FragmentDetail,
  FragmentQuery,
  FragmentRow,
  Molecule
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function params(query: Record<string, string | number | boolean | undefined>) {
  const search = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  return search.toString();
}

export async function fetchFragments(query: FragmentQuery): Promise<{ items: FragmentRow[]; total: number }> {
  const response = await fetch(`${API_BASE}/api/fragments?${params(query)}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchFragment(fragmentId: string): Promise<FragmentDetail> {
  const response = await fetch(`${API_BASE}/api/fragments/${fragmentId}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchCleanAdmetDistribution(fragmentId: string, row: CleanAdmetSummaryRow): Promise<CleanAdmetDistribution> {
  const response = await fetch(
    `${API_BASE}/api/fragments/${fragmentId}/clean-admet-distribution?${params({
      standard_type: row.standard_type,
      standard_units: row.standard_units ?? "",
      tdc_tasks: row.tdc_tasks
    })}`
  );
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchFragmentAdmetComparison(fragmentA: string, fragmentB: string): Promise<FragmentAdmetComparison> {
  const response = await fetch(
    `${API_BASE}/api/fragments/compare/admet?${params({
      fragment_a: fragmentA,
      fragment_b: fragmentB
    })}`
  );
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchMolecule(chemblId: string): Promise<Molecule> {
  const response = await fetch(`${API_BASE}/api/molecules/${chemblId}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function fragmentSvgUrl(smiles: string) {
  return `${API_BASE}/api/render/fragment.svg?${params({ smiles })}`;
}
