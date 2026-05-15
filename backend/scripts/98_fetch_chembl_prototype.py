#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = "https://www.ebi.ac.uk/chembl/api/data"
ADMET_TYPES = {
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
}


def get_json(path: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params, doseq=True)
    url = f"{API_ROOT}/{path}.json?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_pages(path: str, params: dict[str, Any], key: str, limit: int, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while len(rows) < limit:
        payload = get_json(path, {**params, "limit": min(page_size, limit - len(rows)), "offset": offset})
        page = payload.get(key, [])
        if not page:
            break
        rows.extend(page)
        if not payload.get("page_meta", {}).get("next"):
            break
        offset += len(page)
        time.sleep(0.05)
    return rows[:limit]


def molecule_row(item: dict[str, Any]) -> dict[str, Any] | None:
    structures = item.get("molecule_structures") or {}
    props = item.get("molecule_properties") or {}
    smiles = structures.get("canonical_smiles")
    if not smiles:
        return None
    return {
        "chembl_id": item.get("molecule_chembl_id"),
        "canonical_smiles": smiles,
        "standard_inchi_key": structures.get("standard_inchi_key"),
        "pref_name": item.get("pref_name"),
        "max_phase": item.get("max_phase"),
        "mw": props.get("full_mwt"),
        "clogp": props.get("alogp"),
        "tpsa": props.get("psa"),
        "hbd": props.get("hbd"),
        "hba": props.get("hba"),
        "rotb": props.get("rtb"),
    }


def activity_row(item: dict[str, Any]) -> dict[str, Any] | None:
    if item.get("standard_value") in {None, ""} or not item.get("standard_type"):
        return None
    standard_type = item.get("standard_type")
    description = (item.get("assay_description") or "").lower()
    assay_type = item.get("assay_type")
    looks_admet = (
        assay_type == "A"
        or standard_type in ADMET_TYPES
        or any(token in description for token in ["adme", "tox", "clearance", "solubility", "permeability", "microsom", "hepat", "herg"])
    )
    if not looks_admet:
        return None
    return {
        "chembl_id": item.get("molecule_chembl_id"),
        "assay_chembl_id": item.get("assay_chembl_id"),
        "assay_type": assay_type,
        "assay_description": item.get("assay_description"),
        "target_chembl_id": item.get("target_chembl_id"),
        "target_pref_name": item.get("target_pref_name"),
        "target_type": item.get("target_type"),
        "organism": item.get("target_organism"),
        "standard_type": standard_type,
        "standard_relation": item.get("standard_relation"),
        "standard_value": item.get("standard_value"),
        "standard_units": item.get("standard_units"),
        "pchembl_value": item.get("pchembl_value"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a small real ChEMBL prototype subset through the ChEMBL web API.")
    parser.add_argument("--max-phase", type=int, default=4, help="Minimum ChEMBL max_phase for molecule selection.")
    parser.add_argument("--molecule-limit", type=int, default=1000)
    parser.add_argument("--activity-limit-per-molecule", type=int, default=50)
    parser.add_argument("--molecules-output", type=Path, default=ROOT / "data/raw/chembl_prototype_molecules.csv")
    parser.add_argument("--admet-output", type=Path, default=ROOT / "data/raw/chembl_prototype_admet.csv")
    args = parser.parse_args()

    raw_molecules = fetch_pages(
        "molecule",
        {"max_phase__gte": args.max_phase, "molecule_structures__canonical_smiles__isnull": "false"},
        "molecules",
        args.molecule_limit,
    )
    molecules = [row for item in raw_molecules if (row := molecule_row(item))]
    molecule_ids = [row["chembl_id"] for row in molecules if row.get("chembl_id")]

    activities: list[dict[str, Any]] = []
    for index, chembl_id in enumerate(molecule_ids, start=1):
        try:
            raw_activities = fetch_pages(
                "activity",
                {
                    "molecule_chembl_id": chembl_id,
                    "standard_value__isnull": "false",
                    "standard_type__isnull": "false",
                },
                "activities",
                args.activity_limit_per_molecule,
            )
            activities.extend(row for item in raw_activities if (row := activity_row(item)))
        except Exception as exc:
            print(f"Warning: failed to fetch activities for {chembl_id}: {exc}")
        if index % 50 == 0:
            print(f"Fetched activities for {index:,}/{len(molecule_ids):,} molecules")
        time.sleep(0.03)

    args.molecules_output.parent.mkdir(parents=True, exist_ok=True)
    args.admet_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(molecules).drop_duplicates("chembl_id").to_csv(args.molecules_output, index=False)
    pd.DataFrame(activities).drop_duplicates().to_csv(args.admet_output, index=False)
    print(f"Wrote {len(molecules):,} molecules to {args.molecules_output}")
    print(f"Wrote {len(activities):,} ADMET/activity measurements to {args.admet_output}")


if __name__ == "__main__":
    main()
