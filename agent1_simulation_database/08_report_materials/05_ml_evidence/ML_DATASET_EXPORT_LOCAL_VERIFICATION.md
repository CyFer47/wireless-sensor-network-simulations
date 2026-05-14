# ML Dataset Export Local Verification

- Export folder: /home/cyfer/FYP/WSN_simulation/09_dataset_exports
- Backup file: /home/cyfer/FYP/archive/db_backups/wsn_sim_before_ml_dataset_export.sql
- Package file: /home/cyfer/FYP/archive/ml_dataset_exports/wsn_ml_dataset_phase04_export.tar.gz

## File checks

- ml_run_outcomes.csv: present
- ml_healing_candidates.csv: present
- ml_best_healing_labels.csv: present
- ml_recovery_time_regression.csv: present
- dataset_split_manifest.csv: present
- DATASET_DICTIONARY.md: present
- ML_EXPORT_SUMMARY.md: present

## CSV row counts

- ml_run_outcomes.csv: 1148
- ml_healing_candidates.csv: 1148
- ml_best_healing_labels.csv: 636
- ml_recovery_time_regression.csv: 520
- dataset_split_manifest.csv: 1148

## Split validation

- train rows: 1012
- validation rows: 68
- test rows: 68
- train scales: ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
- validation scales: ["S10"]
- test scales: ["S11"]
- duplicate run_id in ml_run_outcomes.csv: 0

## Recovery dataset checks

- active-healing only: yes
- H0 controls have blank recovery fields: yes

## Secrets scan

- secret hits found: 0

## Package checksum

- checksum: pending until archive is generated

- PostgreSQL rows modified: no
- simulations run: no
- ML models trained: no

## Verdict

- Export folder exists: yes
- All expected files found: yes
- Local verification: pass
