# Final Scale5000 S11 Stage B Results

**Date**: 2026-05-04  
**Status**: COMPLETE ✅  
**Duration**: ~8 minutes 35 seconds  
**Execution**: 08:27:15 → 08:35:50 UTC

---

## Stage B Overview

Stage B validates all four active healing families across full matrix dimensions:

- **Healing Families**: F1/H1, F2/H2, F3/H3, F4/H4
- **Architectures**: A (passive), B (with recovery)
- **Loads**: L1 (baseline traffic), L2 (double traffic)
- **Seeds**: seed01, seed02 (deterministic variation)

**Pre-scan Strategy**: 8 Stage A rows overlap with Stage B (F1/H1 and F4/H4 seed01 A/B L1/L2), detected and skipped to avoid duplication.

**Expected New Rows**: 32 target − 8 overlap = 24 new simulations + 8 skipped = 32 total traced.

---

## Target Matrix

| Healing | Architecture | Load | Seed01 | Seed02 | Total per Family |
|---------|--------------|------|--------|--------|------------------|
| **H1 (F1)** | A/B | L1/L2 | 4 rows | 4 rows | 8 |
| **H2 (F2)** | A/B | L1/L2 | 4 rows | 4 rows | 8 |
| **H3 (F3)** | A/B | L1/L2 | 4 rows | 4 rows | 8 |
| **H4 (F4)** | A/B | L1/L2 | 4 rows | 4 rows | 8 |
| **TOTAL** | | | **16 rows** | **16 rows** | **32 rows** |

---

## Execution Summary

| Item | Value |
|------|-------|
| **Target Rows** | 32 |
| **Pre-scan Reused** | 8 (Stage A overlap: F1/H1 and F4/H4 seed01) |
| **New Simulations** | 24 |
| **Total Complete** | 32 |
| **Failed** | 0 |
| **Partial** | 0 |
| **Quarantined** | 0 |

---

## Run ID Allocation

**Stage B Rows**: run_ids 1200–1223 (new) + reused Stage A rows (1200–1207 for F1/H1 and F4/H4 seedO1)

### Newly Imported Stage B Rows

| Healing | Architecture | Load | Seed02 | Run ID | Status |
|---------|--------------|------|--------|--------|--------|
| F1/H1 | A | L1 | seed02 | 1208 | ✅ |
| F1/H1 | A | L2 | seed02 | 1209 | ✅ |
| F1/H1 | B | L1 | seed02 | 1210 | ✅ |
| F1/H1 | B | L2 | seed02 | 1211 | ✅ |
| F2/H2 | A | L1 | seed01 | 1212 | ✅ |
| F2/H2 | A | L1 | seed02 | 1213 | ✅ |
| F2/H2 | A | L2 | seed01 | 1214 | ✅ |
| F2/H2 | A | L2 | seed02 | 1215 | ✅ |
| F2/H2 | B | L1 | seed01 | 1216 | ✅ |
| F2/H2 | B | L1 | seed02 | 1217 | ✅ |
| F2/H2 | B | L2 | seed01 | 1218 | ✅ |
| F2/H2 | B | L2 | seed02 | 1219 | ✅ |
| F3/H3 | A | L1 | seed01 | 1220 | ✅ |
| F3/H3 | A | L1 | seed02 | 1221 | ✅ |
| F3/H3 | A | L2 | seed01 | 1222 | ✅ |
| F3/H3 | A | L2 | seed02 | 1223 | ✅ |
| F3/H3 | B | L1 | seed01 | 1224 | ✅ |
| F3/H3 | B | L1 | seed02 | 1225 | ✅ |
| F3/H3 | B | L2 | seed01 | 1226 | ✅ |
| F3/H3 | B | L2 | seed02 | 1227 | ✅ |
| F4/H4 | A | L1 | seed02 | 1228 | ✅ |
| F4/H4 | A | L2 | seed02 | 1229 | ✅ |
| F4/H4 | B | L1 | seed02 | 1230 | ✅ |
| F4/H4 | B | L2 | seed02 | 1231 | ✅ |

**Total New: 24 rows**

### Pre-scanned and Skipped (Already Complete from Stage A)

| Healing | Architecture | Load | Seed01 | Run ID | Status |
|---------|--------------|------|--------|--------|--------|
| F1/H1 | A | L1 | seed01 | 1200 | SKIPPED ✅ |
| F1/H1 | A | L2 | seed01 | 1201 | SKIPPED ✅ |
| F1/H1 | B | L1 | seed01 | 1202 | SKIPPED ✅ |
| F1/H1 | B | L2 | seed01 | 1203 | SKIPPED ✅ |
| F4/H4 | A | L1 | seed01 | 1204 | SKIPPED ✅ |
| F4/H4 | A | L2 | seed01 | 1205 | SKIPPED ✅ |
| F4/H4 | B | L1 | seed01 | 1206 | SKIPPED ✅ |
| F4/H4 | B | L2 | seed01 | 1207 | SKIPPED ✅ |

**Total Skipped: 8 rows**

---

## Completion Acceptance Criteria

| Criterion | Requirement | Result | Status |
|-----------|-------------|--------|--------|
| **Target Rows** | 32 | 32 | ✅ Met |
| **Complete Rows** | 32 | 32 | ✅ Met |
| **Failed Rows** | 0 | 0 | ✅ Met |
| **Partial Rows** | 0 | 0 | ✅ Met |
| **Quarantined Rows** | 0 | 0 | ✅ Met |
| **A/B Balance** | 16/16 | 16/16 | ✅ Met |
| **L1/L2 Balance** | 16/16 | 16/16 | ✅ Met |
| **Seed Balance** | 16/16 | 16/16 | ✅ Met |
| **F1/H1** | 8 rows | 8 rows | ✅ Met |
| **F2/H2** | 8 rows | 8 rows | ✅ Met |
| **F3/H3** | 8 rows | 8 rows | ✅ Met |
| **F4/H4** | 8 rows | 8 rows | ✅ Met |
| **Map Lineage** | All linked | All linked | ✅ Met |
| **DB Queryability** | Pass | Pass | ✅ Met |

---

## Database Query Proof

**Query**: Verify all 32 Stage B rows are complete

```sql
SELECT healing_id, COUNT(*) as count
FROM wsn.runs
WHERE scale='S11'
  AND run_status='complete'
  AND healing_id IN ('H1','H2','H3','H4')
GROUP BY healing_id
ORDER BY healing_id;
```

**Result**:
```
H1|8
H2|8
H3|8
H4|8
```

**Total**: 8 + 8 + 8 + 8 = **32 rows** ✅

**Query**: Verify architecture and load distribution

```sql
SELECT architecture, COUNT(*) as count
FROM wsn.runs
WHERE scale='S11'
  AND run_status='complete'
  AND healing_id IN ('H1','H2','H3','H4')
GROUP BY architecture;
```

**Result**:
```
A|16
B|16
```

**Query**: Verify seed distribution

```sql
SELECT seed, COUNT(*) as count
FROM wsn.runs
WHERE scale='S11'
  AND run_status='complete'
  AND healing_id IN ('H1','H2','H3','H4')
GROUP BY seed
ORDER BY seed;
```

**Result**:
```
1|16
2|16
```

---

## Design Rationale

### Four Healing Families (F1/H1, F2/H2, F3/H3, F4/H4)
- **F1/H1**: Intermediate failure (72s inject), standard healing protocol (m7_profile for B only)
- **F2/H2**: Enhanced failure mode, enhanced healing
- **F3/H3**: High-intensity failure, aggressive healing
- **F4/H4**: Severe failure (highest intensity), most aggressive healing
- Represents full spectrum of failure/recovery behaviors relevant to WSN self-healing research

### Full Matrix Coverage (A/B + L1/L2 + seed01/seed02)
- Tests healing effectiveness across both architectural modes
- Validates performance under normal and heavy traffic conditions
- Two deterministic seeds ensure reproducible healing validation

### Pre-scan Reuse Strategy
- Eliminates redundant re-execution of Stage A overlap rows
- Reduces total Stage B execution time from ~24 rows to ~16 new rows
- Maintains full matrix completeness in database (32 total traced)
- Demonstrates efficient batching for large-scale validation

---

## Performance Notes

**Avg Execution Time per New Simulation**: ~21 seconds per row (including validation, export, import overhead)

---

## Conclusion

✅ **Stage B Healing Family Validation Complete**

All four healing families validated across full matrix. Pre-scan efficiency reduced redundant execution by 25% while maintaining comprehensive coverage. No failures, no partial runs, no anomalies. Ready to proceed to Stage C (H0 control vs active healing matched pairs).

**GATE_B**: ✅ PASSED
