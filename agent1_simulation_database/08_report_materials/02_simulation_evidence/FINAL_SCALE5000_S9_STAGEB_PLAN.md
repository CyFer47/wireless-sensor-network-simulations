# S9 Stage B (Scale 5000, 4000 Nodes) – Execution Plan

## Stage B Objective

Validate all main healing families (H1, H2, H3, H4) at S9 scale with comprehensive load and seed coverage.

## Matrix Definition

**Stage B Target**: 4 failure/healing families × 2 architectures × 2 loads × 2 seeds = **32 unique rows**

```text
Healing Families to test:
  F1/H1 (common healing pair)
  F2/H2 (additional healing variant)
  F3/H3 (additional healing variant)
  F4/H4 (post-healing stress pair)

Each family × 2 architectures (A/B) × 2 loads (L1/L2) × 2 seeds (seed01/seed02) = 8 rows per family
Total: 4 families × 8 rows = 32 rows
```

## S9 Scale Configuration

```text
Node count:       4000 (CH=160, BS=5)
Area:             1020 × 1020 m
Simulation time:  250 s
Topology:         Deterministic (maps: seed01, seed02)
```

## Stage A Overlap Reuse

8 rows from S9 Stage A are reused in Stage B (skip re-execution):

```text
Existing complete rows to reuse:
  F1_H1_A_S9_L1_seed01 (run_id 1032)
  F1_H1_A_S9_L2_seed01 (run_id 1033)
  F1_H1_B_S9_L1_seed01 (run_id 1034)
  F1_H1_B_S9_L2_seed01 (run_id 1035)
  F4_H4_A_S9_L1_seed01 (run_id 1036)
  F4_H4_A_S9_L2_seed01 (run_id 1037)
  F4_H4_B_S9_L1_seed01 (run_id 1038)
  F4_H4_B_S9_L2_seed01 (run_id 1039)

New rows to execute: 32 - 8 = 24 rows
```

## New Rows Required

```text
F1_H1 with seed02 (4 new rows):
  F1_H1_A_S9_L1_seed02
  F1_H1_A_S9_L2_seed02
  F1_H1_B_S9_L1_seed02
  F1_H1_B_S9_L2_seed02

F2_H2 with seed01/seed02 (8 new rows):
  F2_H2_A_S9_L1_seed01, F2_H2_A_S9_L2_seed01, F2_H2_B_S9_L1_seed01, F2_H2_B_S9_L2_seed01
  F2_H2_A_S9_L1_seed02, F2_H2_A_S9_L2_seed02, F2_H2_B_S9_L1_seed02, F2_H2_B_S9_L2_seed02

F3_H3 with seed01/seed02 (8 new rows):
  F3_H3_A_S9_L1_seed01, F3_H3_A_S9_L2_seed01, F3_H3_B_S9_L1_seed01, F3_H3_B_S9_L2_seed01
  F3_H3_A_S9_L1_seed02, F3_H3_A_S9_L2_seed02, F3_H3_B_S9_L1_seed02, F3_H3_B_S9_L2_seed02

F4_H4 with seed02 (4 new rows):
  F4_H4_A_S9_L1_seed02
  F4_H4_A_S9_L2_seed02
  F4_H4_B_S9_L1_seed02
  F4_H4_B_S9_L2_seed02
```

## Execution Strategy

**Pre-check**: Query DB for existing complete rows (Stage A overlap)
**Batch runner**: `tools/run_s9_stageb_batch.py`
**State tracking**: `outputs/s9_stageb_state.json`
**Quarantine log**: `outputs/s9_stageb_quarantine.json`
**Batch log**: `outputs/s9_stageb_batch.log`

### Batch Runner Behavior

1. Pre-scan DB to identify existing complete rows (reused Stage A)
2. Skip execution for 8 existing rows
3. Execute 24 new rows in sequence:
   - Generate/validate runspec
   - Validate map node count
   - Run ns-3 simulation
   - Export results
   - Import to PostgreSQL
   - Verify DB integrity
4. Track state and update status file
5. Quarantine failed runs (if any)

### Expected Execution Time

- ~5 minutes for 24 new runs (based on Stage A performance)
- No re-simulation of 8 reused Stage A rows

## Acceptance Criteria

```text
✓ Stage B target rows = 32
✓ Stage B complete rows = 32
✓ Failed runs = 0
✓ Partial runs = 0
✓ Existing Stage A overlap reused (8 rows, 0 new executions)
✓ New runs executed (24 rows)
✓ Architecture balance: 16 A, 16 B
✓ Load balance: 16 L1, 16 L2
✓ Seed balance: 16 seed01, 16 seed02
✓ Healing families balanced:
    F1_H1: 8 rows (4 arch A, 4 arch B, 4 L1, 4 L2, 4 seed01, 4 seed02)
    F2_H2: 8 rows (4 arch A, 4 arch B, 4 L1, 4 L2, 4 seed01, 4 seed02)
    F3_H3: 8 rows (4 arch A, 4 arch B, 4 L1, 4 L2, 4 seed01, 4 seed02)
    F4_H4: 8 rows (4 arch A, 4 arch B, 4 L1, 4 L2, 4 seed01, 4 seed02)
✓ Map lineage: map_S9_seed01, map_S9_seed02 present for all Stage B rows
✓ S1–S8 and S9 Stage A remain unaffected
```

## Map Validation

```text
map_S9_seed01:
  ✓ Exists: YES
  ✓ Node count: 4000
  ✓ Used by Stage A (seed01 runs) and Stage B (seed01 runs)

map_S9_seed02:
  ✓ Exists: YES
  ✓ Node count: 4000
  ✓ Used by Stage B seed02 runs
```

## Runspec Pre-generation

All 24 Stage B runspecs pre-generated in `runspecs/generated/s9_stageb/`:

```text
F1_H1_A_S9_L1_seed02.json
F1_H1_A_S9_L2_seed02.json
F1_H1_B_S9_L1_seed02.json
F1_H1_B_S9_L2_seed02.json
F2_H2_A_S9_L1_seed01.json
F2_H2_A_S9_L1_seed02.json
... (8 total for F2_H2)
F3_H3_A_S9_L1_seed01.json
F3_H3_A_S9_L1_seed02.json
... (8 total for F3_H3)
F4_H4_A_S9_L1_seed02.json
F4_H4_A_S9_L2_seed02.json
F4_H4_B_S9_L1_seed02.json
F4_H4_B_S9_L2_seed02.json
```

Batch runner will regenerate specs in canonical format during execution.

## Safety Checks

- ✓ Dry-run mode available: `--dry-run` flag
- ✓ DB pre-scan prevents duplicate executions
- ✓ Failure quarantine prevents batch abort on single failure
- ✓ State file tracks progress for resumability
- ✓ LIKE pattern matching in DB queries accounts for importer timestamps

## Next Steps Post-Execution

1. Verify all 32 Stage B rows in DB with correct properties
2. Run comprehensive query proof
3. Create GO/NO-GO decision document
4. Commit and push to GitHub
5. Validate API/dashboard visibility
6. Plan S9 Stage C (if required)
