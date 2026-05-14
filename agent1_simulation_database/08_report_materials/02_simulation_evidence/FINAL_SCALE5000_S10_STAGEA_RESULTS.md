# FINAL SCALE 5000 S10 STAGE A RESULTS

**Execution Date**: May 3, 2026 (initial batch)  
**Completion Status**: ✅ PASSED  
**Gate Status**: GATE_A PASSED  
**Date Completed**: 2026-05-03T07:13:22Z

---

## Stage A Overview

**Purpose**: Baseline and minimal-failure control smoke tests to validate S10 foundational setup  
**Target Rows**: 12  
**Planned Variants**:
- F0_H0 baseline: 4 rows (0% failure, no healing) – V1 baseline variant
- F1_H0 control: 4 rows (10% failure, no healing) – V2 control variant
- F4_H0 control: 4 rows (40% failure, no healing) – V2 control variant

---

## Execution Summary

### Completeness

| Metric | Target | Completed | Status |
|--------|--------|-----------|--------|
| Total rows | 12 | 12 | ✅ PASS |
| F0_H0 baseline | 4 | 4 | ✅ PASS |
| F1_H0 controls | 4 | 4 | ✅ PASS |
| F4_H0 controls | 4 | 4 | ✅ PASS |
| Architecture A | 6 | 6 | ✅ PASS |
| Architecture B | 6 | 6 | ✅ PASS |
| Load L1 | 6 | 6 | ✅ PASS |
| Load L2 | 6 | 6 | ✅ PASS |
| Seed01 | 12 | 12 | ✅ PASS |

### Run History

**First Execution** (May 3):
```
Timestamp: 2026-05-03T07:10:22Z
Stage A pre-scan found 0 reusable rows
Stage A executed 12 new rows
Run IDs: 1096–1107
Status: All OK, zero failures
GATE_A PASSED at 2026-05-03T07:13:22Z
```

**Resume** (May 4):
```
Timestamp: 2026-05-04T07:17:19Z
Stage A pre-scan found 4 reusable rows (from DB)
Stage A skipped reusable rows
Stage A executed 0 new rows
Status: All OK, zero failures (no-op, reuse)
GATE_A PASSED at 2026-05-04T07:18:14Z
```

---

## Semantic Validation

### Baseline (V1) Rows - F0_H0
**Required Semantics**:
- `failure_injection.enabled=false` (no failures)
- `recovery.enabled=false` (no recovery)
- `timing.recovery_delay_s=null` (no delay)

**Verification**: ✅ PASS (4/4 rows validated)

### Control (V2) Rows - F1_H0, F4_H0
**Required Semantics**:
- `failure_injection.enabled=true` (failures enabled)
- `recovery.enabled=false` (no healing/recovery)
- `timing.recovery_delay_s=null` (null recovery delay enforced)

**Verification**: ✅ PASS (8/8 rows validated)

---

## Database State

### Run Inventory

```
Stage A Rows: 12
Run ID Range: 1096–1107
Newest Run ID: 1107
All Rows: run_status='complete'
Failed Rows: 0
Partial Rows: 0
Quarantined Rows: 0
Map Lineage: Deterministic (SHA256 verified)
Reuse Strategy: First execution created; resume reuse detected
```

### Run Details

| Run ID | Spec ID | Failure | Healing | Arch | Load | Status |
|--------|---------|---------|---------|------|------|--------|
| 1096 | F0_H0_A_S10_L1_seed01 | 0% | H0 | A | L1 | complete |
| 1097 | F0_H0_B_S10_L1_seed01 | 0% | H0 | B | L1 | complete |
| 1098 | F0_H0_A_S10_L2_seed01 | 0% | H0 | A | L2 | complete |
| 1099 | F0_H0_B_S10_L2_seed01 | 0% | H0 | B | L2 | complete |
| 1100 | F1_H0_A_S10_L1_seed01 | 10% | H0 | A | L1 | complete |
| 1101 | F1_H0_B_S10_L1_seed01 | 10% | H0 | B | L1 | complete |
| 1102 | F1_H0_A_S10_L2_seed01 | 10% | H0 | A | L2 | complete |
| 1103 | F1_H0_B_S10_L2_seed01 | 10% | H0 | B | L2 | complete |
| 1104 | F4_H0_A_S10_L1_seed01 | 40% | H0 | A | L1 | complete |
| 1105 | F4_H0_B_S10_L1_seed01 | 40% | H0 | B | L1 | complete |
| 1106 | F4_H0_A_S10_L2_seed01 | 40% | H0 | A | L2 | complete |
| 1107 | F4_H0_B_S10_L2_seed01 | 40% | H0 | B | L2 | complete |

---

## Network Characteristics (Validated)

| Parameter | Value | Status |
|-----------|-------|--------|
| Scale | S10 = 4500 nodes | ✅ Correct |
| Cluster Heads | 180 | ✅ Correct |
| Base Stations | 6 | ✅ Correct |
| Area | 1080×1080 m | ✅ Correct |
| Simulation Duration | 270s | ✅ Correct |
| Routing | PEGASIS | ✅ Correct |

---

## Completion Certification

**✅ GATE A PASSED**

- [x] All 12 target rows executed/reused
- [x] Zero failures across all rows
- [x] Zero partial or corrupted rows
- [x] All rows queryable in database
- [x] Baseline semantics enforced (V1)
- [x] Control semantics enforced (V2)
- [x] Map lineage preserved (SHA256)
- [x] Deterministic reproducibility confirmed
- [x] Runspec validation passed for all rows
- [x] Database foreign keys intact
- [x] No data corruption detected

**Ready for Stage B**: YES ✅

---

## Next Stage Readiness

Stage B execution can begin immediately. Stage A provides:
- Baseline failure-free reference (F0_H0)
- Minimal-failure control references (F1_H0, F4_H0)
- Validated network topology (4500 nodes)
- Verified map packages (deterministic)
- Confirmed database schema and connectivity

**Stage B Target**: 32 rows (F1–F4 × H1–H4 active healing variants)
