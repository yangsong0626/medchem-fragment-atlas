#!/usr/bin/env python
from __future__ import annotations

import html
import math
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "figures"
DB = ROOT / "data" / "derived" / "fragment_atlas.duckdb"

BLUE = "#1f6fb2"
BLUE_LIGHT = "#d8e9f7"
RED = "#c43c39"
RED_LIGHT = "#f7d9d7"
INK = "#17202a"
MUTED = "#64748b"
LINE = "#d8e0e7"
PANEL = "#f7f9fb"
GREEN = "#0f766e"


def esc(text) -> str:
    return html.escape("" if text is None else str(text))


def write_svg(path: Path, width: int, height: int, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="white"/>
  <style>
    text {{ font-family: Inter, Arial, sans-serif; fill: {INK}; }}
    .title {{ font-size: 24px; font-weight: 700; }}
    .subtitle {{ font-size: 13px; fill: {MUTED}; }}
    .axis {{ font-size: 11px; fill: {MUTED}; }}
    .label {{ font-size: 12px; }}
    .small {{ font-size: 10px; fill: {MUTED}; }}
  </style>
  {body}
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def rect(x, y, w, h, fill, stroke="none", rx=0, extra="") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" {extra}/>'


def text(x, y, s, cls="label", anchor="start", extra="") -> str:
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}" {extra}>{esc(s)}</text>'


def line(x1, y1, x2, y2, stroke=LINE, width=1.5, extra="") -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}" {extra}/>'


def color_scale(value: float, vmin: float, vmax: float, low=RED, high=BLUE) -> str:
    if value is None or pd.isna(value):
        return "#eef2f6"
    if vmax == vmin:
        t = 0.5
    else:
        t = max(0, min(1, (value - vmin) / (vmax - vmin)))
    lo = tuple(int(low[i : i + 2], 16) for i in (1, 3, 5))
    hi = tuple(int(high[i : i + 2], 16) for i in (1, 3, 5))
    rgb = tuple(round(lo[i] + (hi[i] - lo[i]) * t) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def favorable_color(score: float | None) -> str:
    if score is None or pd.isna(score):
        return "#eef2f6"
    if score >= 0.75:
        return BLUE
    if score >= 0.5:
        return "#8dc1e8"
    if score >= 0.25:
        return "#eda09b"
    return RED


def favorable_score(value: float | None, direction: str, good: float, bad: float) -> float | None:
    if value is None or pd.isna(value):
        return None
    if direction == "high":
        return max(0, min(1, (value - bad) / (good - bad)))
    return max(0, min(1, (bad - value) / (bad - good)))


def load_data():
    conn = duckdb.connect(str(DB), read_only=True)
    def read_table(name: str) -> pd.DataFrame:
        exists = conn.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0]
        return conn.execute(f"select * from {name}").fetchdf() if exists else pd.DataFrame()

    tables = {
        "molecules": read_table("molecules"),
        "fragments": read_table("fragments"),
        "mapping": read_table("molecule_fragments"),
        "stats": read_table("fragment_stats"),
        "admet": read_table("admet_measurements"),
        "admet_stats": read_table("fragment_admet_stats"),
        "tdc_admet": read_table("tdc_admet_measurements"),
        "tdc_admet_stats": read_table("tdc_fragment_admet_stats"),
    }
    conn.close()
    return tables


def figure_workflow() -> None:
    width, height = 1500, 520
    steps = [
        ("ChEMBL molecules", "SMILES, properties, assays"),
        ("RDKit validation", "invalid molecules logged"),
        ("BRICS decomposition", "dummy atoms retained"),
        ("Canonical fragments", "fragment_smiles + display_smiles"),
        ("Parent aggregation", "descriptors + endpoint stats"),
        ("DuckDB/API/UI", "search, SVGs, heatmaps"),
    ]
    parts = [text(50, 58, "Figure 1. MedChem Fragment Atlas Workflow", "title")]
    x, y, w, h, gap = 55, 160, 195, 115, 45
    for i, (label, sub) in enumerate(steps):
        xi = x + i * (w + gap)
        parts.append(rect(xi, y, w, h, PANEL, LINE, 8))
        parts.append(text(xi + w / 2, y + 46, label, "label", "middle", 'font-weight="700"'))
        parts.append(text(xi + w / 2, y + 76, sub, "small", "middle"))
        if i < len(steps) - 1:
            x1, x2 = xi + w + 8, xi + w + gap - 8
            parts.append(line(x1, y + h / 2, x2, y + h / 2, GREEN, 2))
            parts.append(f'<path d="M{x2},{y+h/2} l-9,-6 v12 z" fill="{GREEN}"/>')
    parts.append(text(55, 380, "Design principle: all physicochemical and ADMET values are aggregated from parent molecules containing the fragment, not measured or predicted properties of isolated fragments.", "subtitle"))
    write_svg(OUT / "figure_1_workflow.svg", width, height, "\n".join(parts))


def figure_summary(tables) -> None:
    counts = [
        ("Parent molecules", len(tables["molecules"])),
        ("Unique fragments", len(tables["fragments"])),
        ("Molecule-fragment maps", len(tables["mapping"])),
        ("Raw ChEMBL ADMET rows", len(tables["admet"])),
        ("Clean TDC ADMET rows", len(tables["tdc_admet"])),
        ("Clean TDC endpoint rollups", len(tables["tdc_admet_stats"])),
    ]
    width, height = 1200, 620
    parts = [text(55, 55, "Figure 2. Prototype Atlas Summary", "title")]
    maxv = max(v for _, v in counts)
    x0, y0, bar_h, gap = 290, 120, 54, 32
    for i, (label, value) in enumerate(counts):
        y = y0 + i * (bar_h + gap)
        bw = 760 * math.sqrt(value / maxv)
        parts.append(text(55, y + 34, label, "label"))
        parts.append(rect(x0, y, bw, bar_h, GREEN, rx=4))
        parts.append(text(x0 + bw + 14, y + 34, f"{value:,}", "label"))
    hac = tables["fragments"]["heavy_atom_count"].value_counts().sort_index()
    sx, sy = 55, 500
    parts.append(text(sx, sy - 30, "Fragment heavy atom count distribution", "subtitle"))
    max_count = hac.max()
    for idx, (ha, count) in enumerate(hac.items()):
        bx = sx + idx * 34
        bh = 75 * count / max_count
        parts.append(rect(bx, sy - bh, 20, bh, BLUE, rx=2))
        if idx % 2 == 0:
            parts.append(text(bx + 10, sy + 18, ha, "axis", "middle"))
    parts.append(line(sx, sy, sx + len(hac) * 34, sy, LINE))
    write_svg(OUT / "figure_2_summary.svg", width, height, "\n".join(parts))


def figure_top_fragments(tables) -> None:
    stats = tables["stats"].sort_values("parent_count", ascending=False).head(20).copy()
    width, height = 1500, 900
    parts = [text(55, 55, "Figure 3. Most Frequent BRICS Fragments", "title")]
    x0, y0, maxw, row_h = 470, 100, 880, 34
    maxv = stats["parent_count"].max()
    for i, row in stats.iterrows():
        rank = len(parts)
    for n, (_, row) in enumerate(stats.iterrows(), start=1):
        y = y0 + (n - 1) * row_h
        label = row["display_smiles"]
        if len(label) > 42:
            label = label[:39] + "..."
        parts.append(text(55, y + 21, f"{n:02d}", "axis"))
        parts.append(text(100, y + 21, label, "small"))
        bw = maxw * row["parent_count"] / maxv
        parts.append(rect(x0, y, bw, 22, BLUE, rx=3))
        parts.append(text(x0 + bw + 10, y + 17, f"{int(row['parent_count'])} parents | {int(row['admet_measurement_count'])} endpoints rows", "axis"))
    parts.append(text(55, 835, "Fragments are ranked by unique parent molecule count. BRICS attachment labels are normalized for display.", "subtitle"))
    write_svg(OUT / "figure_3_top_fragments.svg", width, height, "\n".join(parts))


def figure_descriptor_heatmap(tables) -> None:
    stats = tables["stats"].sort_values(["parent_count", "admet_measurement_count"], ascending=False).head(20).copy()
    cols = [
        ("MW", "mw_median"),
        ("LogP", "clogp_median"),
        ("TPSA", "tpsa_median"),
        ("HBD", "hbd_median"),
        ("HBA", "hba_median"),
        ("RotB", "rotb_median"),
        ("Fsp3", "fsp3_median"),
        ("QED", "qed_median"),
    ]
    width, height = 1500, 920
    parts = [text(55, 55, "Figure 4. Parent-Molecule Descriptor Medians by Fragment", "title")]
    x0, y0, cw, ch = 390, 105, 105, 34
    for j, (label, _) in enumerate(cols):
        parts.append(text(x0 + j * cw + cw / 2, y0 - 16, label, "axis", "middle"))
    for i, (_, row) in enumerate(stats.iterrows()):
        y = y0 + i * ch
        label = row["display_smiles"]
        if len(label) > 44:
            label = label[:41] + "..."
        parts.append(text(55, y + 22, label, "small"))
        for j, (_, col) in enumerate(cols):
            values = pd.to_numeric(stats[col], errors="coerce")
            fill = color_scale(row[col], values.quantile(0.05), values.quantile(0.95))
            parts.append(rect(x0 + j * cw, y, cw - 3, ch - 3, fill))
            parts.append(text(x0 + j * cw + cw / 2, y + 21, f"{row[col]:.1f}" if pd.notna(row[col]) else "NA", "small", "middle", 'fill="white"' if fill in [BLUE, RED] else ""))
    parts.append(text(55, 840, "Values are medians of parent molecules containing each fragment. Blue/red reflect relative scale within this selected fragment set, not intrinsic fragment properties.", "subtitle"))
    write_svg(OUT / "figure_4_descriptor_heatmap.svg", width, height, "\n".join(parts))


ADMET_METRICS = [
    ("CL", {"cl", "clearance", "clint", "clrenal"}, "low", 5, 20),
    ("Papp", {"papp", "caco2", "pampa", "permeability"}, "high", 10, 2),
    ("Absorption", {"absorption", "f", "f%", "ba", "bioavailability", "fa"}, "high", 70, 30),
    ("Solubility", {"solubility"}, "high", 50, 5),
    ("hERG", {"herg"}, "high", 10000, 1000),
]


def metric_row(endpoint_rows: pd.DataFrame, metric) -> pd.Series | None:
    _, aliases, _, _, _ = metric
    if endpoint_rows.empty:
        return None
    tmp = endpoint_rows.copy()
    tmp["_norm"] = tmp["standard_type"].fillna("").str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    selected = tmp[tmp["_norm"].isin(aliases)].sort_values("measurement_count", ascending=False)
    if selected.empty:
        return None
    return selected.iloc[0]


def figure_admet_heatmap(tables) -> None:
    if not tables["tdc_admet_stats"].empty:
        admet = tables["tdc_admet_stats"]
        ranked = (
            admet.groupby(["fragment_id", "display_smiles"], as_index=False)["measurement_count"]
            .sum()
            .sort_values("measurement_count", ascending=False)
            .head(16)
        )
        title = "Figure 5. Clean TDC ADMET Endpoint Heatmap"
        note = "Median clean TDC values are mapped onto BRICS fragments. Color uses endpoint-specific directionality; gray indicates no matched clean TDC endpoint."
    else:
        stats = tables["stats"].sort_values("admet_measurement_count", ascending=False).head(16)
        admet = tables["admet_stats"]
        ranked = stats[["fragment_id", "display_smiles", "admet_measurement_count"]].rename(columns={"admet_measurement_count": "measurement_count"})
        title = "Figure 5. Common ADMET Endpoint Heatmap"
        note = "Median ChEMBL assay-derived values are mapped onto BRICS fragments. Color uses endpoint-specific directionality; gray indicates no matched endpoint."
    width, height = 1450, 760
    parts = [text(55, 55, title, "title")]
    x0, y0, cw, ch = 380, 115, 145, 38
    for j, (label, *_rest) in enumerate(ADMET_METRICS):
        parts.append(text(x0 + j * cw + cw / 2, y0 - 18, label, "axis", "middle"))
    for i, (_, frag) in enumerate(ranked.iterrows()):
        y = y0 + i * ch
        label = frag["display_smiles"]
        if len(label) > 42:
            label = label[:39] + "..."
        parts.append(text(55, y + 24, label, "small"))
        endpoint_rows = admet[admet["fragment_id"] == frag["fragment_id"]]
        for j, metric in enumerate(ADMET_METRICS):
            _, _, direction, good, bad = metric
            row = metric_row(endpoint_rows, metric)
            median = None if row is None else row["median"]
            fill = favorable_color(favorable_score(median, direction, good, bad))
            txt = "NA" if median is None or pd.isna(median) else f"{median:.1f}"
            parts.append(rect(x0 + j * cw, y, cw - 4, ch - 4, fill))
            text_fill = 'fill="white"' if fill in [BLUE, RED] else ""
            parts.append(text(x0 + j * cw + cw / 2, y + 24, txt, "small", "middle", text_fill))
    parts.append(rect(1040, 63, 34, 14, RED, rx=2))
    parts.append(text(1080, 75, "less favorable", "axis"))
    parts.append(rect(1190, 63, 34, 14, BLUE, rx=2))
    parts.append(text(1230, 75, "more favorable", "axis"))
    parts.append(text(55, 715, note, "subtitle"))
    write_svg(OUT / "figure_5_admet_heatmap.svg", width, height, "\n".join(parts))


def figure_case_studies(tables) -> None:
    preferred = ["[16*]c1ccccc1", "[15*]C1CC1", "[5*]N1CCN([5*])CC1", "[12*]S(C)(=O)=O", "[6*]C(=O)O"]
    stats = tables["stats"]
    rows = []
    for smi in preferred:
        hit = stats[stats["fragment_smiles"] == smi]
        if not hit.empty:
            rows.append(hit.iloc[0])
    if len(rows) < 5:
        rows.extend([r for _, r in stats.sort_values("admet_measurement_count", ascending=False).head(5).iterrows() if r["fragment_id"] not in {x["fragment_id"] for x in rows}])
    rows = rows[:5]
    width, height = 1400, 620
    parts = [text(55, 55, "Figure 6. Fragment Case Studies", "title")]
    x0, y0, w, h, gap = 55, 105, 245, 390, 22
    for i, row in enumerate(rows):
        x = x0 + i * (w + gap)
        parts.append(rect(x, y0, w, h, PANEL, LINE, 8))
        label = row["display_smiles"]
        if len(label) > 28:
            label = label[:25] + "..."
        parts.append(text(x + 18, y0 + 34, label, "small"))
        fields = [
            ("Parents", int(row["parent_count"])),
            ("ADMET rows", int(row["admet_measurement_count"])),
            ("Endpoints", int(row["admet_endpoint_count"])),
            ("MW median", f"{row['mw_median']:.1f}"),
            ("LogP median", f"{row['clogp_median']:.2f}"),
            ("QED median", f"{row['qed_median']:.2f}"),
        ]
        for n, (name, value) in enumerate(fields):
            yy = y0 + 78 + n * 42
            parts.append(text(x + 18, yy, name, "axis"))
            parts.append(text(x + w - 18, yy, value, "label", "end", 'font-weight="700"'))
        parts.append(rect(x + 18, y0 + 345, min(195, row["admet_measurement_count"] / max(1, stats["admet_measurement_count"].max()) * 195), 18, GREEN, rx=3))
        parts.append(text(x + 18, y0 + 385, "ADMET coverage", "small"))
    parts.append(text(55, 560, "Example fragment cards summarize structural motif frequency, descriptor context, and endpoint coverage for medicinal chemistry triage.", "subtitle"))
    write_svg(OUT / "figure_6_case_studies.svg", width, height, "\n".join(parts))


def main() -> None:
    tables = load_data()
    figure_workflow()
    figure_summary(tables)
    figure_top_fragments(tables)
    figure_descriptor_heatmap(tables)
    figure_admet_heatmap(tables)
    figure_case_studies(tables)
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
