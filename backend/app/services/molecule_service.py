from __future__ import annotations

import pandas as pd


def normalize_molecule_columns(df: pd.DataFrame) -> pd.DataFrame:
    required = ["chembl_id", "canonical_smiles"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    out = df.copy()
    if "standard_inchi_key" not in out.columns:
        out["standard_inchi_key"] = pd.NA
    if "pref_name" not in out.columns:
        out["pref_name"] = pd.NA
    out = out.dropna(subset=["chembl_id", "canonical_smiles"]).drop_duplicates("chembl_id")
    return out
