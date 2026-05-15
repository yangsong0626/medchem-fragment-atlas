# Backend

FastAPI and ETL pipeline for the MedChem Fragment Atlas.

## Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

RDKit is available on PyPI for common platforms. If your platform has trouble resolving wheels, install it through conda-forge and then install the remaining dependencies with pip.

## Pipeline

From the project root:

```bash
source backend/.venv/bin/activate
python backend/scripts/00_prepare_chembl.py --input data/raw/sample_molecules.csv --admet-csv data/raw/sample_admet_measurements.csv
python backend/scripts/01_fragment_chembl.py
python backend/scripts/02_compute_descriptors.py
python backend/scripts/03_aggregate_fragments.py
python backend/scripts/04_build_search_index.py
```

The scripts keep BRICS dummy atoms in `fragment_smiles` and create a normalized `display_smiles` for UI display.

For ChEMBL 36:

```bash
make download-chembl36
make fragment-chembl36
```

ADMET measurements are extracted from ChEMBL assays as parent-molecule observations and then summarized per fragment. They are not treated as isolated-fragment ADMET predictions.

## Validation Experiments

After importing clean TDC ADMET data, run:

```bash
make validation-experiments
```

This script performs three manuscript-supporting analyses:

- Bootstrap 95% confidence intervals for fragment-endpoint medians.
- Matched-context validation using nearest-neighbor controls from the same TDC task, matched on simple RDKit descriptors.
- Case-study table, narrative Markdown, and SVG figures for publication drafting.

Outputs are written to `data/derived/`, `reports/tables/`, `reports/case_studies/`, and `reports/figures/`, and the main DuckDB database receives corresponding tables for downstream analysis.

## API

```bash
cd backend
uvicorn app.main:app --reload
```

Key routes:

- `GET /health`
- `GET /api/fragments`
- `GET /api/fragments/{fragment_id}`
- `GET /api/fragments/{fragment_id}/molecules`
- `GET /api/render/fragment.svg?smiles=...`
