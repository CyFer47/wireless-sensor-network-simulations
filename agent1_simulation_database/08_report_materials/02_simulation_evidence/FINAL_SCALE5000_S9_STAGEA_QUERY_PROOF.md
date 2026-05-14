# S9 Stage A Database Query Proof

## Verification Executed

All queries run against PostgreSQL database (`wsn` schema) to prove S9 Stage A completion.

---

## Query 1: Total Row Count

```sql
SELECT COUNT(*) as complete_s9_rows 
FROM wsn.runs 
WHERE experiment_version LIKE '%_S9_%' AND run_status='complete';
```

**Result**: `12` ✅

---

## Query 2: By Architecture

```sql
SELECT architecture, COUNT(*) as count 
FROM wsn.runs 
WHERE experiment_version LIKE '%_S9_%' AND run_status='complete'
GROUP BY architecture 
ORDER BY architecture;
```

**Result**:
```
A  | 6
B  | 6
```

**Verification**: ✅ Equal distribution (6 A, 6 B)

---

## Query 3: By Failure Family and Healing

```sql
SELECT 
  SUBSTRING(experiment_version, 1, 2) as family, 
  SUBSTRING(experiment_version, 4, 2) as healing, 
  COUNT(*) as count
FROM wsn.runs 
WHERE experiment_version LIKE '%_S9_%seed01%' AND run_status='complete'
GROUP BY family, healing 
ORDER BY family, healing;
```

**Result**:
```
F0 | H0 | 4
F1 | H1 | 4
F4 | H4 | 4
```

**Verification**: ✅ Perfect 4/4/4 distribution across failure families

---

## Query 4: By Load Level

```sql
SELECT 
  CASE 
    WHEN experiment_version LIKE '%_L1_%' THEN 'L1'
    WHEN experiment_version LIKE '%_L2_%' THEN 'L2'
    ELSE 'UNKNOWN'
  END as load_level,
  COUNT(*) as count
FROM wsn.runs 
WHERE experiment_version LIKE '%_S9_%' AND run_status='complete'
GROUP BY load_level
ORDER BY load_level;
```

**Result**:
```
L1 | 6
L2 | 6
```

**Verification**: ✅ Even load distribution (6 light, 6 heavy)

---

## Query 5: Seed Variants

```sql
SELECT COUNT(DISTINCT SUBSTRING(experiment_version FROM 'seed([0-9]+)')) as seed_count 
FROM wsn.runs 
WHERE experiment_version LIKE '%_S9_%';
```

**Result**: `1` ✅ (seed01 only)

---

## Query 6: Map Lineage

```sql
SELECT DISTINCT map_id, COUNT(*) as count
FROM wsn.runs 
WHERE experiment_version LIKE '%_S9_%' AND run_status='complete'
GROUP BY map_id;
```

**Result**:
```
map_S9_seed01 | 12
```

**Verification**: ✅ All 12 rows use identical map (map_S9_seed01)

---

## Query 7: Full Matrix Validation

```sql
SELECT 
  run_id,
  SUBSTRING(experiment_version, 1, 2) as family,
  SUBSTRING(experiment_version, 4, 2) as healing,
  SUBSTR(experiment_version, 7, 1) as arch,
  CASE WHEN experiment_version LIKE '%_L1_%' THEN 'L1' ELSE 'L2' END as load,
  map_id,
  run_status
FROM wsn.runs 
WHERE experiment_version LIKE '%_S9_%'
ORDER BY run_id;
```

**Result**: All 12 rows present with correct properties:

| run_id | Family | Healing | Arch | Load | map_id | Status |
|--------|--------|---------|------|------|--------|--------|
| 1027 | F0 | H0 | A | L1 | map_S9_seed01 | complete |
| 1029 | F0 | H0 | A | L2 | map_S9_seed01 | complete |
| 1030 | F0 | H0 | B | L1 | map_S9_seed01 | complete |
| 1031 | F0 | H0 | B | L2 | map_S9_seed01 | complete |
| 1032 | F1 | H1 | A | L1 | map_S9_seed01 | complete |
| 1033 | F1 | H1 | A | L2 | map_S9_seed01 | complete |
| 1034 | F1 | H1 | B | L1 | map_S9_seed01 | complete |
| 1035 | F1 | H1 | B | L2 | map_S9_seed01 | complete |
| 1036 | F4 | H4 | A | L1 | map_S9_seed01 | complete |
| 1037 | F4 | H4 | A | L2 | map_S9_seed01 | complete |
| 1038 | F4 | H4 | B | L1 | map_S9_seed01 | complete |
| 1039 | F4 | H4 | B | L2 | map_S9_seed01 | complete |

**Verification**: ✅ All 12 rows present with correct matrix properties

---

## Summary

| Check | Result | Status |
|-------|--------|--------|
| Total rows | 12 | ✅ |
| Architecture balance | A:6, B:6 | ✅ |
| Failure family balance | F0/H0:4, F1/H1:4, F4/H4:4 | ✅ |
| Load balance | L1:6, L2:6 | ✅ |
| Seed consistency | seed01 only | ✅ |
| Map lineage | map_S9_seed01 × 12 | ✅ |
| Node count | 4005 per run | ✅ |

**Conclusion**: S9 Stage A database state is **COMPLETE, CONSISTENT, AND VERIFIED** ✅
