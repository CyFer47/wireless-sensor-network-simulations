# How Data Was Created — Import and Export Commands

This document explains how the datasets in this DATA folder were created, exported from the simulation, derived from the database, and how to verify them.

## PostgreSQL Database Backup

```bash
# Create backup directory
mkdir -p /home/cyfer/FYP/archive/db_backups

# Backup entire wsn database
pg_dump -h 127.0.0.1 -U wsn_user -d wsn_sim > /home/cyfer/FYP/archive/db_backups/wsn_sim_final_demo_backup.sql
```

## Query Total Runs

```bash
psql -h 127.0.0.1 -U wsn_user -d wsn_sim -c "SELECT COUNT(*) FROM wsn.runs;"
```

Expected output: `1148` (or similar after Phase2A rerun)

## Export ML Dataset Source Location

```bash
ls -lh /home/cyfer/FYP/WSN_simulation/09_dataset_exports/
```

This folder contains the official exported ML dataset before it was copied into this DATA folder.

## Verify ML Dataset Row Counts

Run this Python script to verify row counts match expected values:

```python
import pandas as pd
import sys

base = "/home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA/01_official_ml_dataset"

expected = {
    "ml_run_outcomes.csv": 1148,
    "ml_healing_candidates.csv": 1148,
    "ml_best_healing_labels.csv": 636,
    "ml_recovery_time_regression.csv": 520,
    "dataset_split_manifest.csv": 1148,
}

all_match = True
for filename, expected_count in expected.items():
    filepath = f"{base}/{filename}"
    df = pd.read_csv(filepath)
    actual_count = len(df)
    match = "✓" if actual_count == expected_count else "✗"
    print(f"{match} {filename}: {actual_count} (expected {expected_count})")
    if actual_count != expected_count:
        all_match = False

sys.exit(0 if all_match else 1)
```

## Verify Dataset Split

```python
import pandas as pd

df = pd.read_csv("/home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA/04_split_manifest/dataset_split_manifest.csv")

print("=" * 60)
print("SPLIT DISTRIBUTION")
print("=" * 60)
print(df["split"].value_counts())
print()

print("=" * 60)
print("SPLIT BY SCALE")
print("=" * 60)
print(df.groupby(["split", "scale"]).size())
print()

print("=" * 60)
print("TRAIN SCALE RANGE")
print("=" * 60)
train_df = df[df["split"] == "train"]
print(f"S1 - S9: {len(train_df)} runs")
print()

print("=" * 60)
print("VALIDATION SCALE (S10)")
print("=" * 60)
val_df = df[df["split"] == "validation"]
print(f"S10: {len(val_df)} runs")
print()

print("=" * 60)
print("TEST SCALE (S11)")
print("=" * 60)
test_df = df[df["split"] == "test"]
print(f"S11: {len(test_df)} runs")
```

## Verify No Duplicate Run IDs

```python
import pandas as pd

df = pd.read_csv("/home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA/01_official_ml_dataset/ml_run_outcomes.csv")
duplicates = df.duplicated(subset=["run_id"]).sum()
if duplicates > 0:
    print(f"WARNING: {duplicates} duplicate run_ids found!")
else:
    print("✓ No duplicate run_ids")
```

## Verify No Secrets in Data

```bash
find /home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA \
  \( -name ".env" -o -name "*.sql" -o -name "*.db" -o -name "*.log" -o -name ".venv" \) -print

# Should output nothing if clean
```

## Check Data Folder Size

```bash
du -sh /home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA
```

## Verify Checksums

```bash
cd /home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA
sha256sum -c ./07_checksums/DATA_SHA256SUMS.txt
```

## Export Phases

This data was exported in these phases:

1. **Phase 04**: Official ML dataset from S1-S11 runs exported to `09_dataset_exports/`
2. **Phase 05**: ML models trained and tested on split dataset
3. **Phase 05 Stage B**: DB-derived labels created when simulation labels were insufficient
4. **Phase 05 Stage C**: Final metrics, safe/unsafe claims, feature importance
5. **Phase 2A**: Energy dataset (162 runs × scaling factors) exported after patch/rerun

## Data Lineage

```
Simulation Runs (S1-S11)
    ↓
PostgreSQL Import
    ↓
wsn schema (runs, run_summary, events, clusters, nodes tables)
    ↓
Export to 09_dataset_exports/ (ML dataset)
    ↓
ML dataset splits (train=S1-S9, val=S10, test=S11)
    ↓
Model training and validation (Stage C)
    ↓
This DATA folder (curated, demo-safe copies)
```

## DB-Derived Labels

When the simulation output for `best_healing_id` was insufficient:

1. Query the wsn.run_summary table for actual_best_healing_id
2. Derive labels from healing outcome metrics
3. Create ml_best_healing_labels_derived_from_db_v1.csv
4. Document methodology in ML_BEST_HEALING_LABEL_DB_SOURCE_REPORT.md

See `02_derived_labels/` for derived label files.

## Phase2A Dataset

Phase2A is a separate 162-run × 6 scales dataset designed for:
- Energy consumption analysis
- H0 vs active-healing comparison
- Scale-dependent behavior study
- Live PostgreSQL validation after S12/S13 patch

Files in `03_phase2A_energy_dataset/`:
- phase2A_run_summary.csv (one row per run)
- phase2A_energy_summary.csv (energy metrics by run)
- phase2A_healing_comparison.csv (healing vs no-healing)
- phase2A_scale_comparison.csv (energy across scales)
- phase2A_h0_vs_h1_h3_h4.csv (H0 baseline vs healing families)

See PHASE2A_PATCH_AND_RERUN_REPORT.md for details.
