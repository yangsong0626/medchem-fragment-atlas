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
const DEMO_MODE = !API_BASE && import.meta.env.PROD && window.location.hostname.endsWith("github.io");
const DEMO_BASE = `${import.meta.env.BASE_URL}demo`;
const DEMO_STRUCTURE_BY_SMILES: Record<string, string> = {
  "[16*]c1ccccc1": "frag_f9875edcde5bb1a4.svg",
  "[6*]C(=O)O": "frag_7f8242582a24a3ae.svg",
  "[16*]c1ccc([16*])cc1": "frag_00c7078885e6f102.svg",
  "[5*]N(C)C": "frag_cddf509caab0ea86.svg",
  "[1*]C(C)=O": "frag_0c9df19e3c60afcf.svg"
};

function params(query: Record<string, string | number | boolean | undefined>) {
  const search = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  return search.toString();
}

function numericFilter(value: number | null | undefined, min?: number, max?: number) {
  if (min === undefined && max === undefined) return true;
  if (value === null || value === undefined) return false;
  return (min === undefined || value >= min) && (max === undefined || value <= max);
}

function demoSvg(smiles: string) {
  const escaped = smiles.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="160" viewBox="0 0 240 160">
    <rect width="240" height="160" rx="14" fill="#ffffff"/>
    <rect x="1" y="1" width="238" height="158" rx="13" fill="none" stroke="#d8e1e8"/>
    <text x="120" y="74" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13" fill="#0f172a">${escaped}</text>
    <text x="120" y="98" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#64748b">static GitHub Pages preview</text>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function demoStructureUrl(smiles: string) {
  const fileName = DEMO_STRUCTURE_BY_SMILES[smiles];
  return fileName ? `${DEMO_BASE}/structures/${fileName}` : demoSvg(smiles);
}

async function demoStructureMarkup(smiles: string) {
  const fileName = DEMO_STRUCTURE_BY_SMILES[smiles];
  if (!fileName) return decodeURIComponent(demoSvg(smiles).replace("data:image/svg+xml;charset=utf-8,", ""));
  const response = await fetch(`${DEMO_BASE}/structures/${fileName}`);
  if (!response.ok) throw new Error("Static fragment structure is unavailable.");
  return response.text();
}

async function fetchDemoFragments(query: FragmentQuery): Promise<{ items: FragmentRow[]; total: number }> {
  const response = await fetch(`${DEMO_BASE}/fragments.json`);
  if (!response.ok) throw new Error("Static demo data is unavailable.");
  const data = (await response.json()) as { items: FragmentRow[] };
  let items = data.items;

  if (query.q) {
    const needle = query.q.toLowerCase();
    items = items.filter((item) => `${item.fragment_smiles} ${item.display_smiles}`.toLowerCase().includes(needle));
  }
  if (query.source === "chembl") items = items.filter((item) => item.has_chembl);
  if (query.source === "tdc") items = items.filter((item) => item.has_tdc);
  if (query.source === "both") items = items.filter((item) => item.has_chembl && item.has_tdc);
  if (query.fragment_like ?? true) items = items.filter((item) => item.is_fragment_like ?? true);

  items = items.filter(
    (item) =>
      (query.min_count === undefined || item.parent_count >= query.min_count) &&
      numericFilter(item.fragment_mw, query.min_mw, query.max_mw) &&
      numericFilter(item.fragment_clogp, query.min_logp, query.max_logp) &&
      numericFilter(item.fragment_tpsa, query.min_tpsa, query.max_tpsa) &&
      numericFilter(item.fragment_hbd, query.min_hbd, query.max_hbd) &&
      numericFilter(item.fragment_hba, query.min_hba, query.max_hba) &&
      numericFilter(item.fragment_rotb, query.min_rotb, query.max_rotb) &&
      numericFilter(item.fragment_fsp3, query.min_fsp3, query.max_fsp3) &&
      numericFilter(item.fragment_qed, query.min_qed, query.max_qed) &&
      (query.min_admet_measurements === undefined || item.admet_measurement_count >= query.min_admet_measurements)
  );

  const sortBy = query.sort_by ?? "parent_count";
  const sortDir = query.sort_dir ?? "desc";
  items = [...items].sort((a, b) => {
    const left = a[sortBy as keyof FragmentRow];
    const right = b[sortBy as keyof FragmentRow];
    if (typeof left === "number" && typeof right === "number") return sortDir === "asc" ? left - right : right - left;
    return sortDir === "asc" ? String(left ?? "").localeCompare(String(right ?? "")) : String(right ?? "").localeCompare(String(left ?? ""));
  });

  const total = items.length;
  const page = query.page ?? 1;
  const pageSize = query.page_size ?? 25;
  const start = (page - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), total };
}

async function demoFragment(fragmentId: string): Promise<FragmentDetail> {
  const data = await fetchDemoFragments({ fragment_like: false, page_size: 100 });
  const fragment = data.items.find((item) => item.fragment_id === fragmentId);
  if (!fragment) throw new Error("Fragment is not included in the static GitHub Pages preview.");
  return {
    ...fragment,
    svg: await demoStructureMarkup(fragment.fragment_smiles),
    representative_molecules: [],
    property_distributions: {},
    clean_admet_summary: [
      {
        source: "static-demo",
        standard_type: "Solubility",
        standard_units: "logS",
        measurement_count: fragment.tdc_measurement_count ?? 0,
        molecule_count: fragment.parent_count,
        task_count: fragment.tdc_endpoint_count ?? 0,
        tdc_tasks: "TDC demo",
        favorable_direction: "high",
        description: "Static preview row; deploy the FastAPI backend for full distributions.",
        median: -3.1,
        mean: -3.0,
        std: 0.8,
        p10: -4.2,
        p90: -1.9
      }
    ]
  };
}

export async function fetchFragments(query: FragmentQuery): Promise<{ items: FragmentRow[]; total: number }> {
  if (DEMO_MODE) return fetchDemoFragments(query);
  const response = await fetch(`${API_BASE}/api/fragments?${params(query)}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchFragment(fragmentId: string): Promise<FragmentDetail> {
  if (DEMO_MODE) return demoFragment(fragmentId);
  const response = await fetch(`${API_BASE}/api/fragments/${fragmentId}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchCleanAdmetDistribution(fragmentId: string, row: CleanAdmetSummaryRow): Promise<CleanAdmetDistribution> {
  if (DEMO_MODE) {
    return {
      fragment_id: fragmentId,
      standard_type: row.standard_type,
      standard_units: row.standard_units,
      tdc_tasks: row.tdc_tasks,
      measurement_count: row.measurement_count,
      molecule_count: row.molecule_count,
      mean: row.mean,
      median: row.median,
      std: row.std,
      p10: row.p10,
      p90: row.p90,
      min: row.p10,
      max: row.p90,
      histogram: [
        { bin_start: -5, bin_end: -4, count: 3 },
        { bin_start: -4, bin_end: -3, count: 9 },
        { bin_start: -3, bin_end: -2, count: 7 },
        { bin_start: -2, bin_end: -1, count: 2 }
      ],
      values: [-4.4, -4.0, -3.7, -3.2, -2.9, -2.5, -2.1],
      values_truncated: false,
      task_breakdown: [{ tdc_task: "Static GitHub Pages preview", count: row.measurement_count }]
    };
  }
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
  if (DEMO_MODE) {
    const data = await fetchDemoFragments({ fragment_like: false, page_size: 100 });
    const fragments = await Promise.all(
      data.items
        .filter((item) => item.fragment_id === fragmentA || item.fragment_id === fragmentB)
        .map(async (item) => ({ ...item, svg: await demoStructureMarkup(item.fragment_smiles) }))
    );
    return { fragments, endpoints: [] };
  }
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
  if (DEMO_MODE) throw new Error("Molecule detail requires the FastAPI backend.");
  const response = await fetch(`${API_BASE}/api/molecules/${chemblId}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function fragmentSvgUrl(smiles: string) {
  if (DEMO_MODE) return demoStructureUrl(smiles);
  return `${API_BASE}/api/render/fragment.svg?${params({ smiles })}`;
}
