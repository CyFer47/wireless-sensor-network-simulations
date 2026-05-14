# DATA Folder — ML Dataset and Validation Evidence

## What This Folder Contains

This `DATA` folder contains all curated simulation-derived datasets used for:
- ML model training, validation, and testing
- Report analysis and viva demonstration
- Energy consumption analysis (Phase2A)
- Safe inference and limited generalization claims

**Do not**: run simulations, train models, or modify PostgreSQL using these files. These are read-only demo copies.

## Folder Organization

### 01_official_ml_dataset/
Official ML dataset exported directly from simulation runs (S1-S11).
- `ml_run_outcomes.csv`: 1148 runs × feature matrix
- `ml_healing_candidates.csv`: 1148 rows (one per run)
- `ml_best_healing_labels.csv`: 636 rows (labeled subset for classification)
- `ml_recovery_time_regression.csv`: 520 rows (labeled for regression)
- `dataset_split_manifest.csv`: Train/validation/test assignment per run
- `ML_EXPORT_SUMMARY.md`: Export metadata
- `DATASET_DICTIONARY.md`: Column descriptions

**Key fact**: Original best_healing_id in simulation was mostly NaN. Labels were derived from database query results (see 02_derived_labels/).

### 02_derived_labels/
DB-derived healing labels created when simulation output was insufficient.
- `ml_best_healing_labels_derived_from_db_v1.csv`: Labels from DB query
- `ml_healing_candidates_scored_from_db_v1.csv`: Healing candidates from DB
- `ml_scenario_base_conditions_v1.csv`: Base scenario conditions
- `ML_BEST_HEALING_LABEL_DB_SOURCE_REPORT.md`: Methodology and reconciliation

**Important**: The classifier (Model C) is pairwise active-healing vs H0, not a full best-healing selector. Do not claim it selects from all healing families.

### 03_phase2A_energy_dataset/
Phase2A (162 runs × scaling) dataset for energy and live DB validation.
- `phase2A_run_summary.csv`: Run metadata
- `phase2A_energy_summary.csv`: Energy consumption per run
- `phase2A_healing_comparison.csv`: Healing vs no-healing comparison
- `phase2A_scale_comparison.csv`: Energy across scales
- `phase2A_h0_vs_h1_h3_h4.csv`: H0 baseline vs active-healing families
- `phase2A_dashboard_run_index.csv`: Run index for dashboard queries
- `PHASE2A_PATCH_AND_RERUN_REPORT.md`: Patch, smoke test, and rerun summary

**Known limitation**: Phase2A lacks comprehensive H0 coverage across all failure families. For H0-vs-healing comparison, prefer S8-S11 Stage C results.

### 04_split_manifest/
Split assignment for train/validation/test.
- `dataset_split_manifest.csv`: Scale → split assignment
- `SPLIT_EXPLANATION.md`: Why train=S1-S9, validation=S10, test=S11

### 05_data_dictionary/
Data structure and export metadata.
- `DATASET_DICTIONARY.md`: Column definitions and value ranges
- `ML_EXPORT_SUMMARY.md`: Export process and checksums

### 06_verification_reports/
Audit, verification, and safe/unsafe claims.
- `ML_DATASET_AUDIT_REPORT.md`: Data consistency and uniqueness checks
- `ML_DATASET_SPLIT_DECISION.md`: Why train/validation/test split was chosen
- `ML_SEED_EXPANSION_DECISION.md`: Why seeds were added to dataset
- `PHASE05_STAGEC_FINAL_ML_RESULT_SUMMARY.md`: Stage C final results
- `PHASE05_STAGEC_SAFE_AND_UNSAFE_CLAIMS.md`: **Read this for viva**
- `PHASE05_STAGEC_FINAL_METRICS_TABLE.csv`: Final model metrics

### 07_checksums/
SHA256 checksums for all copied files.
- `DATA_SHA256SUMS.txt`: Checksums for verification and integrity

### 08_import_export_commands/
Commands used to create and export this dataset.
- `HOW_DATA_WAS_CREATED.md`: DB backup, query, export, and verify commands

## How to Use Data in ML Demo

### Verify Row Counts

```bash
python3 - <<'PY'
import pandas as pd
base = "DATA/01_official_ml_dataset"
for f in ["ml_run_outcomes.csv", "ml_healing_candidates.csv", "ml_best_healing_labels.csv", "ml_recovery_time_regression.csv", "dataset_split_manifest.csv"]:
    df = pd.read_csv(f"{base}/{f}")
    print(f"{f}: {len(df)} rows")
PY
```

Expected output:
```
ml_run_outcomes.csv: 1148 rows
ml_healing_candidates.csv: 1148 rows
ml_best_healing_labels.csv: 636 rows
ml_recovery_time_regression.csv: 520 rows
dataset_split_manifest.csv: 1148 rows
```

### Verify Split

```bash
python3 - <<'PY'
import pandas as pd
df = pd.read_csv("DATA/04_split_manifest/dataset_split_manifest.csv")
print("Split distribution:")
print(df["split"].value_counts())
print("\nSplit by scale:")
print(df.groupby(["split", "scale"]).size())
PY
```

### Load for ML Workflow

```python
import pandas as pd

# Load features
X = pd.read_csv("DATA/01_official_ml_dataset/ml_run_outcomes.csv")

# Load split assignment
split_manifest = pd.read_csv("DATA/01_official_ml_dataset/dataset_split_manifest.csv")

# Load labels (for regression or classification)
regression_labels = pd.read_csv("DATA/01_official_ml_dataset/ml_recovery_time_regression.csv")
classification_labels = pd.read_csv("DATA/01_official_ml_dataset/ml_best_healing_labels.csv")

# Filter by split
train_idx = split_manifest[split_manifest["split"] == "train"].index
test_idx = split_manifest[split_manifest["split"] == "test"].index
```

## ML Models — Safe and Unsafe Claims

### Model A: Recovery-Time Regression
**Purpose**: Predict time to recovery (seconds) during active healing.

**Safe claims**:
- Model learns recovery delay under different healing strategies
- Regression performance on test set (S11) is documented

**Unsafe claims**:
- Do not claim Model A provides real-time prediction
- Do not generalize to scales beyond S11

### Model B: Delivery Ratio and Consumed Energy Regression
**Purpose**: Predict aggregate delivery ratio and recovered cluster count.

**Safe claims**:
- Model B predicts delivery ratio (agg_delivery_ratio) accurately
- Model B predicts recovered_clusters accurately
- Feature importance shows scenario parameters drive these metrics

**Unsafe claims**:
- ⚠️ **Energy prediction is not usable** — consumed_j regression is weak and not recommended
- Do not use Model B for energy claims without Stage C validation

### Model C: Active-Healing vs H0 Classifier
**Purpose**: Pairwise classifier for active-healing vs baseline (H0).

**Safe claims**:
- Model C distinguishes active-healing runs from H0 baseline
- Classification accuracy on test set (S11) is documented
- Feature importance identifies healing-relevant parameters

**Unsafe claims**:
- ⚠️ **Not a best-healing selector** — Model C is pairwise, not 5-way
- Do not claim Model C selects optimal healing from {H0, H1, H2, H3, H4}
- Do not generalize classifier to new scales without retraining

## Known Limitations

1. **Scale dependency**: Models trained on S1-S11. New scales require retraining.
2. **No random split**: Dataset is scale-stratified, not randomly shuffled. Do not claim random CV results.
3. **Energy claim caveat**: Do not use Model B energy predictions for production claims.
4. **Healing selector caveat**: Model C is pairwise, not a best-healing optimizer.
5. **DB derivation**: Labels were derived from DB when simulation output was insufficient. Query logic is documented.

## Key Files for Viva

1. **Start here**: [PHASE05_STAGEC_SAFE_AND_UNSAFE_CLAIMS.md](06_verification_reports/PHASE05_STAGEC_SAFE_AND_UNSAFE_CLAIMS.md)
2. **Understand splits**: [SPLIT_EXPLANATION.md](04_split_manifest/SPLIT_EXPLANATION.md)
3. **Verify data**: [ML_DATASET_AUDIT_REPORT.md](06_verification_reports/ML_DATASET_AUDIT_REPORT.md)
4. **Model metrics**: [PHASE05_STAGEC_FINAL_METRICS_TABLE.csv](06_verification_reports/PHASE05_STAGEC_FINAL_METRICS_TABLE.csv)
5. **Phase2A evidence**: [PHASE2A_PATCH_AND_RERUN_REPORT.md](03_phase2A_energy_dataset/PHASE2A_PATCH_AND_RERUN_REPORT.md)

## Questions?

Refer to:
- `DATA_MANIFEST.md` for complete file inventory
- `05_data_dictionary/DATASET_DICTIONARY.md` for column definitions
- `06_verification_reports/` for audit and decision records
