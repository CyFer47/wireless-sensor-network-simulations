# Final Scale5000 S8 Stage B: Matrix Definition

## Stage B Target: 32 Unique Rows

**S8 Stage B** targets all healing families (F1–F4 with H1–H4) at two seeds, across all architecture/load combinations.

### Full Matrix

#### F1/H1 (8 rows)

| Architecture | Load | seed01 | seed02 |
|-------------|------|--------|--------|
| A | L1 | F1_H1_A_S8_L1_seed01 ✓(A) | F1_H1_A_S8_L1_seed02 |
| A | L2 | F1_H1_A_S8_L2_seed01 ✓(A) | F1_H1_A_S8_L2_seed02 |
| B | L1 | F1_H1_B_S8_L1_seed01 ✓(A) | F1_H1_B_S8_L1_seed02 |
| B | L2 | F1_H1_B_S8_L2_seed01 ✓(A) | F1_H1_B_S8_L2_seed02 |

**(A) = Already complete in Stage A**

#### F2/H2 (8 rows)

| Architecture | Load | seed01 | seed02 |
|-------------|------|--------|--------|
| A | L1 | F2_H2_A_S8_L1_seed01 | F2_H2_A_S8_L1_seed02 |
| A | L2 | F2_H2_A_S8_L2_seed01 | F2_H2_A_S8_L2_seed02 |
| B | L1 | F2_H2_B_S8_L1_seed01 | F2_H2_B_S8_L1_seed02 |
| B | L2 | F2_H2_B_S8_L2_seed01 | F2_H2_B_S8_L2_seed02 |

**All 8 new rows**

#### F3/H3 (8 rows)

| Architecture | Load | seed01 | seed02 |
|-------------|------|--------|--------|
| A | L1 | F3_H3_A_S8_L1_seed01 | F3_H3_A_S8_L1_seed02 |
| A | L2 | F3_H3_A_S8_L2_seed01 | F3_H3_A_S8_L2_seed02 |
| B | L1 | F3_H3_B_S8_L1_seed01 | F3_H3_B_S8_L1_seed02 |
| B | L2 | F3_H3_B_S8_L2_seed01 | F3_H3_B_S8_L2_seed02 |

**All 8 new rows**

#### F4/H4 (8 rows)

| Architecture | Load | seed01 | seed02 |
|-------------|------|--------|--------|
| A | L1 | F4_H4_A_S8_L1_seed01 ✓(A) | F4_H4_A_S8_L1_seed02 |
| A | L2 | F4_H4_A_S8_L2_seed01 ✓(A) | F4_H4_A_S8_L2_seed02 |
| B | L1 | F4_H4_B_S8_L1_seed01 ✓(A) | F4_H4_B_S8_L1_seed02 |
| B | L2 | F4_H4_B_S8_L2_seed01 ✓(A) | F4_H4_B_S8_L2_seed02 |

**(A) = Already complete in Stage A**

---

## Summary

| Dimension | F1 | F2 | F3 | F4 | Total |
|-----------|----|----|----|----|-------|
| **New rows (seed02)** | 4 | 8 | 8 | 4 | **24** |
| **Stage A overlap** | 4 | 0 | 0 | 4 | **8** |
| **Total per family** | 8 | 8 | 8 | 8 | **32** |

### Reuse from Stage A

Four seed01 cells are already complete from Stage A:

1. `F1_H1_A_S8_L1_seed01` (run_id 955) → Row 1
2. `F1_H1_A_S8_L2_seed01` (run_id 956) → Row 2
3. `F1_H1_B_S8_L1_seed01` (run_id 957) → Row 3
4. `F1_H1_B_S8_L2_seed01` (run_id 958) → Row 4
5. `F4_H4_A_S8_L1_seed01` (run_id 959) → Row 21
6. `F4_H4_A_S8_L2_seed01` (run_id 960) → Row 22
7. `F4_H4_B_S8_L1_seed01` (run_id 961) → Row 23
8. `F4_H4_B_S8_L2_seed01` (run_id 962) → Row 24

The batch runner will **skip these 8 rows** and execute only the **24 missing rows**.

---

## Variant Mapping

All F1–F4 rows use **V3 (recovery enabled)** with m7_profile:

- **Architecture A**: Recovery profile disabled (baseline comparison)
- **Architecture B**: Recovery profile = `bsbssp_profile` (active recovery via BSBSSP controller)

---

## Deterministic Maps

| Seed | File | Signature |
|------|------|-----------|
| seed01 | `maps/examples/map_S8_seed01/manifest.json` | `fb969a468352b224ac76c1dce90944cf5f7dd6acc148c153e89692e2ef04ceb5` |
| seed02 | `maps/examples/map_S8_seed02/manifest.json` | `9d9cbda6449d002e75fc6dc97c8cf523044b156c6e3ec5d2656fa19f49a9c21f` |

Each topology is deterministic and reproducible from seed and scale rule.

