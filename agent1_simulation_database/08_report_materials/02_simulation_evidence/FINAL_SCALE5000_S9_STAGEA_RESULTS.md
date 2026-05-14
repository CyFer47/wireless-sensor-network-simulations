# S9 Stage A (Scale 5000, 4000 Nodes) – Final Results

## Execution Summary

**Status**: ✅ **COMPLETE**

All 12 required S9 Stage A simulation runs have been successfully executed, imported, and verified in the PostgreSQL database.

### Batch Execution Details

- **Batch Command**: `python3 tools/run_s9_stagea_batch.py`
- **Execution Window**: ~9 minutes per full run cycle
- **Total Rows**: 12 (all marked `run_status='complete'`)
- **Newest run_id**: 1039 (F4_H4_B_S9_L2_seed01)
- **Import Status**: All rows successfully imported to `wsn.runs` and related tables
- **Seed**: seed01 (single seed variant for S9 Stage A)

### Run Matrix

| Index | Spec ID | Architecture | Load | Failure Family/Healing | run_id | Status |
|-------|---------|--------------|------|------------------------|--------|--------|
| 1 | F0_H0_A_S9_L1_seed01 | A | L1 | F0/H0 | 1027 | ✓ |
| 2 | F0_H0_A_S9_L2_seed01 | A | L2 | F0/H0 | 1029 | ✓ |
| 3 | F0_H0_B_S9_L1_seed01 | B | L1 | F0/H0 | 1030 | ✓ |
| 4 | F0_H0_B_S9_L2_seed01 | B | L2 | F0/H0 | 1031 | ✓ |
| 5 | F1_H1_A_S9_L1_seed01 | A | L1 | F1/H1 | 1032 | ✓ |
| 6 | F1_H1_A_S9_L2_seed01 | A | L2 | F1/H1 | 1033 | ✓ |
| 7 | F1_H1_B_S9_L1_seed01 | B | L1 | F1/H1 | 1034 | ✓ |
| 8 | F1_H1_B_S9_L2_seed01 | B | L2 | F1/H1 | 1035 | ✓ |
| 9 | F4_H4_A_S9_L1_seed01 | A | L1 | F4/H4 | 1036 | ✓ |
| 10 | F4_H4_A_S9_L2_seed01 | A | L2 | F4/H4 | 1037 | ✓ |
| 11 | F4_H4_B_S9_L1_seed01 | B | L1 | F4/H4 | 1038 | ✓ |
| 12 | F4_H4_B_S9_L2_seed01 | B | L2 | F4/H4 | 1039 | ✓ |

### Key Properties

- **Total Nodes per Simulation**: 4005 (4000 sensor nodes + 1 base station)
- **Architecture Breakdown**: 6 runs × Architecture A, 6 runs × Architecture B
- **Failure Family Breakdown**: 4 runs × F0/H0, 4 runs × F1/H1, 4 runs × F4/H4
- **Load Balance**: 6 runs × L1 (light), 6 runs × L2 (heavy)
- **Map Lineage**: All 12 runs use `map_S9_seed01` (single topology variant)

### Database Integration

**Import Timeline**:
- Export from ns-3 simulator → timestamped export directories (e.g., `run_F0_H0_A_S9_L2_seed01_01_20260501_200138`)
- Parsed by `tools/import_run_to_postgres.py` → Database rows created with `experiment_version` field (includes spec_id + timestamp)
- Stored in: `wsn.runs`, `wsn.nodes_static`, `wsn.node_final_summary`, `wsn.global_timeseries`, `wsn.cluster_timeseries`, `wsn.events`, `wsn.run_summary`

### Database Verification

**Final Verification Queries** (executed post-cleanup):

```
Complete S9 rows: 12 (expected: 12) ✓
Architecture A: 6 (expected: 6) ✓
Architecture B: 6 (expected: 6) ✓
Failure family / healing:
  F0/H0: 4 (expected: 4) ✓
  F1/H1: 4 (expected: 4) ✓
  F4/H4: 4 (expected: 4) ✓
Seed variants: 1 (expected: 1 - seed01 only) ✓
Unique map_id: 1 (expected: 1 - map_S9_seed01) ✓
Newest S9 run_id: 1039 ✓
```

### Critical Issues Resolved

**Issue 1: Node Count Mismatch** (Early in S9 Stage A)
- **Root Cause**: Map manifest schema mismatch (`nodes` field vs. `counts.node_count`)
- **Fix Applied**: Updated `tools/run_s9_stagea_batch.py` to validate `counts.node_count` with fallback to legacy `nodes` field
- **Result**: F0_H0_A_S9_L1_seed01 retried successfully as run_id 1027

**Issue 2: Export Directory Naming** (During batch resume)
- **Problem**: Batch runner expected `outputs/F0_H0_A_S9_L2_seed01` but ns-3 creates `outputs/run_F0_H0_A_S9_L2_seed01_01_[TIMESTAMP]`
- **Fix Applied**: Updated batch runner to use glob pattern matching:
  ```python
  matching_dirs = sorted(glob.glob(str(output_root / f"run_{spec_id}_*")), reverse=True)
  export_dir = Path(matching_dirs[0])
  ```

**Issue 3: Database Query Pattern Matching** (During batch resume)
- **Problem**: Importer adds timestamp to `experiment_version`, so exact match queries returned no rows
- **Fix Applied**: Changed DB queries to use LIKE pattern:
  ```sql
  WHERE experiment_version LIKE '{spec_id}_%'
  ```

**Issue 4: Duplicate Run Detected & Cleaned** (Post-batch)
- **Problem**: F0_H0_A_S9_L2_seed01 had two run_ids (1028 and 1029) due to iterative batch refinement
- **Fix Applied**: Deleted all records for run_id 1028 from 7 tables (runs, nodes_static, node_final_summary, global_timeseries, cluster_timeseries, events, run_summary)
- **Result**: Final state contains exactly 12 unique S9 rows

### Historical Context

- **Initial Failure**: F0_H0_A_S9_L1_seed01 failed with map node-count validation error
- **Focused Retry**: Manual retry after manifest fix succeeded, inserted as run_id 1027 with signature `b1a269ea312df101dae663163fb8c0968a4bef6686220abd6fbca88960b9de94`
- **Batch Resume**: After batch runner fixes, all remaining 11 runs executed successfully in ~9 minutes
- **Database Cleanup**: One duplicate detected and cleaned to restore clean 12-row state

