#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.fragment_service import PROPERTY_COLUMNS, aggregate_property

ROOT = Path(__file__).resolve().parents[2]
ADMET_VALUE_COLUMN = "standard_value"
ADMET_COLUMNS = [
    "chembl_id",
    "assay_chembl_id",
    "assay_type",
    "assay_description",
    "target_chembl_id",
    "target_pref_name",
    "target_type",
    "organism",
    "standard_type",
    "standard_relation",
    "standard_value",
    "standard_units",
    "pchembl_value",
]


def unique_count(series: pd.Series) -> int:
    return int(series.dropna().nunique()) if series is not None else 0


def build_admet_rollups(mapping: pd.DataFrame, admet: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if admet.empty:
        return pd.DataFrame(), pd.DataFrame()

    required = {"chembl_id", "standard_type", ADMET_VALUE_COLUMN}
    missing = required - set(admet.columns)
    if missing:
        raise ValueError(f"ADMET input is missing required columns: {', '.join(sorted(missing))}")

    admet = admet.copy()
    admet[ADMET_VALUE_COLUMN] = pd.to_numeric(admet[ADMET_VALUE_COLUMN], errors="coerce")
    admet = admet.dropna(subset=["chembl_id", "standard_type", ADMET_VALUE_COLUMN])
    joined = mapping[["chembl_id", "fragment_id"]].drop_duplicates().merge(admet, on="chembl_id", how="inner")
    if joined.empty:
        return pd.DataFrame(), joined

    rows: list[dict] = []
    group_cols = ["fragment_id", "standard_type", "standard_units"]
    for keys, group in joined.groupby(group_cols, dropna=False):
        fragment_id, standard_type, standard_units = keys
        summary = aggregate_property(group[ADMET_VALUE_COLUMN])
        rows.append(
            {
                "fragment_id": fragment_id,
                "standard_type": standard_type,
                "standard_units": standard_units,
                "measurement_count": int(len(group)),
                "parent_count": unique_count(group["chembl_id"]),
                "assay_count": unique_count(group["assay_chembl_id"]) if "assay_chembl_id" in group.columns else 0,
                "target_count": unique_count(group["target_chembl_id"]) if "target_chembl_id" in group.columns else 0,
                **summary,
            }
        )
    rollups = pd.DataFrame(rows).sort_values(["fragment_id", "measurement_count"], ascending=[True, False])
    return rollups, joined


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate parent molecule properties per BRICS fragment.")
    parser.add_argument("--molecules", type=Path, default=ROOT / "data/derived/molecules_with_descriptors.parquet")
    parser.add_argument("--fragments", type=Path, default=ROOT / "data/derived/fragments.parquet")
    parser.add_argument("--mapping", type=Path, default=ROOT / "data/derived/molecule_fragments.parquet")
    parser.add_argument("--admet", type=Path, default=ROOT / "data/processed/admet_measurements.parquet")
    parser.add_argument("--stats-output", type=Path, default=ROOT / "data/derived/fragment_stats.parquet")
    parser.add_argument("--admet-stats-output", type=Path, default=ROOT / "data/derived/fragment_admet_stats.parquet")
    parser.add_argument("--duckdb-output", type=Path, default=ROOT / "data/derived/fragment_atlas.duckdb")
    args = parser.parse_args()

    molecules = pd.read_parquet(args.molecules)
    fragments = pd.read_parquet(args.fragments)
    mapping = pd.read_parquet(args.mapping).drop_duplicates(["chembl_id", "fragment_id"])
    admet = pd.read_parquet(args.admet) if args.admet.exists() else pd.DataFrame(columns=ADMET_COLUMNS)
    admet_rollups, fragment_admet_measurements = build_admet_rollups(mapping, admet)
    joined = mapping.merge(molecules, on="chembl_id", how="inner").merge(fragments, on="fragment_id", how="inner", suffixes=("", "_fragment"))

    stats_rows: list[dict] = []
    for fragment_id, group in joined.groupby("fragment_id"):
        first = group.iloc[0]
        row = {
            "fragment_id": fragment_id,
            "fragment_smiles": first["fragment_smiles"],
            "display_smiles": first["display_smiles"],
            "heavy_atom_count": int(first["heavy_atom_count"]),
            "parent_count": unique_count(group["chembl_id"]),
            "assay_count": 0,
            "target_count": 0,
            "admet_measurement_count": 0,
            "admet_endpoint_count": 0,
            "admet_assay_count": 0,
            "admet_target_count": 0,
            "admet_summary": "[]",
            "representative_parent_ids": json.dumps(group["chembl_id"].drop_duplicates().head(20).tolist()),
        }
        if not admet_rollups.empty:
            fragment_endpoint_rows = admet_rollups[admet_rollups["fragment_id"] == fragment_id]
            endpoint_rows = fragment_endpoint_rows.head(25)
            if not endpoint_rows.empty:
                row["admet_summary"] = json.dumps(endpoint_rows.drop(columns=["fragment_id"]).to_dict(orient="records"))
                row["admet_endpoint_count"] = int(fragment_endpoint_rows[["standard_type", "standard_units"]].drop_duplicates().shape[0])
                row["admet_measurement_count"] = int(fragment_endpoint_rows["measurement_count"].sum())
        if not fragment_admet_measurements.empty:
            target_cols = [col for col in ["target_chembl_id", "target_pref_name"] if col in fragment_admet_measurements.columns]
            admet_targets = fragment_admet_measurements[fragment_admet_measurements["fragment_id"] == fragment_id]
            row["admet_assay_count"] = unique_count(admet_targets["assay_chembl_id"]) if "assay_chembl_id" in admet_targets.columns else 0
            row["admet_target_count"] = unique_count(admet_targets["target_chembl_id"]) if "target_chembl_id" in admet_targets.columns else 0
            row["assay_count"] = row["admet_assay_count"]
            row["target_count"] = row["admet_target_count"]
            row["top_targets"] = (
                json.dumps(admet_targets[target_cols].dropna(how="all").drop_duplicates().head(20).to_dict(orient="records"))
                if target_cols and not admet_targets.empty
                else "[]"
            )
        else:
            row["top_targets"] = "[]"
        for prop in PROPERTY_COLUMNS:
            summary = aggregate_property(group[prop])
            for stat, value in summary.items():
                row[f"{prop}_{stat}"] = value
            row[f"{prop}_values"] = json.dumps(pd.to_numeric(group[prop], errors="coerce").dropna().round(4).tolist())
        stats_rows.append(row)

    stats = pd.DataFrame(stats_rows).sort_values(["parent_count", "fragment_smiles"], ascending=[False, True])
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    stats.to_parquet(args.stats_output, index=False)
    if not admet_rollups.empty:
        args.admet_stats_output.parent.mkdir(parents=True, exist_ok=True)
        admet_rollups.to_parquet(args.admet_stats_output, index=False)

    conn = duckdb.connect(str(args.duckdb_output))
    conn.register("fragments_df", fragments)
    conn.register("molecules_df", molecules)
    conn.register("mapping_df", mapping)
    conn.register("stats_df", stats)
    conn.register("admet_df", admet)
    conn.register("admet_rollups_df", admet_rollups)
    conn.execute("create or replace table fragments as select * from fragments_df")
    conn.execute("create or replace table molecules as select * from molecules_df")
    conn.execute("create or replace table molecule_fragments as select * from mapping_df")
    conn.execute("create or replace table fragment_stats as select * from stats_df")
    conn.execute("create or replace table admet_measurements as select * from admet_df")
    conn.execute("create or replace table fragment_admet_stats as select * from admet_rollups_df")
    conn.execute("create index if not exists idx_fragment_stats_id on fragment_stats(fragment_id)")
    conn.execute("create index if not exists idx_molecule_fragments_fragment on molecule_fragments(fragment_id)")
    conn.execute("create index if not exists idx_fragment_admet_stats_fragment on fragment_admet_stats(fragment_id)")
    conn.close()
    print(f"Wrote {len(stats):,} fragment stats rows and DuckDB database to {args.duckdb_output}")


if __name__ == "__main__":
    main()
