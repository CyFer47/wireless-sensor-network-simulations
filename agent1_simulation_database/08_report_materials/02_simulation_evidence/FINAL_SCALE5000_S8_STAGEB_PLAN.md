# Final Scale5000 S8 Stage B: Healing-Family Validation Plan

## Overview

**Final Scale5000 S8 Stage B** extends Phase 1 simulation coverage to validate healing-family behavior across all four main healing strategies (H1, H2, H3, H4) at the S8 scale (3500 nodes).

This stage completes the Stage A baseline (F0/H0, F1/H1, F4/H4 with seed01) by adding:

1. **Complete healing-family matrix** (F1–F4, H1–H4)
2. **Dual-seed variability** (seed01 + seed02) for each family
3. **Balanced architecture coverage** (A/B, L1/L2 for each family/seed)
4. **Deterministic topology reproducibility** (seed-specific maps, deterministic node placement)

## Scope

| Dimension | Coverage | Count |
|-----------|----------|-------|
| Scale | S8 (3500 nodes, 140 CH, 5 BS, 950×950 m) | 1 |
| Healing families | H1, H2, H3, H4 | 4 |
| Failure families | F1, F2, F3, F4 | 4 |
| Architectures | A, B | 2 |
| Loads | L1, L2 | 2 |
| Seeds | seed01, seed02 | 2 |
| **Stage B target rows** | — | **32** |

## Known Overlap from Stage A

Stage A already completed 8 rows with seed01:

- `F1_H1_A_S8_L1_seed01` (run_id 955)
- `F1_H1_A_S8_L2_seed01` (run_id 956)
- `F1_H1_B_S8_L1_seed01` (run_id 957)
- `F1_H1_B_S8_L2_seed01` (run_id 958)
- `F4_H4_A_S8_L1_seed01` (run_id 959)
- `F4_H4_A_S8_L2_seed01` (run_id 960)
- `F4_H4_B_S8_L1_seed01` (run_id 961)
- `F4_H4_B_S8_L2_seed01` (run_id 962)

**Stage B execution will skip these 8 rows** and execute only the **24 missing rows**.

## Execution Strategy

### Map Preparation

Two deterministic S8 topology maps are prepared:

| Seed | Signature | Location |
|------|-----------|----------|
| seed01 | `fb969a468352b224ac76c1dce90944cf5f7dd6acc148c153e89692e2ef04ceb5` | `maps/examples/map_S8_seed01/` |
| seed02 | `9d9cbda6449d002e75fc6dc97c8cf523044b156c6e3ec5d2656fa19f49a9c21f` | `maps/examples/map_S8_seed02/` |

### Batch Execution

Each missing run follows this pipeline:

1. **Spec generation** – Dynamically generate run-spec from Stage B matrix cell
2. **Spec validation** – Confirm runnable, complete, and schema-compliant
3. **Map linkage** – Verify deterministic topology matches seed and scale
4. **Simulation** – Run ns-3 M4 scenario library with architecture A/B, failure family, recovery profile
5. **Export** – Stage results to `outputs/<run_spec_id>/`
6. **PostgreSQL import** – Persist to `wsn.runs` and related tables
7. **Verification** – Confirm run_status="complete" and metadata consistency
8. **State update** – Log completion in resumable state file

### Resumable Execution

The batch runner maintains resumable state:

- **State file** – `outputs/s8_stageb_state.json` – 32 entries (all rows, skipping "ok" entries)
- **Quarantine file** – `outputs/s8_stageb_quarantine.json` – failed runs that blocked the batch
- **Log file** – `outputs/s8_stageb_batch.log` – execution trace with timing and error details

If a run fails, the batch stops, quarantines the failing run, and can resume from the state file.

## Scale Rule (S8)

| Parameter | Value |
|-----------|-------|
| Node count | 3500 |
| Cluster count | 140 |
| Base station count | 5 |
| Simulation time | 230 s |
| Area dimensions | 950 × 950 m |
| Failure injection time | 46 s |
| Recovery delay | 4 s |
| Traffic interval | 3 s |
| Aggregation interval | 4 s |
| Dashboard interval | 1 s |

## Variant Definitions

| Variant | Description |
|---------|-------------|
| V3 | Recovery enabled (bsbssp_profile for arch B, disabled for arch A; m7_profile) |

## Expected Outcomes

After Stage B completion:

- ✅ 32 Stage B target rows in `wsn.runs` with scale='S8'
- ✅ All 32 rows have run_status='complete'
- ✅ 4 healing families balanced (H1, H2, H3, H4): 8 rows each
- ✅ 4 failure families balanced (F1, F2, F3, F4): 8 rows each
- ✅ 2 architectures balanced (A, B): 16 rows each
- ✅ 2 loads balanced (L1, L2): 16 rows each
- ✅ 2 seeds balanced (seed01, seed02): 16 rows each
- ✅ Map lineage present (map_id, map_signature populated)
- ✅ Queryable by all axes (scale, healing_id, failure_family, architecture, load, seed)
- ✅ dashboard/API visibility maintained
- ✅ S1–S7 data unaffected
- ✅ Stage A runs (951–962) remain intact
- ✅ 0 failed, 0 partial, 0 quarantined

## Acceptance Criteria

**Stage B passes only if:**

| Criterion | Status |
|-----------|--------|
| 32 target rows exist in DB | ✓ / ✗ |
| All 32 rows are complete | ✓ / ✗ |
| 24 new runs executed and imported successfully | ✓ / ✗ |
| 8 Stage A overlap rows reused | ✓ / ✗ |
| 0 failed runs | ✓ / ✗ |
| 0 partial runs | ✓ / ✗ |
| 0 quarantined runs | ✓ / ✗ |
| A/B balanced | ✓ / ✗ |
| L1/L2 balanced | ✓ / ✗ |
| seed01/seed02 balanced | ✓ / ✗ |
| F1–F4 all visible (8 rows each) | ✓ / ✗ |
| H1–H4 all visible (8 rows each) | ✓ / ✗ |
| Dashboard/API visibility maintained | ✓ / ✗ |
| S1–S7 unaffected | ✓ / ✗ |
| S8 Stage A (951–962) unaffected | ✓ / ✗ |

---

**Stage B is part of Final Scale5000 for Phase 1 completion.**

- **Phase**: Phase 1 (simulation & PostgreSQL validation)
- **Agent**: Agent 1 (VMware ns-3 / PostgreSQL / Dashboard)
- **Next stage**: S8 Stage C (optional production extension)
- **Agent 2 scope**: MATLAB analytics on S8 Stages A–B combined

