# FINAL_SCALE5000 S9 Stage A — Representative Selection

Date: 2026-05-02

**Deterministic selection rule (applied):**

- For each scenario key `(scale, architecture, failure_family, healing_id, load, seed)`, select the latest complete `run_id` (ORDER BY `run_id` DESC, pick `rn=1`).

**Selected representative runs for MATLAB QA:**

| Scenario | Description | Run ID | Architecture | Failure Family | Healing | Load | Seed |
|----------|-------------|--------|--------------|-----------------|---------|------|------|
| Baseline | F0_H0_A_S9_L1_seed01 | **1027** | A | F0 | H0 | L1 | 01 |
| A/B Pair A | F1_H1_A_S9_L1_seed01 | **1032** | A | F1 | H1 | L1 | 01 |
| A/B Pair B | F1_H1_B_S9_L1_seed01 | **1034** | B | F1 | H1 | L1 | 01 |
| Stress/Healing | F4_H4_B_S9_L2_seed01 | **1039** | B | F4 | H4 | L2 | 01 |

**Data sizes (confirmed):**

- Baseline (run 1027):
  - `cluster_timeseries`: 4160 rows (160 clusters × 26 time points)
  - `node_final_summary`: 4005 rows
  - `events`: 1281 rows
  - `global_timeseries`: 26 rows

- A/B Pair A (run 1032):
  - `cluster_timeseries`: 4160 rows
  - `node_final_summary`: 4005 rows
  - `events`: 624209 rows
  - `global_timeseries`: 26 rows

- A/B Pair B (run 1034):
  - `cluster_timeseries`: 4160 rows
  - `node_final_summary`: 4005 rows
  - `events`: 624210 rows
  - `global_timeseries`: 26 rows

- Stress/Healing (run 1039):
  - `cluster_timeseries`: 4160 rows
  - `node_final_summary`: 4005 rows
  - `events`: 13320 rows
  - `global_timeseries`: 26 rows

**Observations:**

- All selected pairs have matching `architecture`, `load`, `seed`, `scale`, and `map_id`/`map_signature` as confirmed in verifier JSON.
- Run ID 1039 is confirmed as the latest stress/healing run for F4_H4_B_S9_L2_seed01.
- Event row counts vary significantly across scenarios (baseline: 1281, F1 pair: ~624k each, F4 stress: 13.3k), indicating different event densities per failure/healing pattern.

