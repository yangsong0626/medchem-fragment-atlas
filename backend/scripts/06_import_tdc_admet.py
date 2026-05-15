#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.fragment_service import decompose_brics

ROOT = Path(__file__).resolve().parents[2]
HF_ROOT = "https://huggingface.co/datasets/maomlab/TDC/resolve/main/single_instance_datasets"

TASKS = {
    "caco2_wang": ("Papp", "log Papp", "Caco-2 permeability; higher is better", "high"),
    "pampa_ncats": ("Papp", "binary class", "PAMPA permeability; higher is better", "high"),
    "approved_pampa_ncats": ("Papp", "binary class", "Approved-drug PAMPA permeability; higher is better", "high"),
    "bioavailability_ma": ("Absorption", "binary class", "Oral bioavailability; higher is better", "high"),
    "hia_hou": ("Absorption", "binary class", "Human intestinal absorption; higher is better", "high"),
    "clearance_hepatocyte_az": ("CL", "uL/min/10^6 cells", "Hepatocyte clearance; lower is better", "low"),
    "clearance_microsome_az": ("CL", "mL/min/g", "Microsomal clearance; lower is better", "low"),
    "half_life_obach": ("Half-life", "hr", "Half-life; higher is often better", "high"),
    "ppbr_az": ("PPB", "%", "Plasma protein binding", "neutral"),
    "vdss_lombardo": ("VDss", "L/kg", "Volume of distribution", "neutral"),
    "solubility_aqsoldb": ("Solubility", "log mol/L", "Aqueous solubility; higher is better", "high"),
    "lipophilicity_astrazeneca": ("LogD", "logD", "Lipophilicity", "neutral"),
    "herg": ("hERG", "safety class", "hERG safety class derived as 1 - liability label; higher is better", "high"),
    "herg_karim": ("hERG", "safety class", "hERG safety class derived as 1 - liability label; higher is better", "high"),
    "ld50_zhu": ("LD50", "log(1/mol/kg)", "Acute toxicity LD50; higher is better", "high"),
    "dili": ("DILI", "safety class", "DILI safety class derived as 1 - liability label; higher is better", "high"),
}

CLASSIFICATION_SAFETY_INVERT = {"herg", "herg_karim", "dili"}


def download(url: str, output: Path) -> None:
    if output.exists() and output.stat().st_size > 0:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, output.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def load_tdc(raw_dir: Path, include_tox: bool) -> pd.DataFrame:
    files = [("ADME", f"{HF_ROOT}/ADME/train-00000-of-00001.parquet")]
    if include_tox:
        files.append(("Tox", f"{HF_ROOT}/Tox/train-00000-of-00001.parquet"))
    frames = []
    for name, url in files:
        path = raw_dir / f"{name}.parquet"
        download(url, path)
        frame = pd.read_parquet(path)
        frame["tdc_group"] = name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def normalize_rows(df: pd.DataFrame, max_rows_per_task: int | None) -> pd.DataFrame:
    df = df.copy()
    df["Task"] = df["Task"].str.lower()
    df = df[df["Task"].isin(TASKS)].copy()
    if max_rows_per_task:
        df = df.groupby("Task", group_keys=False).head(max_rows_per_task)

    records = []
    for row in df.itertuples(index=False):
        task = row.Task
        endpoint, units, description, direction = TASKS[task]
        raw_value = pd.to_numeric(row.Y, errors="coerce")
        if pd.isna(raw_value):
            continue
        value = float(1 - raw_value) if task in CLASSIFICATION_SAFETY_INVERT else float(raw_value)
        records.append(
            {
                "tdc_id": f"{task}:{row.Drug_ID}",
                "tdc_task": task,
                "tdc_group": row.tdc_group,
                "drug_id": row.Drug_ID,
                "canonical_smiles": row.SMILES,
                "standard_type": endpoint,
                "standard_units": units,
                "standard_value": value,
                "raw_value": float(raw_value),
                "favorable_direction": direction,
                "description": description,
                "split": row.split,
            }
        )
    return pd.DataFrame(records).drop_duplicates(["tdc_task", "drug_id", "canonical_smiles"])


def aggregate(values: pd.Series) -> dict[str, float | None]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return {"mean": None, "median": None, "std": None, "p10": None, "p90": None}
    return {
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std(ddof=0)),
        "p10": float(clean.quantile(0.10)),
        "p90": float(clean.quantile(0.90)),
    }


def fragment_tdc(clean: pd.DataFrame, min_heavy_atoms: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fragment_rows: dict[str, dict] = {}
    mapping_rows: list[dict] = []
    failures: list[dict] = []
    fragment_cache: dict[str, list] = {}
    for row in clean.itertuples(index=False):
        try:
            if row.canonical_smiles not in fragment_cache:
                fragment_cache[row.canonical_smiles] = decompose_brics(row.canonical_smiles, min_heavy_atoms=min_heavy_atoms)
            for fragment in fragment_cache[row.canonical_smiles]:
                fragment_rows[fragment.fragment_id] = {
                    "fragment_id": fragment.fragment_id,
                    "fragment_smiles": fragment.fragment_smiles,
                    "display_smiles": fragment.display_smiles,
                    "heavy_atom_count": fragment.heavy_atom_count,
                }
                mapping_rows.append({"tdc_id": row.tdc_id, "fragment_id": fragment.fragment_id})
        except Exception as exc:
            failures.append({"tdc_id": row.tdc_id, "canonical_smiles": row.canonical_smiles, "failure": str(exc)})
    return pd.DataFrame(fragment_rows.values()), pd.DataFrame(mapping_rows).drop_duplicates(), pd.DataFrame(failures)


def build_rollups(clean: pd.DataFrame, mapping: pd.DataFrame, fragments: pd.DataFrame) -> pd.DataFrame:
    joined = mapping.merge(clean, on="tdc_id", how="inner").merge(fragments, on="fragment_id", how="inner")
    rows = []
    for keys, group in joined.groupby(["fragment_id", "fragment_smiles", "display_smiles", "standard_type", "standard_units"], dropna=False):
        fragment_id, fragment_smiles, display_smiles, standard_type, standard_units = keys
        first = group.iloc[0]
        rows.append(
            {
                "fragment_id": fragment_id,
                "fragment_smiles": fragment_smiles,
                "display_smiles": display_smiles,
                "source": "TDC",
                "standard_type": standard_type,
                "standard_units": standard_units,
                "measurement_count": int(len(group)),
                "molecule_count": int(group["tdc_id"].nunique()),
                "task_count": int(group["tdc_task"].nunique()),
                "tdc_tasks": ",".join(sorted(group["tdc_task"].dropna().unique())),
                "favorable_direction": first["favorable_direction"],
                "description": first["description"],
                **aggregate(group["standard_value"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["fragment_id", "measurement_count"], ascending=[True, False])


def main() -> None:
    parser = argparse.ArgumentParser(description="Import clean TDC ADMET datasets and aggregate them onto BRICS fragments.")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/tdc")
    parser.add_argument("--duckdb", type=Path, default=ROOT / "data/derived/fragment_atlas.duckdb")
    parser.add_argument("--clean-output", type=Path, default=ROOT / "data/derived/tdc_admet_measurements.parquet")
    parser.add_argument("--fragment-output", type=Path, default=ROOT / "data/derived/tdc_fragments.parquet")
    parser.add_argument("--mapping-output", type=Path, default=ROOT / "data/derived/tdc_molecule_fragments.parquet")
    parser.add_argument("--stats-output", type=Path, default=ROOT / "data/derived/tdc_fragment_admet_stats.parquet")
    parser.add_argument("--failures-output", type=Path, default=ROOT / "data/derived/tdc_fragment_failures.csv")
    parser.add_argument("--max-rows-per-task", type=int, default=None)
    parser.add_argument("--min-heavy-atoms", type=int, default=3)
    parser.add_argument("--skip-tox", action="store_true")
    args = parser.parse_args()

    raw = load_tdc(args.raw_dir, include_tox=not args.skip_tox)
    clean = normalize_rows(raw, args.max_rows_per_task)
    fragments, mapping, failures = fragment_tdc(clean, min_heavy_atoms=args.min_heavy_atoms)
    stats = build_rollups(clean, mapping, fragments)

    for path in [args.clean_output, args.fragment_output, args.mapping_output, args.stats_output, args.failures_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(args.clean_output, index=False)
    fragments.to_parquet(args.fragment_output, index=False)
    mapping.to_parquet(args.mapping_output, index=False)
    stats.to_parquet(args.stats_output, index=False)
    failures.to_csv(args.failures_output, index=False)

    conn = duckdb.connect(str(args.duckdb))
    conn.register("tdc_clean_df", clean)
    conn.register("tdc_fragments_df", fragments)
    conn.register("tdc_mapping_df", mapping)
    conn.register("tdc_stats_df", stats)
    conn.execute("create or replace table tdc_admet_measurements as select * from tdc_clean_df")
    conn.execute("create or replace table tdc_fragments as select * from tdc_fragments_df")
    conn.execute("create or replace table tdc_molecule_fragments as select * from tdc_mapping_df")
    conn.execute("create or replace table tdc_fragment_admet_stats as select * from tdc_stats_df")
    conn.execute("create index if not exists idx_tdc_fragment_admet_stats_fragment on tdc_fragment_admet_stats(fragment_id)")
    conn.close()
    print(f"Wrote {len(clean):,} clean TDC measurements, {len(fragments):,} fragments, {len(stats):,} fragment endpoint rollups")
    print(f"Wrote DuckDB tables to {args.duckdb}")


if __name__ == "__main__":
    main()
