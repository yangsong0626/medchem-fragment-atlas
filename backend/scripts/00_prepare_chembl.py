#!/usr/bin/env python
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.molecule_service import normalize_molecule_columns

ROOT = Path(__file__).resolve().parents[2]
ADMET_STANDARD_TYPES = [
    "AUC",
    "BA",
    "CL",
    "Caco-2",
    "Clearance",
    "F",
    "F%",
    "Fu",
    "Half-life",
    "Hepatotoxicity",
    "LD50",
    "LogD",
    "PPB",
    "PAMPA",
    "Pgp",
    "Solubility",
    "T1/2",
    "VDss",
    "hERG",
    "t1/2",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def read_chembl_sqlite(path: Path) -> pd.DataFrame:
    query = """
    select
      md.chembl_id,
      cs.canonical_smiles,
      cs.standard_inchi_key,
      md.pref_name,
      cp.full_mwt as mw,
      cp.alogp as clogp,
      cp.psa as tpsa,
      cp.hbd,
      cp.hba,
      cp.rtb as rotb
    from molecule_dictionary md
    join compound_structures cs on md.molregno = cs.molregno
    left join compound_properties cp on md.molregno = cp.molregno
    where cs.canonical_smiles is not null
    """
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(query, conn)


def read_chembl_admet_sqlite(path: Path) -> pd.DataFrame:
    """Extract ChEMBL assay-derived ADMET measurements.

    ChEMBL marks ADME/PK/tox assays with assay_type = 'A'. Some releases also
    carry useful ADMET-like endpoints outside that broad flag, so the standard
    type filter keeps common pharmacokinetic and safety endpoints as well.
    """
    placeholders = ",".join("?" for _ in ADMET_STANDARD_TYPES)
    query = f"""
    select
      md.chembl_id,
      ass.assay_chembl_id,
      ass.assay_type,
      ass.description as assay_description,
      td.chembl_id as target_chembl_id,
      td.pref_name as target_pref_name,
      td.target_type,
      td.organism,
      act.standard_type,
      act.standard_relation,
      act.standard_value,
      act.standard_units,
      act.pchembl_value
    from activities act
    join assays ass on act.assay_id = ass.assay_id
    join molecule_dictionary md on act.molregno = md.molregno
    left join target_dictionary td on ass.tid = td.tid
    where act.standard_value is not null
      and act.standard_type is not null
      and (
        ass.assay_type = 'A'
        or act.standard_type in ({placeholders})
        or lower(coalesce(ass.description, '')) like '%adme%'
        or lower(coalesce(ass.description, '')) like '%tox%'
        or lower(coalesce(ass.description, '')) like '%clearance%'
        or lower(coalesce(ass.description, '')) like '%solubility%'
        or lower(coalesce(ass.description, '')) like '%permeability%'
        or lower(coalesce(ass.description, '')) like '%microsom%'
        or lower(coalesce(ass.description, '')) like '%hepat%'
        or lower(coalesce(ass.description, '')) like '%herg%'
      )
    """
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(query, conn, params=ADMET_STANDARD_TYPES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare ChEMBL molecules for fragment atlas.")
    parser.add_argument("--input", type=Path, required=True, help="ChEMBL SQLite database or CSV file.")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/molecules.parquet")
    parser.add_argument("--admet-output", type=Path, default=ROOT / "data/processed/admet_measurements.parquet")
    parser.add_argument("--admet-csv", type=Path, help="Optional ADMET/activity CSV for CSV molecule inputs.")
    parser.add_argument("--skip-admet", action="store_true", help="Skip extraction of ChEMBL assay-derived ADMET measurements.")
    args = parser.parse_args()

    if args.input.suffix.lower() in {".sqlite", ".db", ".sqlite3"}:
        df = read_chembl_sqlite(args.input)
        admet = pd.DataFrame() if args.skip_admet else read_chembl_admet_sqlite(args.input)
    else:
        df = read_csv(args.input)
        admet = pd.read_csv(args.admet_csv) if args.admet_csv else pd.DataFrame()

    molecules = normalize_molecule_columns(df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    molecules.to_parquet(args.output, index=False)
    if not admet.empty:
        args.admet_output.parent.mkdir(parents=True, exist_ok=True)
        admet.to_parquet(args.admet_output, index=False)
        print(f"Wrote {len(admet):,} ADMET/activity measurements to {args.admet_output}")
    print(f"Wrote {len(molecules):,} molecules to {args.output}")


if __name__ == "__main__":
    main()
