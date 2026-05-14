# FINAL_SCALE5000 S9 Stage B — Representative Selection

Date: 2026-05-02

**Deterministic selection rule (applied):**

- For each scenario key `(scale, architecture, failure_family, healing_id, load, seed)`, select the latest complete `run_id` (ORDER BY `run_id` DESC, pick `rn=1`).

**Selected representative runs for MATLAB QA:**

| Healing Family | Description | Run ID | Scenario |
|---|---|---|---|
| F1/H1 | Latest for F1/H1 | **1032** | A, L1, seed01 |
| F2/H2 | Latest for F2/H2 | **1044** | A, L2, seed01 |
| F3/H3 | Latest for F3/H3 | **1052** | B, L1, seed01 |
| F4/H4 | Latest for F4/H4 | **1036** | A, L1, seed01 |

**Data sizes (confirmed):**

- F1/H1 (run 1032):
  - `cluster_timeseries`: 4160 rows (160 clusters × 26 time points)
  - `node_final_summary`: 4005 rows
  - `events`: 624209 rows
  - `global_timeseries`: 26 rows

- F2/H2 (run 1044):
  - `cluster_timeseries`: 4160 rows
  - `node_final_summary`: 4005 rows
  - `events`: 1284 rows
  - `global_timeseries`: 26 rows

- F3/H3 (run 1052):
  - `cluster_timeseries`: 4160 rows
  - `node_final_summary`: 4005 rows
  - `events`: 2367 rows
  - `global_timeseries`: 26 rows

- F4/H4 (run 1036):
  - `cluster_timeseries`: 4160 rows
  - `node_final_summary`: 4005 rows
  - `events`: 13318 rows
  - `global_timeseries`: 26 rows

**Observations:**

- All representative runs selected from Stage B data (no Stage A reuse in representatives)
- Event row counts vary by healing family: F1/H1 shows highest event density (624k), F2/H2 and F3/H3 lower (1.3k and 2.4k), F4/H4 moderate (13.3k)
- This variation reflects different healing algorithm behaviors and event logging densities per failure/healing pattern
- All runs use identical cluster and node counts, confirming consistent S9 scale (4000 nodes, 160 clusters, 251 time points)

