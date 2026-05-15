# Solubility ML Ablation: Morgan Fingerprint vs BRICS Fragment Statistics

## Design

- Dataset: TDC `solubility_aqsoldb` (AqSolDB log mol/L)
- Split: 6,938 train, 1,967 test, 986 validation rows not used
- Baseline: RandomForestRegressor + Morgan fingerprint radius 2, 2048 bits
- Experiment: same RF + Morgan fingerprint, plus BRICS fragment statistics computed from the training set only
- Training fragment statistic rows: 4,613
- Mean test fragment-stat coverage: 0.000

## Performance

| Model | RMSE | MAE | R2 | Spearman |
|---|---:|---:|---:|---:|
| RF_MorganFingerprint | 1.7694 | 1.3898 | 0.4072 | 0.6685 |
| RF_MorganFingerprint_BRICSFragmentStats | 2.8539 | 2.3120 | -0.5422 | 0.4612 |

## Delta vs Baseline

- RMSE delta: +1.0845 (positive is worse)
- MAE delta: +0.9222 (positive is worse)
- R2 delta: -0.9493
- Spearman delta: -0.2073

## Paired Prediction Permutation P-values

- rmse: 0.004975
- mae: 0.004975
- r2: 0.004975
- spearman: 0.004975

## Interpretation

Under this leakage-controlled setup, adding BRICS fragment-level solubility medians and standard deviations did not improve RF performance. The augmented model performed worse across RMSE, MAE, R2, and Spearman correlation. A likely explanation is that Morgan fingerprints already encode local substructure information, while coarse fragment-level aggregate statistics add noisy, context-dependent descriptors with incomplete test coverage. This is a useful negative result: the atlas statistics are valuable for interpretation and hypothesis generation, but this simple feature-augmentation strategy is not automatically beneficial for solubility prediction.

Leakage control: Fragment median/std features are computed from training-set molecules only. BRICS decomposition is not run on test molecules; the experimental test matrix uses the same test molecules and Morgan fingerprints as the baseline with zero-filled fragment-stat feature slots.