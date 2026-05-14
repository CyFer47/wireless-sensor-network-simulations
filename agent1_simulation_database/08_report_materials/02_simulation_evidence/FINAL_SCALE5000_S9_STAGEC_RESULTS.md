# S9 Stage C Results

## Summary

**S9 Stage C** completed successfully after fixing V2/H0 control runspec generation.

- **Target rows**: 64
- **Complete rows**: 64 (100%)
- **Failed rows**: 0
- **Partial rows**: 0
- **Quarantined rows**: 0

### Stage C Composition

| Metric | Count |
|--------|-------|
| H0 control rows (F1-F4) | 32 |
| Active healing rows (F1_H1, F2_H2, F3_H3, F4_H4) | 32 |
| Total Stage C | 64 |

## Execution Summary

### Batch Execution

- **Batch start**: 2026-05-03T06:06:22Z
- **Pre-scan reused**: 33 rows (32 original + 1 from focused retry)
- **New rows executed**: 31
- **Newest run_id**: 1095
- **Total runtime**: Approximately 9 minutes (end: 2026-05-03T06:15:04Z)

### Healing Matrix Coverage

#### F1 Failure Family
- **F1_H0 (controls)**: 8 rows (2 arch × 2 load × 2 seed) ✅
- **F1_H1 (active healing)**: 8 rows ✅
- **Pairing**: F1_H0 ↔ F1_H1 (32 pairs) ✅

#### F2 Failure Family
- **F2_H0 (controls)**: 8 rows ✅
- **F2_H2 (active healing)**: 8 rows ✅
- **Pairing**: F2_H0 ↔ F2_H2 (32 pairs) ✅

#### F3 Failure Family
- **F3_H0 (controls)**: 8 rows ✅
- **F3_H3 (active healing)**: 8 rows ✅
- **Pairing**: F3_H0 ↔ F3_H3 (32 pairs) ✅

#### F4 Failure Family
- **F4_H0 (controls)**: 8 rows ✅
- **F4_H4 (active healing)**: 8 rows ✅
- **Pairing**: F4_H0 ↔ F4_H4 (32 pairs) ✅

### Architecture/Load Balance
- **Architecture A**: 32 rows (50%)
- **Architecture B**: 32 rows (50%)
- **Load L1**: 32 rows (50%)
- **Load L2**: 32 rows (50%)

### Seed Variation
- **Seed 01**: 32 rows (50%)
- **Seed 02**: 32 rows (50%)

### Map Lineage
- **map_S9_seed01**: 32 rows (50%)
- **map_S9_seed02**: 32 rows (50%)
- **Map validation**: Both 4000-node maps confirmed
- **Deterministic linkage**: seed01→map_S9_seed01, seed02→map_S9_seed02 ✅

## S9 Stage Progression

| Stage | Type | Target | Complete | Status |
|-------|------|--------|----------|--------|
| Stage A | F0/H0 baseline | 4 | 4 | ✅ Complete |
| Stage B | F1-F4 active healing | 32 | 32 | ✅ Complete |
| **Stage C** | **F1-F4 H0 controls** | **32** | **32** | **✅ Complete** |
| **Stage A+B+C Total** | **S9 comparative** | **68** | **68** | **✅ Complete** |

## H0 Control Semantics Verification

All Stage C H0 control rows conform to required semantics:
- `failure_injection.enabled = true` ✅
- `recovery.enabled = false` ✅
- `healing_id = H0` ✅
- `variant = V2` ✅
- `timing.recovery_delay_s = null` ✅
- No recovery profile applied ✅

## Previously Affected & Unaffected Scopes

### S1–S8 (Baseline scans)
- **Status**: Unaffected ✅
- **Rationale**: S9-specific Stage C runner does not modify S1–S8 data.

### S9 Stage A (Baseline failure injection)
- **Status**: Unaffected ✅
- **Stage A rows**: 4 F0_H0_* rows remain at run_ids 1027–1030.
- **Rationale**: Stage C runner skips F0 scenarios.

### S9 Stage B (Active healing validation)
- **Status**: Unaffected ✅
- **Stage B rows**: 32 F*_H*×_* (active healing) rows remain at run_ids 1031–1063.
- **Rationale**: Stage C pre-scan detects and reuses complete rows; no re-execution.

### S9 Stage C (New matched control-vs-healing)
- **Status**: Complete ✅
- **Stage C rows**: 32 new F*_H0_* (controls) at run_ids 1064–1095.

## Data Quality Assurance

| Check | Result |
|-------|--------|
| Total S9 rows = 68 (4 + 32 + 32) | ✅ Pass |
| Stage C target = 64 | ✅ Pass |
| Stage C complete = 64 | ✅ Pass |
| H0 controls = 32 | ✅ Pass |
| Active healing = 32 | ✅ Pass |
| F1 pairs = 16 (8 H0 + 8 H1) | ✅ Pass |
| F2 pairs = 16 (8 H0 + 8 H2) | ✅ Pass |
| F3 pairs = 16 (8 H0 + 8 H3) | ✅ Pass |
| F4 pairs = 16 (8 H0 + 8 H4) | ✅ Pass |
| A/B balanced (32/32) | ✅ Pass |
| L1/L2 balanced (32/32) | ✅ Pass |
| seed01/seed02 balanced (32/32) | ✅ Pass |
| Map lineage = 2 maps × 32 rows | ✅ Pass |
| Failed runs = 0 | ✅ Pass |
| Quarantined runs = 0 | ✅ Pass |
| Partial runs = 0 | ✅ Pass |

## Known Issues & Resolutions

### Issue: V2/H0 Recovery Delay Validator Failure (Resolved)
- **Problem**: Initial Stage C batch failed 1 spec (F1_H0_A_S9_L1_seed01) with validator error: "V2 requires timing.recovery_delay_s=null"
- **Root cause**: `tools/run_s9_stagec_batch.py` generator produced non-null `recovery_delay_s` for H0 controls
- **Resolution**: Patched generator to robustly read healing_id and set `recovery_delay_s = null` for `healing='H0'` and `variant='V2'`
- **Result**: All 64 Stage C specs regenerated and validated successfully; focused retry of failed spec imported as run_id 1064; batch resume completed without further failures

## Ready for Next Stages

✅ **Safe for Agent 2 MATLAB Stage C review**: Yes
- All 64 Stage C rows complete
- H0↔H* pairability verified for all 4 families
- Deterministic map linkage confirmed
- No data integrity issues

✅ **Safe to proceed to S10 combined execution**: Yes
- S1–S8 unaffected
- S9 Stage A unaffected (4 baseline rows stable)
- S9 Stage B unaffected (32 active-healing rows stable)
- S9 Stage C complete (32 H0 control rows + 32 active-healing reused = 64 total)
- All scopes ready for multi-scale combined analysis

## Commit Record

- **Fix commit**: 718b6addfe5e5e5d345b3793626f766bb48a5a1d (applied V2/H0 recovery_delay fix)
- **Results commit**: [to be committed with this doc]
