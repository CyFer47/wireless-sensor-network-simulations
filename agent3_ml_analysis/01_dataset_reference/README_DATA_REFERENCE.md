# Dataset Reference for Agent 3 ML Workspace V2

## Curated DATA Source
The curated DATA folder used by Agent 3 for training and analysis is NOT duplicated in this upload.

It is available under Agent 1 in this repository at:

```
agent1_simulation_database/09_DATA/
```

Agent 3 consumes the curated outputs prepared by Agent 2 and stored under Agent 1. To reproduce training, copy the curated `DATA` folder into `agent3_ml_analysis/01_dataset_reference/` or update the training scripts to point to `agent1_simulation_database/09_DATA/`.

## Why DATA is excluded
- Raw simulation outputs are large and may contain proprietary or intermediate artifacts.
- The project maintains a single authoritative DATA store under Agent 1 to prevent duplication and versioning drift.

## Expected Structure
The curated `DATA` folder contains the official ML exports and derived labels used for training, including:
- `ml_run_outcomes.csv`
- `ml_healing_candidates_scored_from_db_v1.csv`
- `ml_best_healing_labels_derived_from_db_v1.csv`
- `ml_recovery_time_regression.csv`
- `dataset_split_manifest.csv`

Place the curated data at `agent1_simulation_database/09_DATA/` (preferred) or copy to `agent3_ml_analysis/01_dataset_reference/` before running training scripts.

---
