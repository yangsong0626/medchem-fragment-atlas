#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.fragment_service import decompose_brics

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Decompose ChEMBL molecules into canonical BRICS fragments.")
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/molecules.parquet")
    parser.add_argument("--fragments-output", type=Path, default=ROOT / "data/derived/fragments.parquet")
    parser.add_argument("--mapping-output", type=Path, default=ROOT / "data/derived/molecule_fragments.parquet")
    parser.add_argument("--failures-output", type=Path, default=ROOT / "data/derived/fragment_failures.csv")
    parser.add_argument("--min-heavy-atoms", type=int, default=3)
    args = parser.parse_args()

    molecules = pd.read_parquet(args.input)
    fragment_rows: dict[str, dict] = {}
    mapping_rows: list[dict] = []
    failures: list[dict] = []

    for row in molecules.itertuples(index=False):
        chembl_id = str(row.chembl_id)
        smiles = str(row.canonical_smiles)
        try:
            records = decompose_brics(smiles, min_heavy_atoms=args.min_heavy_atoms)
            for record in records:
                fragment_rows[record.fragment_id] = record.__dict__
                mapping_rows.append({"chembl_id": chembl_id, "fragment_id": record.fragment_id, "fragment_smiles": record.fragment_smiles})
        except Exception as exc:
            failures.append({"chembl_id": chembl_id, "canonical_smiles": smiles, "failure": str(exc)})

    for path in [args.fragments_output, args.mapping_output, args.failures_output]:
        path.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(fragment_rows.values()).to_parquet(args.fragments_output, index=False)
    pd.DataFrame(mapping_rows).drop_duplicates().to_parquet(args.mapping_output, index=False)
    pd.DataFrame(failures).to_csv(args.failures_output, index=False)
    print(f"Wrote {len(fragment_rows):,} fragments, {len(mapping_rows):,} mappings, {len(failures):,} failures")


if __name__ == "__main__":
    main()
