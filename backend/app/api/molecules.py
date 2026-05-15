from __future__ import annotations

import duckdb
import math
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.db.duckdb import get_connection
from app.services.image_service import smiles_to_svg

router = APIRouter(prefix="/molecules", tags=["molecules"])


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


@router.get("/{chembl_id}")
def get_molecule(chembl_id: str, conn: duckdb.DuckDBPyConnection = Depends(get_connection)):
    row = conn.execute("select * from molecules where chembl_id = ?", [chembl_id]).fetchdf()
    if row.empty:
        raise HTTPException(status_code=404, detail="Molecule not found")
    record = row.iloc[0].to_dict()
    record["svg"] = smiles_to_svg(record["canonical_smiles"], width=320, height=220)
    fragments = conn.execute(
        """
        select f.fragment_id, f.fragment_smiles, f.display_smiles
        from molecule_fragments mf
        join fragments f using (fragment_id)
        where mf.chembl_id = ?
        order by f.fragment_smiles
        """,
        [chembl_id],
    ).fetchdf()
    record["fragments"] = fragments.to_dict(orient="records")
    return _json_safe(record)
