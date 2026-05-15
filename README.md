# MedChem Fragment Atlas

MedChem Fragment Atlas builds a searchable medicinal chemistry fragment dictionary from ChEMBL molecules. It uses RDKit BRICS decomposition, stores canonical BRICS fragment SMILES with dummy atoms and attachment labels intact, calculates fragment physicochemical descriptors, and exposes parent-molecule ADMET endpoint statistics through a FastAPI and React dashboard.

The UI caveat is intentional: fragment MW, clogP, TPSA, HBD, HBA, rotatable bonds, Fsp3, and QED are calculated from the BRICS fragment structure. ADMET endpoint values are aggregated from molecules containing a fragment; they are not measured properties of the isolated fragment.

## Stack

- Backend: Python 3.11+, FastAPI, RDKit, pandas, DuckDB, pydantic
- Frontend: React, TypeScript, Vite, TailwindCSS, TanStack Table, Recharts
- Data: Parquet pipeline artifacts and a DuckDB serving database

## Quick Start

```bash
make install
make fragment-sample
```

Run the backend and frontend in two terminals:

```bash
make backend
make frontend
```

Open `http://localhost:5173`.

## Pipeline

The sample CSV in `data/raw/sample_molecules.csv` lets the project run without downloading full ChEMBL.

```bash
source backend/.venv/bin/activate
python backend/scripts/00_prepare_chembl.py --input data/raw/sample_molecules.csv --admet-csv data/raw/sample_admet_measurements.csv
python backend/scripts/01_fragment_chembl.py
python backend/scripts/02_compute_descriptors.py
python backend/scripts/03_aggregate_fragments.py
python backend/scripts/04_build_search_index.py
```

For a real, small ChEMBL prototype without downloading the SQLite release:

```bash
make fetch-prototype PROTOTYPE_LIMIT=1000
make fragment-prototype
```

This fetches approved/late-stage ChEMBL molecules from the public ChEMBL API and pulls ADMET-like activity rows for those parent molecules.

The checked local prototype was built with:

```bash
make fetch-prototype PROTOTYPE_LIMIT=300
make fragment-prototype
```

That produced 300 parent molecules, 408 unique BRICS fragments, 751 molecule-fragment mappings, 3,027 ADMET/activity measurements, and 3,760 fragment ADMET endpoint rollups.

To overlay clean Therapeutics Data Commons ADMET benchmark data:

```bash
make import-tdc-admet
```

This downloads the lightweight ADME/Tox parquet files from the public TDC HuggingFace mirror, decomposes the TDC molecules with the same BRICS settings, and creates `tdc_admet_measurements`, `tdc_fragments`, `tdc_molecule_fragments`, and `tdc_fragment_admet_stats` DuckDB tables. The fragment detail page prefers these clean TDC endpoint statistics for the ADMET heatmap and keeps raw ChEMBL endpoint statistics below for provenance.

To run the publication-strength validation experiments:

```bash
make validation-experiments
```

This adds three manuscript-oriented analyses:

- Bootstrap 95% confidence intervals for fragment-endpoint median ADMET values.
- Matched-context validation, matching TDC parent molecules with and without a fragment within the same task on MW, clogP, TPSA, HBD, HBA, and rotatable bonds.
- Automatically selected case studies combining matched-context effect sizes with bootstrap uncertainty.

The validation script writes DuckDB tables `tdc_fragment_admet_bootstrap_ci`, `tdc_fragment_admet_matched_context`, and `fragment_admet_case_studies`, plus report artifacts under `reports/`.

For full ChEMBL 36, download the official SQLite release and build the atlas:

```bash
make download-chembl36
make fragment-chembl36
```

To use an external disk or a larger scratch volume:

```bash
make download-chembl36 CHEMBL36_DIR=/Volumes/fastdata/chembl_36
make fragment-chembl36 CHEMBL36_DB=/Volumes/fastdata/chembl_36/chembl_36.db
```

The download target uses the official EMBL-EBI release URL:
`https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_36/chembl_36_sqlite.tar.gz`

For other ChEMBL inputs, pass either a ChEMBL SQLite database or a CSV containing `chembl_id`, `canonical_smiles`, `standard_inchi_key`, and optionally `pref_name`.

## ADMET Data

ChEMBL ADMET support is assay-derived. The prep script extracts `assay_type = 'A'` activity rows plus common ADMET-like endpoints such as clearance, solubility, permeability, protein binding, half-life, hepatotoxicity, and hERG. The fragment page reports those measurements as parent-molecule aggregates grouped by endpoint and units. They are not intrinsic fragment ADMET predictions.

## Outputs

- `data/processed/molecules.parquet`
- `data/derived/fragments.parquet`
- `data/derived/molecule_fragments.parquet`
- `data/derived/fragment_failures.csv`
- `data/derived/molecules_with_descriptors.parquet`
- `data/derived/fragment_stats.parquet`
- `data/derived/fragment_admet_stats.parquet`
- `data/derived/tdc_fragment_admet_bootstrap_ci.parquet`
- `data/derived/tdc_fragment_admet_matched_context.parquet`
- `data/derived/fragment_atlas.duckdb`
- `reports/tables/fragment_admet_case_studies.csv`
- `reports/case_studies/fragment_admet_case_studies.md`
- `reports/figures/figure_8_bootstrap_ci.svg`
- `reports/figures/figure_9_matched_context_validation.svg`
- `reports/figures/figure_10_case_study_panels.svg`

## API

- `GET /health`
- `GET /api/fragments`
- `GET /api/fragments/{fragment_id}`
- `GET /api/fragments/{fragment_id}/molecules`
- `GET /api/render/fragment.svg?smiles=...`

## Development

```bash
make test
```

`make test` runs backend smoke/unit tests and builds the frontend.

## GitHub Pages

This repository includes a GitHub Actions workflow at `.github/workflows/pages.yml` that builds the React frontend and deploys it to GitHub Pages on pushes to `main`.

GitHub Pages hosts the static frontend only. The FastAPI backend and DuckDB atlas still need to run separately for live search, SVG rendering, fragment details, and ADMET comparison. For a public deployment, host the backend on a Python-capable service and set the repository variable `VITE_API_BASE` to that backend origin before running the Pages workflow.
