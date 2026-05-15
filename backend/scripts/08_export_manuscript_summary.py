#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def table_count(conn: duckdb.DuckDBPyConnection, table: str) -> int:
    exists = conn.execute("select count(*) from information_schema.tables where table_name = ?", [table]).fetchone()[0]
    if not exists:
        return 0
    return int(conn.execute(f"select count(*) from {table}").fetchone()[0])


def records(conn: duckdb.DuckDBPyConnection, sql: str, limit: int | None = None) -> list[dict]:
    query = sql if limit is None else f"{sql}\nlimit {limit}"
    df = conn.execute(query).fetchdf()
    return json.loads(df.to_json(orient="records"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export compact manuscript summary data from the fragment atlas DuckDB database.")
    parser.add_argument("--duckdb", type=Path, default=ROOT / "data/derived/fragment_atlas.duckdb")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/manuscript/manuscript_summary.json")
    args = parser.parse_args()

    conn = duckdb.connect(str(args.duckdb), read_only=True)
    summary = {
        "counts": {
            "molecules": table_count(conn, "molecules"),
            "fragments": table_count(conn, "fragments"),
            "molecule_fragments": table_count(conn, "molecule_fragments"),
            "fragment_stats": table_count(conn, "fragment_stats"),
            "admet_measurements": table_count(conn, "admet_measurements"),
            "fragment_admet_stats": table_count(conn, "fragment_admet_stats"),
            "tdc_admet_measurements": table_count(conn, "tdc_admet_measurements"),
            "tdc_fragments": table_count(conn, "tdc_fragments"),
            "tdc_molecule_fragments": table_count(conn, "tdc_molecule_fragments"),
            "tdc_fragment_admet_stats": table_count(conn, "tdc_fragment_admet_stats"),
            "bootstrap_ci": table_count(conn, "tdc_fragment_admet_bootstrap_ci"),
            "matched_context": table_count(conn, "tdc_fragment_admet_matched_context"),
            "case_studies": table_count(conn, "fragment_admet_case_studies"),
        },
        "top_fragments": records(
            conn,
            """
            select display_smiles, fragment_smiles, parent_count, admet_measurement_count,
                   mw_median, clogp_median, tpsa_median, qed_median
            from fragment_stats
            order by parent_count desc
            """,
            limit=10,
        ),
        "clean_endpoint_counts": records(
            conn,
            """
            select standard_type, standard_units, count(*) as fragment_endpoint_count,
                   sum(measurement_count) as measurement_count,
                   median(median) as median_of_fragment_medians
            from tdc_fragment_admet_stats
            group by standard_type, standard_units
            order by measurement_count desc
            """,
            limit=12,
        ),
        "bootstrap_examples": records(
            conn,
            """
            select display_smiles, standard_type, standard_units, measurement_count,
                   median, ci_low, ci_high, ci_width
            from tdc_fragment_admet_bootstrap_ci
            order by measurement_count desc, ci_width asc
            """,
            limit=8,
        ),
        "matched_examples": records(
            conn,
            """
            select display_smiles, standard_type, standard_units, tdc_task, n_pairs,
                   case_median, control_median, favorable_median_delta, match_distance_median,
                   sign_test_pvalue
            from tdc_fragment_admet_matched_context
            where favorable_direction in ('high', 'low')
            order by abs(favorable_median_delta) desc, n_pairs desc
            """,
            limit=10,
        ),
        "case_studies": records(
            conn,
            """
            select display_smiles, standard_type, standard_units, tdc_task, n_pairs,
                   case_median, control_median, favorable_median_delta, ci_low, ci_high,
                   case_direction
            from fragment_admet_case_studies
            order by case_direction, abs(favorable_median_delta) desc
            """,
        ),
    }
    conn.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote manuscript summary to {args.output}")


if __name__ == "__main__":
    main()
