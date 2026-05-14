# Final Scale5000 S11 Stage A Results

**Date**: 2026-05-04  
**Status**: COMPLETE ✅  
**Duration**: ~6 minutes 35 seconds  
**Execution**: 08:20:40 → 08:27:15 UTC

---

## Stage A Overview

Stage A validates end-to-end readiness at 5000 nodes through a minimal but representative smoke test:

- **Baseline Control**: F0/H0 (no failure injection)
- **Active Healing Pair 1**: F1/H1 (intermediate failure, standard healing)
- **Active Healing Pair 2**: F4/H4 (severe failure, aggressive healing)

---

## Target Matrix

| # | Failure | Healing | Architecture | Load | Seed | Variant | Run ID | Status |
|---|---------|---------|--------------|------|------|---------|--------|--------|
| 1 | F0 | H0 | A | L1 | 01 | V1 | 1196 | ✅ |
| 2 | F0 | H0 | A | L2 | 01 | V1 | 1197 | ✅ |
| 3 | F0 | H0 | B | L1 | 01 | V1 | 1198 | ✅ |
| 4 | F0 | H0 | B | L2 | 01 | V1 | 1199 | ✅ |
| 5 | F1 | H1 | A | L1 | 01 | V3 | 1200 | ✅ |
| 6 | F1 | H1 | A | L2 | 01 | V3 | 1201 | ✅ |
| 7 | F1 | H1 | B | L1 | 01 | V3 | 1202 | ✅ |
| 8 | F1 | H1 | B | L2 | 01 | V3 | 1203 | ✅ |
| 9 | F4 | H4 | A | L1 | 01 | V3 | 1204 | ✅ |
| 10 | F4 | H4 | A | L2 | 01 | V3 | 1205 | ✅ |
| 11 | F4 | H4 | B | L1 | 01 | V3 | 1206 | ✅ |
| 12 | F4 | H4 | B | L2 | 01 | V3 | 1207 | ✅ |

---

## Completion Acceptance Criteria

| Criterion | Requirement | Result | Status |
|-----------|-------------|--------|--------|
| **Target Rows** | 12 | 12 | ✅ Met |
| **Complete Rows** | 12 | 12 | ✅ Met |
| **Failed Rows** | 0 | 0 | ✅ Met |
| **Partial Rows** | 0 | 0 | ✅ Met |
| **Quarantined Rows** | 0 | 0 | ✅ Met |
| **A/B Balance** | 6/6 | 6/6 | ✅ Met |
| **L1/L2 Balance** | 6/6 | 6/6 | ✅ Met |
| **Seed Pattern** | seed01 only | seed01 only | ✅ Met |
| **Families** | F0/H0, F1/H1, F4/H4 | F0/H0, F1/H1, F4/H4 | ✅ Met |
| **Map Lineage** | All linked | All linked | ✅ Met |
| **DB Queryability** | Pass | Pass | ✅ Met |

---

## Database Query Proof

**Query**: Verify all 12 Stage A rows are complete and queryable

```sql
SELECT COUNT(*) as stage_a_complete_rows
FROM wsn.runs
WHERE scale='S11'
  AND run_status='complete'
  AND failure_family='F0' AND healing_id='H0'
  AND seed=1;
```

**Result**: `4` rows (F0_H0 seed01)

```sql
SELECT COUNT(*) as f1_h1_stage_a_rows
FROM wsn.runs
WHERE scale='S11'
  AND run_status='complete'
  AND failure_family='F1' AND healing_id='H1'
  AND seed=1;
```

**Result**: `4` rows (F1_H1 seed01)

```sql
SELECT COUNT(*) as f4_h4_stage_a_rows
FROM wsn.runs
WHERE scale='S11'
  AND run_status='complete'
  AND failure_family='F4' AND healing_id='H4'
  AND seed=1;
```

**Result**: `4` rows (F4_H4 seed01)

**Total Stage A Proof**: 4 + 4 + 4 = **12 rows** ✅

---

## Design Rationale

### Scale Selection (5000 nodes)
- **S11 ultimate project target** – demonstrates 5000-node deployment feasibility
- **300s simulation time** – allows sufficient horizon for failure injection and healing observation
- **1150×1150 m deployment area** – maintains network density in safe range (~0.0038 nodes/m²)

### Failure/Healing Families (F0/H0, F1/H1, F4/H4)
- **F0/H0/V1 (Baseline)**: No failure injection; validates simulation baseline and export/import pipeline
- **F1/H1/V3**: Intermediate failure (72s inject), standard healing; representative of typical scenario
- **F4/H4/V3**: Severe failure (high intensity), aggressive healing (m7_profile for B architecture); stress test for healing mechanisms

### Architecture Variants (A, B)
- **Architecture A**: Passive receivers only (no healing mechanism)
- **Architecture B**: With recovery mechanism (m7_profile for F1/H1 and F4/H4)
- Validates end-to-end readiness across both stack modes

### Load Variants (L1, L2)
- **L1**: Baseline traffic load (3 pkt/s per node)
- **L2**: Double traffic (6 pkt/s per node)
- Stresses both scenarios and recovery performance under normal vs heavy load

### Seed Constraint (seed01 only)
- Stage A is smoke test, not production matrix
- Single deterministic seed sufficient for preflight validation
- Reduces Stage A row count and execution time while maintaining representative coverage

---

## Performance Notes

| Simulation | Nodes | Clusters | BS | Sim Time | Exec Time | Status |
|------------|-------|----------|----|---------|---------|----|
| F0_H0_A_S11_L1_seed01 | 5000 | 200 | 6 | 300s | ~4m 20s | ✅ |
| F0_H0_A_S11_L2_seed01 | 5000 | 200 | 6 | 300s | ~4m 35s | ✅ |
| F0_H0_B_S11_L1_seed01 | 5000 | 200 | 6 | 300s | ~4m 50s | ✅ |
| F0_H0_B_S11_L2_seed01 | 5000 | 200 | 6 | 300s | ~5m 10s | ✅ |
| F1_H1_A_S11_L1_seed01 | 5000 | 200 | 6 | 300s | ~4m 40s | ✅ |
| (... remaining rows) | 5000 | 200 | 6 | 300s | ~4–5m | ✅ |

**Average Execution Time**: ~4.7 minutes per 5000-node simulation

---

## Conclusion

✅ **Stage A Smoke Test Complete**

All 12 baseline and representative healing rows executed successfully. No failures, no partial runs, no import anomalies. Pipeline validated end-to-end at 5000 nodes and ready to proceed to Stage B (32-row healing family validation).

**GATE_A**: ✅ PASSED
