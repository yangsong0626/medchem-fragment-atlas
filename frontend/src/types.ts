export type FragmentRow = {
  fragment_id: string;
  fragment_smiles: string;
  display_smiles: string;
  source?: "ChEMBL" | "TDC" | "ChEMBL+TDC";
  has_chembl?: boolean;
  has_tdc?: boolean;
  is_fragment_like?: boolean;
  fragment_mw?: number | null;
  fragment_clogp?: number | null;
  fragment_tpsa?: number | null;
  fragment_hbd?: number | null;
  fragment_hba?: number | null;
  fragment_rotb?: number | null;
  fragment_fsp3?: number | null;
  fragment_qed?: number | null;
  parent_count: number;
  assay_count: number;
  target_count: number;
  admet_measurement_count: number;
  admet_endpoint_count: number;
  admet_assay_count: number;
  admet_target_count: number;
  tdc_measurement_count?: number;
  tdc_endpoint_count?: number;
  mw_mean: number | null;
  clogp_mean: number | null;
  tpsa_mean: number | null;
  hbd_mean: number | null;
  hba_mean: number | null;
  rotb_mean: number | null;
  fsp3_mean: number | null;
  qed_mean: number | null;
};

export type Molecule = {
  chembl_id: string;
  pref_name?: string | null;
  canonical_smiles: string;
  mw?: number | null;
  clogp?: number | null;
  tpsa?: number | null;
  qed?: number | null;
  svg?: string;
  fragments?: Pick<FragmentRow, "fragment_id" | "fragment_smiles" | "display_smiles">[];
};

export type FragmentDetail = FragmentRow & {
  svg: string;
  representative_molecules: Molecule[];
  property_distributions: Record<string, number[]>;
  representative_parent_ids?: string;
  top_targets?: Array<{ target_chembl_id?: string; target_pref_name?: string }>;
  clean_admet_summary?: Array<{
    source: string;
    standard_type: string;
    standard_units?: string | null;
    measurement_count: number;
    molecule_count: number;
    task_count: number;
    tdc_tasks: string;
    favorable_direction?: "low" | "high" | "neutral";
    description?: string;
    mean?: number | null;
    median?: number | null;
    std?: number | null;
    p10?: number | null;
    p90?: number | null;
  }>;
  admet_summary?: Array<{
    standard_type: string;
    standard_units?: string | null;
    measurement_count: number;
    parent_count: number;
    assay_count: number;
    target_count: number;
    mean?: number | null;
    median?: number | null;
    std?: number | null;
    p10?: number | null;
    p90?: number | null;
  }>;
};

export type CleanAdmetSummaryRow = NonNullable<FragmentDetail["clean_admet_summary"]>[number];

export type CleanAdmetDistribution = {
  fragment_id: string;
  standard_type: string;
  standard_units?: string | null;
  tdc_tasks?: string | null;
  measurement_count: number;
  molecule_count: number;
  mean?: number | null;
  median?: number | null;
  std?: number | null;
  p10?: number | null;
  p90?: number | null;
  min?: number | null;
  max?: number | null;
  histogram: Array<{ bin_start: number; bin_end: number; count: number }>;
  values: number[];
  values_truncated: boolean;
  task_breakdown: Array<{ tdc_task: string; count: number }>;
};

export type FragmentAdmetComparison = {
  fragments: Array<
    Pick<FragmentRow, "fragment_id" | "fragment_smiles" | "display_smiles" | "parent_count" | "admet_measurement_count"> & {
      svg: string;
    }
  >;
  endpoints: Array<{
    standard_type: string;
    standard_units?: string | null;
    tdc_tasks: string;
    domain: { min?: number | null; max?: number | null };
    fragments: Record<
      string,
      {
        count: number;
        min?: number | null;
        q1?: number | null;
        median?: number | null;
        q3?: number | null;
        max?: number | null;
        mean?: number | null;
        std?: number | null;
      }
    >;
  }>;
};

export type FragmentQuery = {
  q?: string;
  source?: "all" | "chembl" | "tdc" | "both";
  fragment_like?: boolean;
  min_count?: number;
  min_mw?: number;
  max_mw?: number;
  min_logp?: number;
  max_logp?: number;
  min_tpsa?: number;
  max_tpsa?: number;
  min_hbd?: number;
  max_hbd?: number;
  min_hba?: number;
  max_hba?: number;
  min_rotb?: number;
  max_rotb?: number;
  min_fsp3?: number;
  max_fsp3?: number;
  min_qed?: number;
  max_qed?: number;
  min_admet_measurements?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
};
