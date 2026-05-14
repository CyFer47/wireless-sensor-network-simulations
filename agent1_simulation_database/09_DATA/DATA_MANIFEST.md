# DATA Manifest — Complete File Inventory

Complete inventory of all files in the DATA folder.

## Summary

- **Total files**: 34 (excluding manifest and checksums)
- **CSV files**: 19 (datasets and tables)
- **MD files**: 14 (documentation and guides)
- **TXT files**: 1 (checksums)
- **Total size**: 1.7 MB

## File Organization

### 01_official_ml_dataset/ — ML Dataset Core
| File | Purpose | Rows | Size |
|------|---------|------|------|
| ml_run_outcomes.csv | Feature matrix for all 1148 runs | 1148 | 322 KB |
| ml_healing_candidates.csv | Healing candidates per run | 1148 | 311 KB |
| ml_best_healing_labels.csv | Labels for classification task | 636 | 103 KB |
| ml_recovery_time_regression.csv | Labels for regression task | 520 | 116 KB |
| dataset_split_manifest.csv | Train/val/test split assignment | 1148 | 160 KB |
| ML_EXPORT_SUMMARY.md | Export metadata | — | 1.1 KB |
| DATASET_DICTIONARY.md | Column definitions | — | 5.7 KB |

### 02_derived_labels/ — DB-Derived Labels
| File | Purpose | Notes |
|------|---------|-------|
| ml_best_healing_labels_derived_from_db_v1.csv | Classification labels from DB | Primary source |
| ml_best_healing_labels_derived_from_db_v1_archived.csv | Archived backup | — |
| ml_healing_candidates_scored_from_db_v1.csv | Healing candidates scored | Primary source |
| ml_healing_candidates_scored_from_db_v1_archived.csv | Archived backup | — |
| ml_scenario_base_conditions_v1.csv | Base scenario conditions | Primary source |
| ml_scenario_base_conditions_v1_archived.csv | Archived backup | — |
| ML_BEST_HEALING_LABEL_DB_SOURCE_REPORT.md | Derivation methodology | **Read this** |

### 03_phase2A_energy_dataset/ — Energy Validation
| File | Purpose | Rows |
|------|---------|------|
| phase2A_run_summary.csv | Run metadata for Phase2A | 162 |
| phase2A_energy_summary.csv | Energy metrics per run | 162 |
| phase2A_healing_comparison.csv | Healing vs no-healing | 6 summary rows |
| phase2A_scale_comparison.csv | Energy across scales | 6 scales |
| phase2A_h0_vs_h1_h3_h4.csv | H0 baseline vs active healing | Summary |
| phase2A_dashboard_run_index.csv | Dashboard query index | 162 |
| PHASE2A_PATCH_AND_RERUN_REPORT.md | Patch and rerun summary | — |

### 04_split_manifest/ — Train/Val/Test Split
| File | Purpose |
|------|---------|
| dataset_split_manifest.csv | Scale-stratified split (Train: S1-S9, Val: S10, Test: S11) |
| SPLIT_EXPLANATION.md | Why and how the split was done |

Split Distribution:
- Train (S1-S9): 1012 runs
- Validation (S10): 68 runs
- Test (S11): 68 runs

### 05_data_dictionary/ — Data Reference
| File | Purpose |
|------|---------|
| DATASET_DICTIONARY.md | Column descriptions and value ranges |
| ML_EXPORT_SUMMARY.md | Export process metadata |

### 06_verification_reports/ — Audit and Results
| File | Purpose |
|------|---------|
| ML_DATASET_AUDIT_REPORT.md | Data consistency checks |
| ML_DATASET_SPLIT_DECISION.md | Split strategy rationale |
| ML_SEED_EXPANSION_DECISION.md | Why seeds were added |
| PHASE05_STAGEC_FINAL_ML_RESULT_SUMMARY.md | **Final ML results** |
| PHASE05_STAGEC_SAFE_AND_UNSAFE_CLAIMS.md | **Read for viva** |
| PHASE05_STAGEC_FINAL_METRICS_TABLE.csv | Model metrics (A, B, C) |

### 07_checksums/ — Data Integrity
| File | Purpose |
|------|---------|
| DATA_SHA256SUMS.txt | SHA256 checksums for all files |

Verify with:
```bash
cd /home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA
sha256sum -c ./07_checksums/DATA_SHA256SUMS.txt
```

### 08_import_export_commands/ — Guides
| File | Purpose |
|------|---------|
| HOW_DATA_WAS_CREATED.md | DB backup, export, and verify commands |

## Safe for Viva — YES

All files in this DATA folder are safe for demonstration and explanation during a viva.

## Safe for GitHub — YES (With Restrictions)

Files marked safe for GitHub:
- All CSV files (datasets)
- All MD files (documentation)
- Split manifest and dictionary
- Verification reports

Files NOT safe for GitHub (though none are in this folder):
- .env files
- .venv directories
- Database dumps
- Logs

## Data Verification

### Row Counts (Verified)
- ml_run_outcomes.csv: ✓ 1148 rows
- ml_healing_candidates.csv: ✓ 1148 rows
- ml_best_healing_labels.csv: ✓ 636 rows
- ml_recovery_time_regression.csv: ✓ 520 rows
- dataset_split_manifest.csv: ✓ 1148 rows

### Split Distribution (Verified)
- Train: 1012 runs (S1-S9)
- Validation: 68 runs (S10)
- Test: 68 runs (S11)
- Total: 1148 runs

### Uniqueness (Verified)
- No duplicate run_ids in ml_run_outcomes.csv
- All 1148 unique runs represented

### Safety (Verified)
- No .env, .venv, .sql, .db, or .log files
- No credentials exposed
- All files are curated demo-safe copies

## Key Files for Viva Preparation

1. **Start here**: [00_README_DATA.md](00_README_DATA.md)
2. **Understand safe/unsafe claims**: [06_verification_reports/PHASE05_STAGEC_SAFE_AND_UNSAFE_CLAIMS.md](06_verification_reports/PHASE05_STAGEC_SAFE_AND_UNSAFE_CLAIMS.md)
3. **Know the split**: [04_split_manifest/SPLIT_EXPLANATION.md](04_split_manifest/SPLIT_EXPLANATION.md)
4. **See final metrics**: [06_verification_reports/PHASE05_STAGEC_FINAL_METRICS_TABLE.csv](06_verification_reports/PHASE05_STAGEC_FINAL_METRICS_TABLE.csv)
5. **Understand data lineage**: [08_import_export_commands/HOW_DATA_WAS_CREATED.md](08_import_export_commands/HOW_DATA_WAS_CREATED.md)

## Data Lineage

```
Simulation Runs (S1-S11, 1148 total)
    ↓
PostgreSQL wsn schema
    ↓
Export: 09_dataset_exports/
    ↓
ML Dataset Splits (train/val/test)
    ↓
Models A, B, C Training (Phase 05)
    ↓
Final Metrics & Claims (Stage C)
    ↓
This DATA Folder (Demo-Safe Curated Copies)
```

## Questions?

See [00_README_DATA.md](00_README_DATA.md) for comprehensive documentation.
