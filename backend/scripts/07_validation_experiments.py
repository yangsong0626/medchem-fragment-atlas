#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.fragment_service import add_missing_descriptors

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "derived" / "fragment_atlas.duckdb"
DERIVED = ROOT / "data" / "derived"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
CASE_DIR = REPORTS / "case_studies"

BLUE = "#1f6fb2"
BLUE_LIGHT = "#d8e9f7"
RED = "#c43c39"
RED_LIGHT = "#f7d9d7"
INK = "#17202a"
MUTED = "#64748b"
LINE = "#d8e0e7"
PANEL = "#f7f9fb"
GREEN = "#0f766e"


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def write_svg(path: Path, width: int, height: int, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
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
""",
        encoding="utf-8",
    )


def rect(x, y, w, h, fill, stroke="none", rx=0, extra="") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" {extra}/>'


def text(x, y, s, cls="label", anchor="start", extra="") -> str:
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}" {extra}>{esc(s)}</text>'


def line(x1, y1, x2, y2, stroke=LINE, width=1.5, extra="") -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}" {extra}/>'


def fmt(value: float | int | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "NA"
    if abs(float(value)) >= 100:
        return f"{float(value):.0f}"
    if abs(float(value)) >= 10:
        return f"{float(value):.1f}"
    return f"{float(value):.{digits}f}"


def has_table(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    count = conn.execute("select count(*) from information_schema.tables where table_name = ?", [table]).fetchone()[0]
    return bool(count)


def read_table(conn: duckdb.DuckDBPyConnection, table: str) -> pd.DataFrame:
    if not has_table(conn, table):
        raise RuntimeError(f"Required DuckDB table is missing: {table}. Run make import-tdc-admet first.")
    return conn.execute(f"select * from {table}").fetchdf()


def ensure_tdc_descriptors(clean: pd.DataFrame, output: Path, force: bool = False) -> pd.DataFrame:
    if output.exists() and not force:
        return pd.read_parquet(output)
    molecules = clean[["tdc_id", "tdc_task", "drug_id", "canonical_smiles"]].drop_duplicates("tdc_id").copy()
    enriched = add_missing_descriptors(molecules)
    valid = enriched[enriched["descriptor_failure"].isna()].copy()
    output.parent.mkdir(parents=True, exist_ok=True)
    valid.to_parquet(output, index=False)
    failures = enriched[enriched["descriptor_failure"].notna()]
    if not failures.empty:
        failures.to_csv(output.with_suffix(".failures.csv"), index=False)
    return valid


def build_joined(clean: pd.DataFrame, mapping: pd.DataFrame, fragments: pd.DataFrame) -> pd.DataFrame:
    return (
        mapping.merge(clean, on="tdc_id", how="inner")
        .merge(fragments[["fragment_id", "fragment_smiles", "display_smiles", "heavy_atom_count"]], on="fragment_id", how="inner")
        .drop_duplicates(["tdc_id", "fragment_id"])
    )


def bootstrap_ci(joined: pd.DataFrame, min_count: int, n_boot: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    group_cols = ["fragment_id", "fragment_smiles", "display_smiles", "standard_type", "standard_units"]
    for keys, group in joined.groupby(group_cols, dropna=False):
        values = pd.to_numeric(group["standard_value"], errors="coerce").dropna().to_numpy(dtype=float)
        if len(values) < min_count:
            continue
        samples = rng.choice(values, size=(n_boot, len(values)), replace=True)
        medians = np.median(samples, axis=1)
        fragment_id, fragment_smiles, display_smiles, standard_type, standard_units = keys
        rows.append(
            {
                "fragment_id": fragment_id,
                "fragment_smiles": fragment_smiles,
                "display_smiles": display_smiles,
                "standard_type": standard_type,
                "standard_units": standard_units,
                "measurement_count": int(len(values)),
                "molecule_count": int(group["tdc_id"].nunique()),
                "task_count": int(group["tdc_task"].nunique()),
                "tdc_tasks": ",".join(sorted(group["tdc_task"].dropna().unique())),
                "median": float(np.median(values)),
                "ci_low": float(np.quantile(medians, 0.025)),
                "ci_high": float(np.quantile(medians, 0.975)),
                "ci_width": float(np.quantile(medians, 0.975) - np.quantile(medians, 0.025)),
                "bootstrap_n": int(n_boot),
            }
        )
    return pd.DataFrame(rows).sort_values(["measurement_count", "ci_width"], ascending=[False, True])


def sign_test_pvalue(deltas: np.ndarray) -> float | None:
    clean = deltas[deltas != 0]
    n = len(clean)
    if n == 0:
        return None
    wins = int((clean > 0).sum())
    mean = n / 2
    sd = math.sqrt(n / 4)
    z = (abs(wins - mean) - 0.5) / sd if sd else 0
    return float(math.erfc(abs(z) / math.sqrt(2)))


def matched_context(
    clean: pd.DataFrame,
    mapping: pd.DataFrame,
    fragments: pd.DataFrame,
    descriptors: pd.DataFrame,
    stats: pd.DataFrame,
    min_cases: int,
    max_fragment_endpoints: int,
    max_cases_per_group: int,
    distance_cutoff: float,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    clean_desc = clean.merge(descriptors, on=["tdc_id", "tdc_task", "drug_id", "canonical_smiles"], how="inner")
    selected = stats[stats["measurement_count"] >= min_cases].sort_values("measurement_count", ascending=False).head(max_fragment_endpoints)
    feature_cols = ["mw", "clogp", "tpsa", "hbd", "hba", "rotb"]
    rows: list[dict] = []

    for stat in selected.itertuples(index=False):
        fragment_maps = mapping[mapping["fragment_id"] == stat.fragment_id][["tdc_id"]].drop_duplicates()
        task_names = [task for task in str(stat.tdc_tasks).split(",") if task]
        for task_name in task_names:
            task_df = clean_desc[
                (clean_desc["tdc_task"] == task_name)
                & (clean_desc["standard_type"] == stat.standard_type)
                & (clean_desc["standard_units"].fillna("") == ("" if pd.isna(stat.standard_units) else stat.standard_units))
            ].copy()
            if task_df.empty:
                continue
            task_df["has_fragment"] = task_df["tdc_id"].isin(fragment_maps["tdc_id"])
            cases = task_df[task_df["has_fragment"]].drop_duplicates("tdc_id").copy()
            controls = task_df[~task_df["has_fragment"]].drop_duplicates("tdc_id").copy()
            if len(cases) < min_cases or len(controls) < min_cases:
                continue
            if len(cases) > max_cases_per_group:
                cases = cases.sample(max_cases_per_group, random_state=seed)

            feature_frame = pd.concat([cases[feature_cols], controls[feature_cols]], ignore_index=True)
            scale = feature_frame.std(ddof=0).replace(0, 1).fillna(1)
            center = feature_frame.mean().fillna(0)
            case_x = ((cases[feature_cols] - center) / scale).to_numpy(dtype=float)
            control_x = ((controls[feature_cols] - center) / scale).to_numpy(dtype=float)
            case_values = cases["standard_value"].to_numpy(dtype=float)
            control_values = controls["standard_value"].to_numpy(dtype=float)

            used: set[int] = set()
            pairs = []
            order = rng.permutation(len(cases))
            for case_idx in order:
                distances = np.sqrt(((control_x - case_x[case_idx]) ** 2).sum(axis=1))
                if used and len(used) < len(distances):
                    distances[list(used)] = np.inf
                control_idx = int(np.argmin(distances))
                if not np.isfinite(distances[control_idx]) or distances[control_idx] > distance_cutoff:
                    continue
                used.add(control_idx)
                pairs.append((case_idx, control_idx, float(distances[control_idx])))

            if len(pairs) < min_cases:
                continue
            case_idx = np.array([pair[0] for pair in pairs], dtype=int)
            control_idx = np.array([pair[1] for pair in pairs], dtype=int)
            distances = np.array([pair[2] for pair in pairs], dtype=float)
            raw_deltas = case_values[case_idx] - control_values[control_idx]
            if stat.favorable_direction == "low":
                favorable_deltas = -raw_deltas
            elif stat.favorable_direction == "high":
                favorable_deltas = raw_deltas
            else:
                favorable_deltas = -np.abs(raw_deltas)

            rows.append(
                {
                    "fragment_id": stat.fragment_id,
                    "fragment_smiles": stat.fragment_smiles,
                    "display_smiles": stat.display_smiles,
                    "standard_type": stat.standard_type,
                    "standard_units": stat.standard_units,
                    "tdc_task": task_name,
                    "favorable_direction": stat.favorable_direction,
                    "description": stat.description,
                    "n_pairs": int(len(pairs)),
                    "case_median": float(np.median(case_values[case_idx])),
                    "control_median": float(np.median(control_values[control_idx])),
                    "raw_median_delta": float(np.median(raw_deltas)),
                    "raw_mean_delta": float(np.mean(raw_deltas)),
                    "favorable_median_delta": float(np.median(favorable_deltas)),
                    "favorable_mean_delta": float(np.mean(favorable_deltas)),
                    "match_distance_median": float(np.median(distances)),
                    "sign_test_pvalue": sign_test_pvalue(favorable_deltas),
                }
            )
    return pd.DataFrame(rows).sort_values(["n_pairs", "favorable_median_delta"], ascending=[False, False])


def select_case_studies(matched: pd.DataFrame, ci: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if matched.empty:
        return pd.DataFrame()
    enriched = matched.merge(
        ci[["fragment_id", "standard_type", "standard_units", "median", "ci_low", "ci_high", "ci_width"]],
        on=["fragment_id", "standard_type", "standard_units"],
        how="left",
        suffixes=("", "_bootstrap"),
    )
    candidates = enriched[(enriched["n_pairs"] >= 20) & (enriched["favorable_direction"].isin(["high", "low"]))].copy()
    if candidates.empty:
        candidates = enriched[enriched["favorable_direction"].isin(["high", "low"])].copy()
    if candidates.empty:
        return pd.DataFrame()

    def take_diverse(pool: pd.DataFrame, target: int) -> pd.DataFrame:
        selected = []
        endpoint_counts: dict[str, int] = {}
        fragment_endpoint_seen: set[tuple[str, str]] = set()
        for _, row in pool.iterrows():
            endpoint = str(row["standard_type"])
            key = (str(row["fragment_id"]), endpoint)
            if endpoint_counts.get(endpoint, 0) >= 2 or key in fragment_endpoint_seen:
                continue
            selected.append(row)
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
            fragment_endpoint_seen.add(key)
            if len(selected) >= target:
                break
        return pd.DataFrame(selected)

    favorable = take_diverse(candidates.sort_values(["favorable_median_delta", "n_pairs"], ascending=[False, False]), limit // 2)
    unfavorable = take_diverse(candidates.sort_values(["favorable_median_delta", "n_pairs"], ascending=[True, False]), limit - len(favorable))
    out = pd.concat([favorable, unfavorable], ignore_index=True).drop_duplicates(["fragment_id", "standard_type", "tdc_task"])
    out["case_direction"] = np.where(out["favorable_median_delta"] >= 0, "favorable association", "unfavorable association")
    return out.head(limit)


def write_case_study_markdown(cases: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if cases.empty:
        output.write_text("# Fragment ADMET Case Studies\n\nNo matched-context case studies passed the current thresholds.\n", encoding="utf-8")
        return
    lines = [
        "# Fragment ADMET Case Studies",
        "",
        "These case studies are association analyses. ADMET values are measured or curated on parent molecules containing a BRICS fragment, not on the isolated fragment itself.",
        "",
    ]
    for idx, row in enumerate(cases.itertuples(index=False), start=1):
        lines.extend(
            [
                f"## Case {idx}: `{row.display_smiles}` and {row.standard_type}",
                "",
                f"- Direction: {row.case_direction}",
                f"- Endpoint/task: {row.standard_type} ({row.standard_units or 'unitless'}), `{row.tdc_task}`",
                f"- Matched pairs: {row.n_pairs}",
                f"- Parent median with fragment: {fmt(row.case_median)}",
                f"- Matched-control median: {fmt(row.control_median)}",
                f"- Favorability-adjusted median delta: {fmt(row.favorable_median_delta)}",
                f"- Bootstrap median CI: {fmt(row.ci_low)} to {fmt(row.ci_high)}",
                f"- Match distance median: {fmt(row.match_distance_median)}",
                "",
                f"Interpretation: molecules containing `{row.display_smiles}` show {'a' if row.case_direction.startswith('favorable') else 'an'} {row.case_direction} for {row.standard_type} after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.",
                "",
            ]
        )
    output.write_text("\n".join(lines), encoding="utf-8")


def figure_bootstrap(ci: pd.DataFrame) -> None:
    if ci.empty:
        return
    subset = (
        ci[(ci["measurement_count"] >= 50)]
        .sort_values(["ci_width", "measurement_count"], ascending=[True, False])
        .head(14)
        .sort_values("median")
    )
    if subset.empty:
        subset = ci.head(14).sort_values("median")
    width, height = 1450, 720
    parts = [text(55, 55, "Figure 8. Bootstrap Confidence Intervals for Fragment ADMET Medians", "title")]
    x0, y0, plot_w, row_h = 520, 115, 760, 38
    low = float(subset["ci_low"].min())
    high = float(subset["ci_high"].max())
    if low == high:
        high = low + 1
    for i, row in enumerate(subset.itertuples(index=False)):
        y = y0 + i * row_h
        label = f"{row.display_smiles} | {row.standard_type}"
        if len(label) > 62:
            label = label[:59] + "..."
        parts.append(text(55, y + 22, label, "small"))
        x_low = x0 + (row.ci_low - low) / (high - low) * plot_w
        x_med = x0 + (row.median - low) / (high - low) * plot_w
        x_high = x0 + (row.ci_high - low) / (high - low) * plot_w
        parts.append(line(x_low, y + 16, x_high, y + 16, BLUE, 3))
        parts.append(rect(x_med - 4, y + 8, 8, 16, BLUE, rx=2))
        parts.append(text(x_high + 10, y + 20, f"n={row.measurement_count}", "axis"))
    parts.append(line(x0, y0 + len(subset) * row_h + 10, x0 + plot_w, y0 + len(subset) * row_h + 10, LINE))
    parts.append(text(x0, y0 + len(subset) * row_h + 34, fmt(low), "axis", "middle"))
    parts.append(text(x0 + plot_w, y0 + len(subset) * row_h + 34, fmt(high), "axis", "middle"))
    parts.append(text(55, 665, "Intervals are percentile bootstrap 95% confidence intervals for median parent-molecule endpoint values.", "subtitle"))
    write_svg(FIGURES / "figure_8_bootstrap_ci.svg", width, height, "\n".join(parts))


def figure_matched(matched: pd.DataFrame) -> None:
    if matched.empty:
        return
    plot_df = matched[matched["favorable_direction"].isin(["high", "low"])].copy()
    if plot_df.empty:
        plot_df = matched.copy()
    top_pos = plot_df.sort_values(["favorable_median_delta", "n_pairs"], ascending=[False, False]).head(8)
    top_neg = plot_df.sort_values(["favorable_median_delta", "n_pairs"], ascending=[True, False]).head(8)
    subset = pd.concat([top_neg, top_pos], ignore_index=True).drop_duplicates(["fragment_id", "standard_type", "tdc_task"])
    subset = subset.sort_values("favorable_median_delta")
    width, height = 1500, 760
    parts = [text(55, 55, "Figure 9. Matched-Context Fragment ADMET Associations", "title")]
    x_mid, y0, plot_w, row_h = 760, 115, 610, 34
    max_abs = max(1e-9, float(subset["favorable_median_delta"].abs().max()))
    parts.append(line(x_mid, y0 - 10, x_mid, y0 + len(subset) * row_h, LINE, 1.5))
    for i, row in enumerate(subset.itertuples(index=False)):
        y = y0 + i * row_h
        label = f"{row.display_smiles} | {row.standard_type}"
        if len(label) > 58:
            label = label[:55] + "..."
        parts.append(text(55, y + 21, label, "small"))
        width_bar = abs(row.favorable_median_delta) / max_abs * plot_w / 2
        if row.favorable_median_delta >= 0:
            parts.append(rect(x_mid, y + 5, width_bar, 20, BLUE, rx=3))
            parts.append(text(x_mid + width_bar + 8, y + 20, f"+{fmt(row.favorable_median_delta)} | pairs={row.n_pairs}", "axis"))
        else:
            parts.append(rect(x_mid - width_bar, y + 5, width_bar, 20, RED, rx=3))
            parts.append(text(x_mid - width_bar - 8, y + 20, f"{fmt(row.favorable_median_delta)} | pairs={row.n_pairs}", "axis", "end"))
    parts.append(rect(1060, 63, 34, 14, BLUE, rx=2))
    parts.append(text(1100, 75, "more favorable vs matched controls", "axis"))
    parts.append(rect(55, 690, 34, 14, RED, rx=2))
    parts.append(text(95, 702, "less favorable vs matched controls; deltas are adjusted to endpoint directionality.", "subtitle"))
    write_svg(FIGURES / "figure_9_matched_context_validation.svg", width, height, "\n".join(parts))


def figure_cases(cases: pd.DataFrame) -> None:
    if cases.empty:
        return
    subset = cases.head(6)
    width, height = 1500, 760
    parts = [text(55, 55, "Figure 10. Publication-Style Fragment Case Studies", "title")]
    x0, y0, w, h, gap = 55, 115, 450, 245, 28
    for i, row in enumerate(subset.itertuples(index=False)):
        x = x0 + (i % 3) * (w + gap)
        y = y0 + (i // 3) * (h + gap)
        fill = BLUE_LIGHT if row.favorable_median_delta >= 0 else RED_LIGHT
        parts.append(rect(x, y, w, h, fill, LINE, 8))
        label = row.display_smiles if len(row.display_smiles) <= 42 else row.display_smiles[:39] + "..."
        parts.append(text(x + 18, y + 34, label, "label", extra='font-weight="700"'))
        parts.append(text(x + 18, y + 62, f"{row.standard_type} | {row.tdc_task}", "small"))
        fields = [
            ("Matched pairs", row.n_pairs),
            ("Case median", fmt(row.case_median)),
            ("Control median", fmt(row.control_median)),
            ("Favorable delta", fmt(row.favorable_median_delta)),
            ("Bootstrap CI", f"{fmt(row.ci_low)} to {fmt(row.ci_high)}"),
        ]
        for n, (name, value) in enumerate(fields):
            yy = y + 98 + n * 26
            parts.append(text(x + 18, yy, name, "axis"))
            parts.append(text(x + w - 18, yy, value, "small", "end", 'font-weight="700"'))
    parts.append(text(55, 710, "Cards combine matched-context effects with bootstrap uncertainty. They are intended as medicinal chemistry hypotheses, not causal fragment liabilities.", "subtitle"))
    write_svg(FIGURES / "figure_10_case_study_panels.svg", width, height, "\n".join(parts))


def write_outputs(
    conn: duckdb.DuckDBPyConnection,
    ci: pd.DataFrame,
    matched: pd.DataFrame,
    cases: pd.DataFrame,
    ci_output: Path,
    matched_output: Path,
    cases_output: Path,
) -> None:
    for path in [ci_output, matched_output, cases_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    ci.to_parquet(ci_output, index=False)
    matched.to_parquet(matched_output, index=False)
    cases.to_csv(cases_output, index=False)

    conn.register("ci_df", ci)
    conn.register("matched_df", matched)
    conn.register("cases_df", cases)
    conn.execute("create or replace table tdc_fragment_admet_bootstrap_ci as select * from ci_df")
    conn.execute("create or replace table tdc_fragment_admet_matched_context as select * from matched_df")
    conn.execute("create or replace table fragment_admet_case_studies as select * from cases_df")
    conn.execute("create index if not exists idx_tdc_bootstrap_fragment on tdc_fragment_admet_bootstrap_ci(fragment_id)")
    conn.execute("create index if not exists idx_tdc_matched_fragment on tdc_fragment_admet_matched_context(fragment_id)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run publication-strength validation analyses for the fragment ADMET atlas.")
    parser.add_argument("--duckdb", type=Path, default=DB)
    parser.add_argument("--descriptor-output", type=Path, default=DERIVED / "tdc_molecules_with_descriptors.parquet")
    parser.add_argument("--bootstrap-output", type=Path, default=DERIVED / "tdc_fragment_admet_bootstrap_ci.parquet")
    parser.add_argument("--matched-output", type=Path, default=DERIVED / "tdc_fragment_admet_matched_context.parquet")
    parser.add_argument("--case-output", type=Path, default=TABLES / "fragment_admet_case_studies.csv")
    parser.add_argument("--case-markdown", type=Path, default=CASE_DIR / "fragment_admet_case_studies.md")
    parser.add_argument("--bootstrap-min-count", type=int, default=20)
    parser.add_argument("--bootstrap-n", type=int, default=300)
    parser.add_argument("--matched-min-cases", type=int, default=20)
    parser.add_argument("--matched-max-fragment-endpoints", type=int, default=450)
    parser.add_argument("--matched-max-cases-per-group", type=int, default=400)
    parser.add_argument("--matched-distance-cutoff", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--force-descriptors", action="store_true")
    args = parser.parse_args()

    conn = duckdb.connect(str(args.duckdb))
    clean = read_table(conn, "tdc_admet_measurements")
    mapping = read_table(conn, "tdc_molecule_fragments")
    fragments = read_table(conn, "tdc_fragments")
    stats = read_table(conn, "tdc_fragment_admet_stats")

    descriptors = ensure_tdc_descriptors(clean, args.descriptor_output, force=args.force_descriptors)
    joined = build_joined(clean, mapping, fragments)
    ci = bootstrap_ci(joined, min_count=args.bootstrap_min_count, n_boot=args.bootstrap_n, seed=args.seed)
    matched = matched_context(
        clean=clean,
        mapping=mapping,
        fragments=fragments,
        descriptors=descriptors,
        stats=stats,
        min_cases=args.matched_min_cases,
        max_fragment_endpoints=args.matched_max_fragment_endpoints,
        max_cases_per_group=args.matched_max_cases_per_group,
        distance_cutoff=args.matched_distance_cutoff,
        seed=args.seed,
    )
    cases = select_case_studies(matched, ci)

    write_outputs(conn, ci, matched, cases, args.bootstrap_output, args.matched_output, args.case_output)
    conn.close()
    write_case_study_markdown(cases, args.case_markdown)
    figure_bootstrap(ci)
    figure_matched(matched)
    figure_cases(cases)

    print(f"Wrote {len(ci):,} bootstrap CI rows to {args.bootstrap_output}")
    print(f"Wrote {len(matched):,} matched-context rows to {args.matched_output}")
    print(f"Wrote {len(cases):,} case studies to {args.case_output}")
    print(f"Wrote case-study narrative to {args.case_markdown}")


if __name__ == "__main__":
    main()
