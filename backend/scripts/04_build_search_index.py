#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.fragment_service import PROPERTY_COLUMNS, compute_descriptors

ROOT = Path(__file__).resolve().parents[2]


def has_table(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(conn.execute("select count(*) from information_schema.tables where table_name = ?", [table]).fetchone()[0])


def ensure_fragment_descriptors(conn: duckdb.DuckDBPyConnection, table: str) -> None:
    if not has_table(conn, table):
        return
    columns = {row[0] for row in conn.execute(f"describe {table}").fetchall()}
    if set(PROPERTY_COLUMNS).issubset(columns):
        return

    fragments = conn.execute(f"select * from {table}").fetchdf()
    rows = []
    for row in fragments.itertuples(index=False):
        values = row._asdict()
        try:
            descriptors = compute_descriptors(values["fragment_smiles"])
        except Exception:
            descriptors = {column: pd.NA for column in PROPERTY_COLUMNS}
        values.update(descriptors)
        rows.append(values)
    enriched = pd.DataFrame(rows)
    conn.register(f"{table}_enriched_df", enriched)
    conn.execute(f"create or replace table {table} as select * from {table}_enriched_df")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build lightweight DuckDB search indexes.")
    parser.add_argument("--duckdb", type=Path, default=ROOT / "data/derived/fragment_atlas.duckdb")
    args = parser.parse_args()

    conn = duckdb.connect(str(args.duckdb))
    ensure_fragment_descriptors(conn, "fragments")
    ensure_fragment_descriptors(conn, "tdc_fragments")
    if has_table(conn, "tdc_fragments") and has_table(conn, "tdc_fragment_admet_stats"):
        conn.execute(
            """
            create or replace table fragment_search as
            with tdc_counts as (
                select fragment_id,
                       sum(measurement_count)::integer as tdc_measurement_count,
                       count(*)::integer as tdc_endpoint_count,
                       sum(molecule_count)::integer as tdc_molecule_observation_count
                from tdc_fragment_admet_stats
                group by fragment_id
            ),
            chembl as (
                select s.fragment_id, s.fragment_smiles, s.display_smiles, s.heavy_atom_count,
                       f.mw as fragment_mw, f.clogp as fragment_clogp, f.tpsa as fragment_tpsa,
                       f.hbd as fragment_hbd, f.hba as fragment_hba, f.rotb as fragment_rotb,
                       f.fsp3 as fragment_fsp3, f.qed as fragment_qed,
                       s.parent_count, s.assay_count, s.target_count,
                       s.admet_measurement_count, s.admet_endpoint_count, s.admet_assay_count, s.admet_target_count,
                       s.mw_mean, s.clogp_mean, s.tpsa_mean, s.hbd_mean, s.hba_mean, s.rotb_mean, s.fsp3_mean, s.qed_mean,
                       true as has_chembl
                from fragment_stats s
                left join fragments f using (fragment_id)
            ),
            tdc as (
                select f.fragment_id, f.fragment_smiles, f.display_smiles, f.heavy_atom_count,
                       f.mw as fragment_mw, f.clogp as fragment_clogp, f.tpsa as fragment_tpsa,
                       f.hbd as fragment_hbd, f.hba as fragment_hba, f.rotb as fragment_rotb,
                       f.fsp3 as fragment_fsp3, f.qed as fragment_qed,
                       coalesce(c.tdc_measurement_count, 0) as tdc_measurement_count,
                       coalesce(c.tdc_endpoint_count, 0) as tdc_endpoint_count,
                       coalesce(c.tdc_molecule_observation_count, 0) as tdc_molecule_observation_count,
                       true as has_tdc
                from tdc_fragments f
                left join tdc_counts c using (fragment_id)
            )
            select coalesce(c.fragment_id, t.fragment_id) as fragment_id,
                   coalesce(c.fragment_smiles, t.fragment_smiles) as fragment_smiles,
                   coalesce(c.display_smiles, t.display_smiles) as display_smiles,
                   coalesce(c.heavy_atom_count, t.heavy_atom_count) as heavy_atom_count,
                   coalesce(c.fragment_mw, t.fragment_mw) as fragment_mw,
                   coalesce(c.fragment_clogp, t.fragment_clogp) as fragment_clogp,
                   coalesce(c.fragment_tpsa, t.fragment_tpsa) as fragment_tpsa,
                   coalesce(c.fragment_hbd, t.fragment_hbd) as fragment_hbd,
                   coalesce(c.fragment_hba, t.fragment_hba) as fragment_hba,
                   coalesce(c.fragment_rotb, t.fragment_rotb) as fragment_rotb,
                   coalesce(c.fragment_fsp3, t.fragment_fsp3) as fragment_fsp3,
                   coalesce(c.fragment_qed, t.fragment_qed) as fragment_qed,
                   coalesce(c.fragment_mw, t.fragment_mw) <= 300
                     and coalesce(c.fragment_clogp, t.fragment_clogp) <= 3
                     and coalesce(c.fragment_hbd, t.fragment_hbd) <= 3
                     and coalesce(c.fragment_hba, t.fragment_hba) <= 3
                     and coalesce(c.fragment_rotb, t.fragment_rotb) <= 3
                     as is_fragment_like,
                   case
                     when c.has_chembl and t.has_tdc then 'ChEMBL+TDC'
                     when c.has_chembl then 'ChEMBL'
                     else 'TDC'
                   end as source,
                   coalesce(c.has_chembl, false) as has_chembl,
                   coalesce(t.has_tdc, false) as has_tdc,
                   coalesce(c.parent_count, 0) as parent_count,
                   coalesce(c.assay_count, 0) as assay_count,
                   coalesce(c.target_count, 0) as target_count,
                   coalesce(c.admet_measurement_count, 0) as chembl_admet_measurement_count,
                   coalesce(c.admet_endpoint_count, 0) as chembl_admet_endpoint_count,
                   coalesce(c.admet_assay_count, 0) as admet_assay_count,
                   coalesce(c.admet_target_count, 0) as admet_target_count,
                   coalesce(t.tdc_measurement_count, 0) as tdc_measurement_count,
                   coalesce(t.tdc_endpoint_count, 0) as tdc_endpoint_count,
                   coalesce(t.tdc_molecule_observation_count, 0) as tdc_molecule_observation_count,
                   coalesce(c.admet_measurement_count, 0) + coalesce(t.tdc_measurement_count, 0) as admet_measurement_count,
                   coalesce(c.admet_endpoint_count, 0) + coalesce(t.tdc_endpoint_count, 0) as admet_endpoint_count,
                   c.mw_mean, c.clogp_mean, c.tpsa_mean, c.hbd_mean, c.hba_mean, c.rotb_mean, c.fsp3_mean, c.qed_mean
            from chembl c
            full outer join tdc t using (fragment_id)
            """
        )
    else:
        conn.execute(
            """
            create or replace table fragment_search as
            select fragment_id, fragment_smiles, display_smiles, heavy_atom_count,
                   null as fragment_mw, null as fragment_clogp, null as fragment_tpsa,
                   null as fragment_hbd, null as fragment_hba, null as fragment_rotb,
                   null as fragment_fsp3, null as fragment_qed,
                   true as is_fragment_like,
                   'ChEMBL' as source, true as has_chembl, false as has_tdc,
                   parent_count, assay_count, target_count,
                   admet_measurement_count as chembl_admet_measurement_count,
                   admet_endpoint_count as chembl_admet_endpoint_count,
                   admet_assay_count, admet_target_count,
                   0 as tdc_measurement_count, 0 as tdc_endpoint_count, 0 as tdc_molecule_observation_count,
                   admet_measurement_count, admet_endpoint_count,
                   mw_mean, clogp_mean, tpsa_mean, hbd_mean, hba_mean, rotb_mean, fsp3_mean, qed_mean
            from fragment_stats
            """
        )
    conn.execute("create index if not exists idx_fragment_smiles on fragment_stats(fragment_smiles)")
    conn.execute("create index if not exists idx_display_smiles on fragment_stats(display_smiles)")
    conn.execute("create index if not exists idx_fragment_search_id on fragment_search(fragment_id)")
    conn.execute("create index if not exists idx_fragment_search_source on fragment_search(source)")
    conn.execute("create index if not exists idx_fragment_search_fragment_like on fragment_search(is_fragment_like)")
    conn.execute("create index if not exists idx_fragment_search_smiles on fragment_search(fragment_smiles)")
    conn.execute("create index if not exists idx_molecule_chembl on molecules(chembl_id)")
    conn.close()
    print(f"Search indexes are ready in {args.duckdb}")


if __name__ == "__main__":
    main()
