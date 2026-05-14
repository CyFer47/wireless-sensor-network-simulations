# S9 Stage B Execution Matrix

## Complete 32-Row Matrix

All 32 Stage B runs successfully executed and imported to PostgreSQL.

### F1_H1 Healing Family (8 rows)

| Index | Spec ID | Arch | Load | Seed | run_id | Status | Source |
|-------|---------|------|------|------|--------|---------|--------|
| 1 | F1_H1_A_S9_L1_seed01 | A | L1 | seed01 | 1032 | ✓ | Stage A reused |
| 2 | F1_H1_A_S9_L2_seed01 | A | L2 | seed01 | 1033 | ✓ | Stage A reused |
| 3 | F1_H1_B_S9_L1_seed01 | B | L1 | seed01 | 1034 | ✓ | Stage A reused |
| 4 | F1_H1_B_S9_L2_seed01 | B | L2 | seed01 | 1035 | ✓ | Stage A reused |
| 5 | F1_H1_A_S9_L1_seed02 | A | L1 | seed02 | 1040 | ✓ | New (Stage B) |
| 6 | F1_H1_A_S9_L2_seed02 | A | L2 | seed02 | 1041 | ✓ | New (Stage B) |
| 7 | F1_H1_B_S9_L1_seed02 | B | L1 | seed02 | 1042 | ✓ | New (Stage B) |
| 8 | F1_H1_B_S9_L2_seed02 | B | L2 | seed02 | 1043 | ✓ | New (Stage B) |

### F2_H2 Healing Family (8 rows)

| Index | Spec ID | Arch | Load | Seed | run_id | Status | Source |
|-------|---------|------|------|------|--------|---------|--------|
| 9 | F2_H2_A_S9_L1_seed01 | A | L1 | seed01 | 1044 | ✓ | New (Stage B) |
| 10 | F2_H2_A_S9_L2_seed01 | A | L2 | seed01 | 1045 | ✓ | New (Stage B) |
| 11 | F2_H2_B_S9_L1_seed01 | B | L1 | seed01 | 1046 | ✓ | New (Stage B) |
| 12 | F2_H2_B_S9_L2_seed01 | B | L2 | seed01 | 1047 | ✓ | New (Stage B) |
| 13 | F2_H2_A_S9_L1_seed02 | A | L1 | seed02 | 1048 | ✓ | New (Stage B) |
| 14 | F2_H2_A_S9_L2_seed02 | A | L2 | seed02 | 1049 | ✓ | New (Stage B) |
| 15 | F2_H2_B_S9_L1_seed02 | B | L1 | seed02 | 1050 | ✓ | New (Stage B) |
| 16 | F2_H2_B_S9_L2_seed02 | B | L2 | seed02 | 1051 | ✓ | New (Stage B) |

### F3_H3 Healing Family (8 rows)

| Index | Spec ID | Arch | Load | Seed | run_id | Status | Source |
|-------|---------|------|------|------|--------|---------|--------|
| 17 | F3_H3_A_S9_L1_seed01 | A | L1 | seed01 | 1052 | ✓ | New (Stage B) |
| 18 | F3_H3_A_S9_L2_seed01 | A | L2 | seed01 | 1053 | ✓ | New (Stage B) |
| 19 | F3_H3_B_S9_L1_seed01 | B | L1 | seed01 | 1054 | ✓ | New (Stage B) |
| 20 | F3_H3_B_S9_L2_seed01 | B | L2 | seed01 | 1055 | ✓ | New (Stage B) |
| 21 | F3_H3_A_S9_L1_seed02 | A | L1 | seed02 | 1056 | ✓ | New (Stage B) |
| 22 | F3_H3_A_S9_L2_seed02 | A | L2 | seed02 | 1057 | ✓ | New (Stage B) |
| 23 | F3_H3_B_S9_L1_seed02 | B | L1 | seed02 | 1058 | ✓ | New (Stage B) |
| 24 | F3_H3_B_S9_L2_seed02 | B | L2 | seed02 | 1059 | ✓ | New (Stage B) |

### F4_H4 Healing Family (8 rows)

| Index | Spec ID | Arch | Load | Seed | run_id | Status | Source |
|-------|---------|------|------|------|--------|---------|--------|
| 25 | F4_H4_A_S9_L1_seed01 | A | L1 | seed01 | 1036 | ✓ | Stage A reused |
| 26 | F4_H4_A_S9_L2_seed01 | A | L2 | seed01 | 1037 | ✓ | Stage A reused |
| 27 | F4_H4_B_S9_L1_seed01 | B | L1 | seed01 | 1038 | ✓ | Stage A reused |
| 28 | F4_H4_B_S9_L2_seed01 | B | L2 | seed01 | 1039 | ✓ | Stage A reused |
| 29 | F4_H4_A_S9_L1_seed02 | A | L1 | seed02 | 1060 | ✓ | New (Stage B) |
| 30 | F4_H4_A_S9_L2_seed02 | A | L2 | seed02 | 1061 | ✓ | New (Stage B) |
| 31 | F4_H4_B_S9_L1_seed02 | B | L1 | seed02 | 1062 | ✓ | New (Stage B) |
| 32 | F4_H4_B_S9_L2_seed02 | B | L2 | seed02 | 1063 | ✓ | New (Stage B) |

---

## Summary Statistics

### By Status
- **Reused from Stage A**: 8 rows
- **Newly executed (Stage B)**: 24 rows
- **Total Stage B**: 32 rows
- **Failed**: 0
- **Partial**: 0
- **Quarantined**: 0

### By Characteristic
- **Total with seed01**: 16 rows (8 reused Stage A + 8 new F2/F3)
- **Total with seed02**: 16 rows (8 direct new + 8 F2/F3 new)
- **Architecture A**: 16 rows
- **Architecture B**: 16 rows
- **Light load (L1)**: 16 rows
- **Heavy load (L2)**: 16 rows

### By Healing Family
- **F1_H1**: 8 rows (4 from Stage A, 4 new seed02)
- **F2_H2**: 8 rows (all new, both seeds)
- **F3_H3**: 8 rows (all new, both seeds)
- **F4_H4**: 8 rows (4 from Stage A, 4 new seed02)

### Map Lineage
- **map_S9_seed01**: 16 rows (8 F1/F4 seed01 reused + 8 F2/F3 seed01 new)
- **map_S9_seed02**: 16 rows (all new)

### Run ID Range
- **Reused**: 1032–1039 (from Stage A)
- **New**: 1040–1063 (Stage B execution)
- **Newest**: 1063 (F4_H4_B_S9_L2_seed02)

---

## Execution Characteristics

### Reuse Strategy
The batch runner pre-scanned the database and identified 8 existing Stage A rows that overlapped with Stage B requirements:
- F1_H1 seed01 all combinations (4 rows)
- F4_H4 seed01 all combinations (4 rows)

These 8 rows were **not re-simulated**, avoiding redundant computation and ensuring deterministic results.

### New Row Execution
24 new rows were executed in batch sequence:
- F1_H1 seed02 variants (4 rows)
- F2_H2 all variants (8 rows)
- F3_H3 all variants (8 rows)
- F4_H4 seed02 variants (4 rows)

### Execution Time
- **Total batch time**: ~5 minutes
- **24 new runs at ~12.5 seconds per run average**
- **0 timeouts, 0 crashes**
- **All 24 imports verified in DB**

---

## Notes

- All rows marked with `run_status='complete'` in database
- All rows use correct S9 scale configuration (4000 nodes, CH=160, BS=5)
- All rows have valid map_id references (map_S9_seed01 or map_S9_seed02)
- All rows have valid map_signature values (deterministic topology mapping)
- Stage B execution did not affect S9 Stage A data or S1–S8 scales
