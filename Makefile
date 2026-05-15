CHEMBL36_DIR ?= data/raw/chembl_36
CHEMBL36_DB ?= $(CHEMBL36_DIR)/chembl_36.db
PROTOTYPE_LIMIT ?= 1000

.PHONY: install backend frontend download-chembl36 fetch-prototype fragment-sample fragment-prototype fragment-chembl36 import-tdc-admet validation-experiments ml-solubility-ablation figures manuscript test

install:
	cd backend && python3 -m venv .venv
	cd backend && . .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -e ".[dev]"
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

download-chembl36:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/99_download_chembl36.py --output-dir $(CHEMBL36_DIR) --link-path $(CHEMBL36_DB)

fetch-prototype:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/98_fetch_chembl_prototype.py --molecule-limit $(PROTOTYPE_LIMIT)

fragment-sample:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/00_prepare_chembl.py --input data/raw/sample_molecules.csv --admet-csv data/raw/sample_admet_measurements.csv
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/01_fragment_chembl.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/02_compute_descriptors.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/03_aggregate_fragments.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/04_build_search_index.py

fragment-prototype:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/00_prepare_chembl.py --input data/raw/chembl_prototype_molecules.csv --admet-csv data/raw/chembl_prototype_admet.csv
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/01_fragment_chembl.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/02_compute_descriptors.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/03_aggregate_fragments.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/04_build_search_index.py

fragment-chembl36:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/00_prepare_chembl.py --input $(CHEMBL36_DB)
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/01_fragment_chembl.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/02_compute_descriptors.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/03_aggregate_fragments.py
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/04_build_search_index.py

import-tdc-admet:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/06_import_tdc_admet.py

validation-experiments:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/07_validation_experiments.py

ml-solubility-ablation:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/09_ml_solubility_fragment_features.py

figures:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/05_generate_figures.py

manuscript:
	cd backend && . .venv/bin/activate && cd .. && python backend/scripts/08_export_manuscript_summary.py
	mkdir -p reports/figures/png
	for f in reports/figures/*.svg; do base=$$(basename "$$f" .svg); magick -density 180 "$$f" -background white -alpha remove -alpha off "reports/figures/png/$${base}.png"; done
	cp reports/figures/figure_7_web_interface.png reports/figures/png/figure_7_web_interface.png
	/Users/songyang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 reports/build_preprint_docx.py

test:
	cd backend && . .venv/bin/activate && pytest
	cd frontend && npm run build
