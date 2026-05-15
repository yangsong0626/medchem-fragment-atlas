from __future__ import annotations

import json
import math
from typing import Literal

import duckdb
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.core.config import get_settings
from app.db.duckdb import get_connection
from app.services.image_service import smiles_to_svg

router = APIRouter(prefix="/fragments", tags=["fragments"])


def _has_table(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    rows = conn.execute("select count(*) from information_schema.tables where table_name = ?", [table]).fetchone()
    return bool(rows and rows[0])


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


def _histogram(values: list[float], bin_count: int = 18) -> list[dict[str, float | int]]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if low == high:
        return [{"bin_start": low, "bin_end": high, "count": len(values)}]

    width = (high - low) / bin_count
    bins = [{"bin_start": low + i * width, "bin_end": low + (i + 1) * width, "count": 0} for i in range(bin_count)]
    for value in values:
        idx = min(int((value - low) / width), bin_count - 1)
        bins[idx]["count"] += 1
    return bins


def _box_summary(values: pd.Series) -> dict[str, float | int | None]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return {"count": 0, "min": None, "q1": None, "median": None, "q3": None, "max": None, "mean": None, "std": None}
    return {
        "count": int(len(clean)),
        "min": float(clean.min()),
        "q1": float(clean.quantile(0.25)),
        "median": float(clean.median()),
        "q3": float(clean.quantile(0.75)),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
        "std": None if len(clean) < 2 else float(clean.std(ddof=0)),
    }


@router.get("")
def list_fragments(
    q: str | None = None,
    source: Literal["all", "chembl", "tdc", "both"] = "all",
    fragment_like: bool = True,
    min_count: int | None = Query(default=None, ge=1),
    min_mw: float | None = None,
    max_mw: float | None = None,
    min_logp: float | None = None,
    max_logp: float | None = None,
    min_tpsa: float | None = None,
    max_tpsa: float | None = None,
    min_hbd: float | None = None,
    max_hbd: float | None = None,
    min_hba: float | None = None,
    max_hba: float | None = None,
    min_rotb: float | None = None,
    max_rotb: float | None = None,
    min_fsp3: float | None = None,
    max_fsp3: float | None = None,
    min_qed: float | None = None,
    max_qed: float | None = None,
    min_admet_measurements: int | None = Query(default=None, ge=1),
    sort_by: str = "parent_count",
    sort_dir: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1),
    conn: duckdb.DuckDBPyConnection = Depends(get_connection),
):
    search_table = "fragment_search" if _has_table(conn, "fragment_search") else "fragment_stats"
    if not _has_table(conn, search_table):
        raise HTTPException(status_code=503, detail="Fragment atlas database has not been built.")

    allowed_sort = {
        "parent_count",
        "mw_mean",
        "clogp_mean",
        "tpsa_mean",
        "hbd_mean",
        "hba_mean",
        "rotb_mean",
        "fsp3_mean",
        "qed_mean",
        "admet_measurement_count",
        "admet_endpoint_count",
        "admet_assay_count",
        "tdc_measurement_count",
        "tdc_endpoint_count",
        "fragment_smiles",
        "source",
        "fragment_mw",
        "fragment_clogp",
        "fragment_tpsa",
        "fragment_hbd",
        "fragment_hba",
        "fragment_rotb",
        "fragment_fsp3",
        "fragment_qed",
    }
    if sort_by not in allowed_sort:
        sort_by = "parent_count"
    page_size = min(page_size, get_settings().api_page_size_limit)

    where: list[str] = []
    params: list[object] = []
    if q:
        where.append("(fragment_smiles ilike ? or display_smiles ilike ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if source == "chembl":
        where.append("has_chembl = true")
    elif source == "tdc":
        where.append("has_tdc = true")
    elif source == "both":
        where.append("has_chembl = true and has_tdc = true")
    if fragment_like and search_table == "fragment_search":
        where.append("is_fragment_like = true")
    descriptor_prefix = "fragment" if search_table == "fragment_search" else None
    filters = [
        ("parent_count >= ?", min_count),
        (f"{descriptor_prefix}_mw >= ?" if descriptor_prefix else "mw_mean >= ?", min_mw),
        (f"{descriptor_prefix}_mw <= ?" if descriptor_prefix else "mw_mean <= ?", max_mw),
        (f"{descriptor_prefix}_clogp >= ?" if descriptor_prefix else "clogp_mean >= ?", min_logp),
        (f"{descriptor_prefix}_clogp <= ?" if descriptor_prefix else "clogp_mean <= ?", max_logp),
        (f"{descriptor_prefix}_tpsa >= ?" if descriptor_prefix else "tpsa_mean >= ?", min_tpsa),
        (f"{descriptor_prefix}_tpsa <= ?" if descriptor_prefix else "tpsa_mean <= ?", max_tpsa),
        (f"{descriptor_prefix}_hbd >= ?" if descriptor_prefix else "hbd_mean >= ?", min_hbd),
        (f"{descriptor_prefix}_hbd <= ?" if descriptor_prefix else "hbd_mean <= ?", max_hbd),
        (f"{descriptor_prefix}_hba >= ?" if descriptor_prefix else "hba_mean >= ?", min_hba),
        (f"{descriptor_prefix}_hba <= ?" if descriptor_prefix else "hba_mean <= ?", max_hba),
        (f"{descriptor_prefix}_rotb >= ?" if descriptor_prefix else "rotb_mean >= ?", min_rotb),
        (f"{descriptor_prefix}_rotb <= ?" if descriptor_prefix else "rotb_mean <= ?", max_rotb),
        (f"{descriptor_prefix}_fsp3 >= ?" if descriptor_prefix else "fsp3_mean >= ?", min_fsp3),
        (f"{descriptor_prefix}_fsp3 <= ?" if descriptor_prefix else "fsp3_mean <= ?", max_fsp3),
        (f"{descriptor_prefix}_qed >= ?" if descriptor_prefix else "qed_mean >= ?", min_qed),
        (f"{descriptor_prefix}_qed <= ?" if descriptor_prefix else "qed_mean <= ?", max_qed),
        ("admet_measurement_count >= ?", min_admet_measurements),
    ]
    for clause, value in filters:
        if value is not None:
            where.append(clause)
            params.append(value)
    where_sql = f"where {' and '.join(where)}" if where else ""
    total = conn.execute(f"select count(*) from {search_table} {where_sql}", params).fetchone()[0]
    offset = (page - 1) * page_size
    search_extra_cols = (
        "source, has_chembl, has_tdc, is_fragment_like, fragment_mw, fragment_clogp, fragment_tpsa, "
        "fragment_hbd, fragment_hba, fragment_rotb, fragment_fsp3, fragment_qed,"
        if search_table == "fragment_search"
        else "'ChEMBL' as source, true as has_chembl, false as has_tdc, true as is_fragment_like, "
        "null as fragment_mw, null as fragment_clogp, null as fragment_tpsa, null as fragment_hbd, "
        "null as fragment_hba, null as fragment_rotb, null as fragment_fsp3, null as fragment_qed,"
    )
    tdc_extra_cols = (
        "tdc_measurement_count, tdc_endpoint_count,"
        if search_table == "fragment_search"
        else "0 as tdc_measurement_count, 0 as tdc_endpoint_count,"
    )
    rows = conn.execute(
        f"""
        select fragment_id, fragment_smiles, display_smiles, {search_extra_cols}
               parent_count, assay_count, target_count,
               admet_measurement_count, admet_endpoint_count, admet_assay_count, admet_target_count,
               {tdc_extra_cols}
               mw_mean, clogp_mean, tpsa_mean, hbd_mean, hba_mean, rotb_mean, fsp3_mean, qed_mean
        from {search_table}
        {where_sql}
        order by {sort_by} {sort_dir}
        limit ? offset ?
        """,
        [*params, page_size, offset],
    ).fetchdf()
    return _json_safe({"items": rows.to_dict(orient="records"), "total": int(total), "page": page, "page_size": page_size})


@router.get("/compare/admet")
def compare_fragment_admet(
    fragment_a: str,
    fragment_b: str,
    limit: int = Query(default=12, ge=1, le=30),
    conn: duckdb.DuckDBPyConnection = Depends(get_connection),
):
    if fragment_a == fragment_b:
        raise HTTPException(status_code=400, detail="Select two different fragments to compare.")
    if not _has_table(conn, "tdc_admet_measurements") or not _has_table(conn, "tdc_molecule_fragments"):
        raise HTTPException(status_code=503, detail="Clean TDC ADMET tables have not been built.")

    search_table = "fragment_search" if _has_table(conn, "fragment_search") else "fragment_stats"
    fragments = conn.execute(
        f"""
        select fragment_id, fragment_smiles, display_smiles, parent_count, admet_measurement_count
        from {search_table}
        where fragment_id in (?, ?)
        """,
        [fragment_a, fragment_b],
    ).fetchdf()
    if len(fragments) != 2:
        raise HTTPException(status_code=404, detail="One or both fragments were not found.")

    rows = conn.execute(
        """
        select mf.fragment_id, m.standard_type, m.standard_units, m.tdc_task, m.standard_value
        from tdc_molecule_fragments mf
        join tdc_admet_measurements m using (tdc_id)
        where mf.fragment_id in (?, ?)
          and m.standard_value is not null
        """,
        [fragment_a, fragment_b],
    ).fetchdf()
    if rows.empty:
        return _json_safe({"fragments": fragments.to_dict(orient="records"), "endpoints": []})

    rows["standard_units"] = rows["standard_units"].fillna("")
    counts = (
        rows.groupby(["fragment_id", "standard_type", "standard_units"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    wide = counts.pivot_table(index=["standard_type", "standard_units"], columns="fragment_id", values="count", fill_value=0).reset_index()
    common = wide[(wide.get(fragment_a, 0) > 0) & (wide.get(fragment_b, 0) > 0)].copy()
    if common.empty:
        return _json_safe({"fragments": fragments.to_dict(orient="records"), "endpoints": []})
    common["rank_count"] = common[fragment_a] + common[fragment_b]
    common = common.sort_values("rank_count", ascending=False).head(limit)

    endpoints = []
    for endpoint in common.itertuples(index=False):
        endpoint_rows = rows[
            (rows["standard_type"] == endpoint.standard_type)
            & (rows["standard_units"] == endpoint.standard_units)
        ]
        task_names = ",".join(sorted(endpoint_rows["tdc_task"].dropna().unique()))
        item = {
            "standard_type": endpoint.standard_type,
            "standard_units": endpoint.standard_units or None,
            "tdc_tasks": task_names,
            "fragments": {},
        }
        all_values = pd.to_numeric(endpoint_rows["standard_value"], errors="coerce").dropna()
        item["domain"] = {
            "min": float(all_values.min()) if not all_values.empty else None,
            "max": float(all_values.max()) if not all_values.empty else None,
        }
        for fragment_id in [fragment_a, fragment_b]:
            values = endpoint_rows[endpoint_rows["fragment_id"] == fragment_id]["standard_value"]
            summary = _box_summary(values)
            item["fragments"][fragment_id] = {
                **summary,
            }
        endpoints.append(item)

    ordered_fragments = []
    for fragment_id in [fragment_a, fragment_b]:
        row = fragments[fragments["fragment_id"] == fragment_id].iloc[0].to_dict()
        row["svg"] = smiles_to_svg(row["fragment_smiles"])
        ordered_fragments.append(row)
    return _json_safe({"fragments": ordered_fragments, "endpoints": endpoints})


@router.get("/{fragment_id}/clean-admet-distribution")
def get_clean_admet_distribution(
    fragment_id: str,
    standard_type: str,
    standard_units: str = "",
    tdc_tasks: str | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_connection),
):
    if not _has_table(conn, "tdc_admet_measurements") or not _has_table(conn, "tdc_molecule_fragments"):
        raise HTTPException(status_code=503, detail="Clean TDC ADMET tables have not been built.")

    where = [
        "mf.fragment_id = ?",
        "m.standard_type = ?",
        "coalesce(m.standard_units, '') = ?",
        "m.standard_value is not null",
    ]
    params: list[object] = [fragment_id, standard_type, standard_units or ""]
    tasks = [task.strip() for task in (tdc_tasks or "").split(",") if task.strip()]
    if tasks:
        where.append(f"m.tdc_task in ({', '.join(['?'] * len(tasks))})")
        params.extend(tasks)

    rows = conn.execute(
        f"""
        select m.standard_value, m.tdc_task, m.drug_id, m.canonical_smiles
        from tdc_molecule_fragments mf
        join tdc_admet_measurements m using (tdc_id)
        where {' and '.join(where)}
        order by m.standard_value
        """,
        params,
    ).fetchdf()
    if rows.empty:
        raise HTTPException(status_code=404, detail="No clean ADMET values found for this fragment endpoint.")

    series = pd.to_numeric(rows["standard_value"], errors="coerce").dropna()
    values = [float(value) for value in series.tolist()]
    if not values:
        raise HTTPException(status_code=404, detail="No numeric clean ADMET values found for this fragment endpoint.")

    values_df = pd.DataFrame({"value": values})
    task_rows = rows.groupby("tdc_task", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False)
    return _json_safe(
        {
            "fragment_id": fragment_id,
            "standard_type": standard_type,
            "standard_units": standard_units or None,
            "tdc_tasks": ",".join(tasks) if tasks else None,
            "measurement_count": len(values),
            "molecule_count": int(rows["drug_id"].nunique()),
            "mean": float(values_df["value"].mean()),
            "median": float(values_df["value"].median()),
            "std": None if len(values) < 2 else float(values_df["value"].std(ddof=0)),
            "p10": float(values_df["value"].quantile(0.10)),
            "p90": float(values_df["value"].quantile(0.90)),
            "min": float(values_df["value"].min()),
            "max": float(values_df["value"].max()),
            "histogram": _histogram(values),
            "values": [round(value, 6) for value in values[:5000]],
            "values_truncated": len(values) > 5000,
            "task_breakdown": task_rows.to_dict(orient="records"),
        }
    )


@router.get("/{fragment_id}")
def get_fragment(fragment_id: str, conn: duckdb.DuckDBPyConnection = Depends(get_connection)):
    row = conn.execute("select * from fragment_stats where fragment_id = ?", [fragment_id]).fetchdf()
    if row.empty and _has_table(conn, "fragment_search"):
        row = conn.execute("select * from fragment_search where fragment_id = ?", [fragment_id]).fetchdf()
    if row.empty:
        raise HTTPException(status_code=404, detail="Fragment not found")
    record = row.iloc[0].to_dict()
    smiles = record["fragment_smiles"]
    if bool(record.get("has_chembl", True)):
        molecules = conn.execute(
            """
            select m.chembl_id, m.pref_name, m.canonical_smiles, m.mw, m.clogp, m.tpsa, m.qed
            from molecule_fragments mf
            join molecules m using (chembl_id)
            where mf.fragment_id = ?
            order by coalesce(m.qed, 0) desc
            limit 20
            """,
            [fragment_id],
        ).fetchdf()
    else:
        molecules = pd.DataFrame()
    distributions = {}
    for prop in ["mw", "clogp", "tpsa", "hbd", "hba", "rotb", "fsp3", "qed"]:
        if f"{prop}_values" in record and record[f"{prop}_values"]:
            try:
                distributions[prop] = json.loads(record[f"{prop}_values"])
            except TypeError:
                distributions[prop] = record[f"{prop}_values"]
    record["svg"] = smiles_to_svg(smiles)
    if "top_targets" in record and record["top_targets"]:
        try:
            record["top_targets"] = json.loads(record["top_targets"])
        except TypeError:
            pass
    if "admet_summary" in record and record["admet_summary"]:
        try:
            record["admet_summary"] = json.loads(record["admet_summary"])
        except TypeError:
            pass
    if _has_table(conn, "tdc_fragment_admet_stats"):
        clean_admet = conn.execute(
            """
            select source, standard_type, standard_units, measurement_count, molecule_count,
                   task_count, tdc_tasks, favorable_direction, description,
                   mean, median, std, p10, p90
            from tdc_fragment_admet_stats
            where fragment_id = ?
            order by measurement_count desc
            limit 30
            """,
            [fragment_id],
        ).fetchdf()
        record["clean_admet_summary"] = clean_admet.to_dict(orient="records")
    else:
        record["clean_admet_summary"] = []
    record["representative_molecules"] = molecules.to_dict(orient="records")
    record["property_distributions"] = distributions
    return _json_safe(record)


@router.get("/{fragment_id}/molecules")
def get_fragment_molecules(
    fragment_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    conn: duckdb.DuckDBPyConnection = Depends(get_connection),
):
    offset = (page - 1) * page_size
    total = conn.execute("select count(*) from molecule_fragments where fragment_id = ?", [fragment_id]).fetchone()[0]
    rows = conn.execute(
        """
        select m.*
        from molecule_fragments mf
        join molecules m using (chembl_id)
        where mf.fragment_id = ?
        order by m.chembl_id
        limit ? offset ?
        """,
        [fragment_id, page_size, offset],
    ).fetchdf()
    return _json_safe({"items": rows.to_dict(orient="records"), "total": int(total), "page": page, "page_size": page_size})


@router.get("/render/fragment.svg", include_in_schema=False)
def render_fragment_legacy(smiles: str):
    return Response(content=smiles_to_svg(smiles), media_type="image/svg+xml")
