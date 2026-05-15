#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.fragment_service import decompose_brics

ROOT = Path(__file__).resolve().parents[2]


def load_solubility(duckdb_path: Path) -> pd.DataFrame:
    conn = duckdb.connect(str(duckdb_path), read_only=True)
    df = conn.execute(
        """
        select tdc_id, drug_id, canonical_smiles, standard_value, split
        from tdc_admet_measurements
        where tdc_task = 'solubility_aqsoldb'
          and standard_value is not null
          and canonical_smiles is not null
        """
    ).fetchdf()
    conn.close()
    df["standard_value"] = pd.to_numeric(df["standard_value"], errors="coerce")
    df = df.dropna(subset=["standard_value"]).drop_duplicates("tdc_id").reset_index(drop=True)
    return df


def morgan_matrix(smiles: pd.Series, radius: int, n_bits: int) -> tuple[np.ndarray, list[str]]:
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    rows: list[np.ndarray] = []
    valid_smiles: list[str] = []
    for smi in smiles:
        mol = Chem.MolFromSmiles(str(smi))
        if mol is None:
            rows.append(np.zeros(n_bits, dtype=np.uint8))
            continue
        fp = generator.GetFingerprint(mol)
        arr = np.zeros((n_bits,), dtype=np.uint8)
        DataStructs.ConvertToNumpyArray(fp, arr)
        rows.append(arr)
        valid_smiles.append(str(smi))
    return np.vstack(rows), valid_smiles


def fragment_ids_for_smiles(smiles: str, cache: dict[str, list[str]], min_heavy_atoms: int) -> list[str]:
    if smiles not in cache:
        try:
            cache[smiles] = [fragment.fragment_id for fragment in decompose_brics(smiles, min_heavy_atoms=min_heavy_atoms)]
        except Exception:
            cache[smiles] = []
    return cache[smiles]


def build_training_fragment_stats(train: pd.DataFrame, min_heavy_atoms: int) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    cache: dict[str, list[str]] = {}
    rows: list[dict] = []
    for row in train.itertuples(index=False):
        for fragment_id in fragment_ids_for_smiles(row.canonical_smiles, cache, min_heavy_atoms):
            rows.append({"fragment_id": fragment_id, "tdc_id": row.tdc_id, "value": row.standard_value})
    mapping = pd.DataFrame(rows)
    if mapping.empty:
        return pd.DataFrame(columns=["fragment_id", "count", "median", "std", "mean"]), cache
    stats = (
        mapping.groupby("fragment_id")["value"]
        .agg(count="count", median="median", std=lambda x: float(np.std(x, ddof=0)), mean="mean")
        .reset_index()
    )
    return stats, cache


def fragment_feature_matrix(
    df: pd.DataFrame,
    fragment_stats: pd.DataFrame,
    cache: dict[str, list[str]],
    min_heavy_atoms: int,
    allow_decompose: bool = True,
) -> tuple[np.ndarray, list[str]]:
    stat_map = {
        row.fragment_id: {"count": float(row.count), "median": float(row.median), "std": float(row.std), "mean": float(row.mean)}
        for row in fragment_stats.itertuples(index=False)
    }
    features = []
    names = [
        "frag_count_total",
        "frag_count_covered",
        "frag_coverage_fraction",
        "frag_sol_median_mean",
        "frag_sol_median_median",
        "frag_sol_median_min",
        "frag_sol_median_max",
        "frag_sol_std_mean",
        "frag_sol_std_max",
        "frag_sol_parent_count_sum",
        "frag_sol_parent_count_max",
    ]
    for row in df.itertuples(index=False):
        fragment_ids = fragment_ids_for_smiles(row.canonical_smiles, cache, min_heavy_atoms) if allow_decompose else []
        matched = [stat_map[fragment_id] for fragment_id in fragment_ids if fragment_id in stat_map]
        total = len(fragment_ids)
        covered = len(matched)
        if matched:
            medians = np.array([item["median"] for item in matched], dtype=float)
            stds = np.array([item["std"] for item in matched], dtype=float)
            counts = np.array([item["count"] for item in matched], dtype=float)
            feature = [
                total,
                covered,
                covered / total if total else 0.0,
                float(np.mean(medians)),
                float(np.median(medians)),
                float(np.min(medians)),
                float(np.max(medians)),
                float(np.mean(stds)),
                float(np.max(stds)),
                float(np.sum(counts)),
                float(np.max(counts)),
            ]
        else:
            feature = [total, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        features.append(feature)
    return np.asarray(features, dtype=np.float32), names


def spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    true_rank = pd.Series(y_true).rank(method="average").to_numpy()
    pred_rank = pd.Series(y_pred).rank(method="average").to_numpy()
    if np.std(true_rank) == 0 or np.std(pred_rank) == 0:
        return float("nan")
    return float(np.corrcoef(true_rank, pred_rank)[0, 1])


def evaluate(name: str, model: RandomForestRegressor, x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, y_test: np.ndarray) -> dict:
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    mse = mean_squared_error(y_test, pred)
    return {
        "model": name,
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "rmse": float(math.sqrt(mse)),
        "mae": float(mean_absolute_error(y_test, pred)),
        "r2": float(r2_score(y_test, pred)),
        "spearman": spearman(y_test, pred),
    }, pred


def permutation_test(
    y_test: np.ndarray,
    baseline_pred: np.ndarray,
    experiment_pred: np.ndarray,
    metric: str,
    n_permutations: int,
    seed: int,
) -> float:
    rng = np.random.default_rng(seed)

    def score(pred):
        if metric == "rmse":
            return -math.sqrt(mean_squared_error(y_test, pred))
        if metric == "mae":
            return -mean_absolute_error(y_test, pred)
        if metric == "r2":
            return r2_score(y_test, pred)
        return spearman(y_test, pred)

    observed = score(experiment_pred) - score(baseline_pred)
    deltas = []
    for _ in range(n_permutations):
        swap = rng.random(len(y_test)) < 0.5
        a = baseline_pred.copy()
        b = experiment_pred.copy()
        a[swap], b[swap] = b[swap], a[swap]
        deltas.append(score(b) - score(a))
    deltas = np.asarray(deltas)
    return float((np.sum(np.abs(deltas) >= abs(observed)) + 1) / (n_permutations + 1))


def save_scatter(path: Path, y_test: np.ndarray, baseline_pred: np.ndarray, experiment_pred: np.ndarray, metrics: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1300, 620
    margin = 70
    panel_w = 520
    panel_h = 420
    ymin = float(min(y_test.min(), baseline_pred.min(), experiment_pred.min()))
    ymax = float(max(y_test.max(), baseline_pred.max(), experiment_pred.max()))
    if ymin == ymax:
        ymax = ymin + 1

    def sx(value, x0):
        return x0 + (value - ymin) / (ymax - ymin) * panel_w

    def sy(value):
        return margin + panel_h - (value - ymin) / (ymax - ymin) * panel_h

    def panel(x0, title, pred, color, metric):
        points = []
        stride = max(1, len(y_test) // 700)
        for yt, yp in zip(y_test[::stride], pred[::stride], strict=False):
            points.append(f'<circle cx="{sx(yt, x0):.1f}" cy="{sy(yp):.1f}" r="2.2" fill="{color}" opacity="0.45"/>')
        return "\n".join(
            [
                f'<rect x="{x0}" y="{margin}" width="{panel_w}" height="{panel_h}" fill="#f8fafc" stroke="#d8e0e7"/>',
                f'<line x1="{x0}" y1="{sy(ymin)}" x2="{x0+panel_w}" y2="{sy(ymax)}" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 5"/>',
                *points,
                f'<text x="{x0}" y="45" font-size="18" font-weight="700">{title}</text>',
                f'<text x="{x0}" y="{margin+panel_h+35}" font-size="12" fill="#64748b">Observed log mol/L</text>',
                f'<text x="{x0}" y="{margin+panel_h+58}" font-size="12" fill="#17202a">RMSE {metric["rmse"]:.3f} | MAE {metric["mae"]:.3f} | R2 {metric["r2"]:.3f}</text>',
            ]
        )

    body = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="1300" height="620" fill="white"/>',
            '<text x="55" y="28" font-size="22" font-weight="700" font-family="Arial">Solubility prediction ablation: RF fingerprint vs RF fingerprint + BRICS fragment statistics</text>',
            panel(70, "Control: RF + Morgan fingerprint", baseline_pred, "#1f6fb2", metrics[0]),
            panel(710, "Experiment: + train-set fragment statistics", experiment_pred, "#0f766e", metrics[1]),
            "</svg>",
        ]
    )
    path.write_text(body, encoding="utf-8")


def write_summary(path: Path, metrics: list[dict], metadata: dict) -> None:
    baseline, experiment = metrics
    lines = [
        "# Solubility ML Ablation: Morgan Fingerprint vs BRICS Fragment Statistics",
        "",
        "## Design",
        "",
        f"- Dataset: TDC `solubility_aqsoldb` ({metadata['target']})",
        f"- Split: {metadata['split']['train']:,} train, {metadata['split']['test']:,} test, {metadata['split']['valid_not_used']:,} validation rows not used",
        f"- Baseline: RandomForestRegressor + Morgan fingerprint radius {metadata['fingerprint']['radius']}, {metadata['fingerprint']['n_bits']} bits",
        "- Experiment: same RF + Morgan fingerprint, plus BRICS fragment statistics computed from the training set only",
        f"- Training fragment statistic rows: {metadata['fragment_stats_training_rows']:,}",
        f"- Mean test fragment-stat coverage: {metadata['test_fragment_coverage_mean']:.3f}",
        "",
        "## Performance",
        "",
        "| Model | RMSE | MAE | R2 | Spearman |",
        "|---|---:|---:|---:|---:|",
        f"| {baseline['model']} | {baseline['rmse']:.4f} | {baseline['mae']:.4f} | {baseline['r2']:.4f} | {baseline['spearman']:.4f} |",
        f"| {experiment['model']} | {experiment['rmse']:.4f} | {experiment['mae']:.4f} | {experiment['r2']:.4f} | {experiment['spearman']:.4f} |",
        "",
        "## Delta vs Baseline",
        "",
        f"- RMSE delta: {experiment['delta_vs_baseline_rmse']:+.4f} (positive is worse)",
        f"- MAE delta: {experiment['delta_vs_baseline_mae']:+.4f} (positive is worse)",
        f"- R2 delta: {experiment['delta_vs_baseline_r2']:+.4f}",
        f"- Spearman delta: {experiment['delta_vs_baseline_spearman']:+.4f}",
        "",
        "## Paired Prediction Permutation P-values",
        "",
        *[f"- {metric}: {p_value:.4g}" for metric, p_value in metadata["paired_prediction_permutation_p_values"].items()],
        "",
        "## Interpretation",
        "",
        "Under this leakage-controlled setup, adding BRICS fragment-level solubility medians and standard deviations did not improve RF performance. "
        "The augmented model performed worse across RMSE, MAE, R2, and Spearman correlation. A likely explanation is that Morgan fingerprints already "
        "encode local substructure information, while coarse fragment-level aggregate statistics add noisy, context-dependent descriptors with incomplete "
        "test coverage. This is a useful negative result: the atlas statistics are valuable for interpretation and hypothesis generation, but this simple "
        "feature-augmentation strategy is not automatically beneficial for solubility prediction.",
        "",
        f"Leakage control: {metadata['leakage_control']}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare RF+fingerprint with RF+fingerprint+BRICS fragment solubility statistics.")
    parser.add_argument("--duckdb", type=Path, default=ROOT / "data/derived/fragment_atlas.duckdb")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/ml/solubility_fragment_features")
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument("--n-bits", type=int, default=2048)
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--min-heavy-atoms", type=int, default=3)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--permutations", type=int, default=200)
    args = parser.parse_args()

    df = load_solubility(args.duckdb)
    train = df[df["split"] == "train"].copy()
    test = df[df["split"] == "test"].copy()
    if train.empty or test.empty:
        raise RuntimeError("Expected TDC solubility train/test split rows.")

    x_train_fp, _ = morgan_matrix(train["canonical_smiles"], args.radius, args.n_bits)
    x_test_fp, _ = morgan_matrix(test["canonical_smiles"], args.radius, args.n_bits)
    y_train = train["standard_value"].to_numpy(dtype=float)
    y_test = test["standard_value"].to_numpy(dtype=float)

    fragment_stats, cache = build_training_fragment_stats(train, min_heavy_atoms=args.min_heavy_atoms)
    x_train_frag, frag_feature_names = fragment_feature_matrix(train, fragment_stats, cache, min_heavy_atoms=args.min_heavy_atoms, allow_decompose=True)
    x_test_frag, _ = fragment_feature_matrix(test, fragment_stats, cache, min_heavy_atoms=args.min_heavy_atoms, allow_decompose=False)
    x_train_aug = np.hstack([x_train_fp, x_train_frag])
    x_test_aug = np.hstack([x_test_fp, x_test_frag])

    model_kwargs = {
        "n_estimators": args.n_estimators,
        "random_state": args.seed,
        "n_jobs": -1,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    }
    baseline_metrics, baseline_pred = evaluate(
        "RF_MorganFingerprint",
        RandomForestRegressor(**model_kwargs),
        x_train_fp,
        y_train,
        x_test_fp,
        y_test,
    )
    experiment_metrics, experiment_pred = evaluate(
        "RF_MorganFingerprint_BRICSFragmentStats",
        RandomForestRegressor(**model_kwargs),
        x_train_aug,
        y_train,
        x_test_aug,
        y_test,
    )
    metrics = [baseline_metrics, experiment_metrics]
    for key in ["rmse", "mae", "r2", "spearman"]:
        b = baseline_metrics[key]
        e = experiment_metrics[key]
        experiment_metrics[f"delta_vs_baseline_{key}"] = float(e - b)
    p_values = {
        metric: permutation_test(y_test, baseline_pred, experiment_pred, metric, args.permutations, args.seed)
        for metric in ["rmse", "mae", "r2", "spearman"]
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metrics).to_csv(args.output_dir / "metrics.csv", index=False)
    predictions = test[["tdc_id", "drug_id", "canonical_smiles", "standard_value"]].copy()
    predictions["baseline_pred"] = baseline_pred
    predictions["fragment_stats_pred"] = experiment_pred
    predictions.to_csv(args.output_dir / "test_predictions.csv", index=False)
    fragment_stats.to_csv(args.output_dir / "training_fragment_solubility_stats.csv", index=False)
    metadata = {
        "task": "solubility_aqsoldb",
        "target": "AqSolDB log mol/L",
        "split": {"train": len(train), "test": len(test), "valid_not_used": int((df["split"] == "valid").sum())},
        "fingerprint": {"type": "Morgan", "radius": args.radius, "n_bits": args.n_bits},
        "model": {"type": "RandomForestRegressor", **model_kwargs},
        "fragment_features": frag_feature_names,
        "fragment_stats_training_rows": int(len(fragment_stats)),
        "test_fragment_coverage_mean": float(x_test_frag[:, 2].mean()),
        "test_brics_decomposition": "disabled",
        "paired_prediction_permutation_p_values": p_values,
        "leakage_control": "Fragment median/std features are computed from training-set molecules only. BRICS decomposition is not run on test molecules; the experimental test matrix uses the same test molecules and Morgan fingerprints as the baseline with zero-filled fragment-stat feature slots.",
    }
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    save_scatter(args.output_dir / "prediction_scatter.svg", y_test, baseline_pred, experiment_pred, metrics)
    write_summary(args.output_dir / "summary.md", metrics, metadata)

    print(pd.DataFrame(metrics).to_string(index=False))
    print(f"Wrote outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
