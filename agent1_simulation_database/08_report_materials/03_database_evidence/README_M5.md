# Milestone M5: Database Hardening

**Status**: ✅ Implementation Complete (Ready for Deployment)  
**Date**: 2026-04-14  
**Owner**: Database Architecture Team

## Overview

M5 hardens the PostgreSQL database for clean run cataloging, A vs B comparison, and future representative run selection. New queryable scenario axes and architecture identity are added **additively** without breaking MATLAB or existing runs.

### What's New

✅ **Architecture Identity**: All runs now traceable to Architecture A or B  
✅ **Scenario Axes**: Queryable scenario dimensions (failure family, healing, load, scale, seed)  
✅ **Topology Lineage**: Deterministic topology identification for A/B pairing  
✅ **Run Completeness**: Import status tracking (complete/partial/invalid)  
✅ **Backward Compatible**: All existing MATLAB queries continue working unchanged  
✅ **Minimal Schema**: Only additive columns; no renames or deletions  

## Files Delivered

### Schema
- **`sql/m5_schema_extension.sql`** — Adds 12 new columns, 4 indexes, 2 reference tables (idempotent, safe to re-run)
- **`sql/m5_matlab_compatibility_views.sql`** — 6 views for backward compatibility and new queryability

### Importer
- **`importer/import_run_to_postgres.py`** — Updated `insert_run()` to extract and populate M4 metadata (architecture, routing_engine, scenario axes, topology fields)

### Documentation
- **`docs/M5_DB_HARDENING_PLAN.md`** — Design philosophy and change strategy
- **`docs/M5_SCHEMA_CONTRACT.md`** — Formal schema contract (frozen until M6)
- **`docs/M5_OPERATOR_GUIDE.md`** — Deployment and operations procedures
- **`docs/M5_IMPLEMENTATION_PLAYBOOK.md`** — Step-by-step implementation guide
- **`sql/m5_verify_queryability.sql`** — Comprehensive verification queries

## Key Features

### 1️⃣ Architecture Identity

New `architecture` column on `runs` table:
- Values: 'A' (baseline) or 'B' (BSBSSP-enabled)
- Default: 'A' (backward compatible)
- Usage: `SELECT * FROM runs WHERE architecture = 'B'`

### 2️⃣ Scenario Axes (Now Queryable)

New columns on `runs` table:
- `failure_family` (F0-F4)
- `healing_id` (H0-H4)
- `variant` (V1-V3)
- `load` (L1-L3)
- `scale` (S1-S6)
- `seed` (random seed for determinism anchor)

Populate from `run_meta.json` during import. Support filtering and grouping.

Example queries:
```sql
-- Filter by failure family and healing scenario
SELECT * FROM runs WHERE failure_family = 'F1' AND healing_id = 'H1';

-- Find runs with identical topology
SELECT * FROM runs WHERE map_signature = '<hash>' ORDER BY architecture;

-- Group by scenario axes
SELECT failure_family, COUNT(*) FROM runs GROUP BY failure_family;
```

### 3️⃣ Topology Lineage

New columns:
- `map_id` — topology map package identifier
- `map_signature` — SHA256 deterministic hash
- Same seed+scale always → same map_signature
- Enables confident A/B pairing

Queryable via view:
```sql
SELECT * FROM runs_topology_lineage;
-- Shows each unique topology and all its runs
```

### 4️⃣ Run Status Tracking

New `run_status` column:
- `complete` — all 7 export files successfully imported
- `partial` — subset of files present (QA/test runs)
- `incomplete` — import in progress or failed
- `invalid` — import validation failure

Filter reliable runs: `WHERE run_status = 'complete'`

### 5️⃣ MATLAB Backward Compatibility

Three options for existing MATLAB queries:

**Option A: Do Nothing** (recommended short-term)
```matlab
% Existing query continues to work unchanged
runs = query('SELECT run_id, scenario_name, ... FROM runs ORDER BY started_at DESC');
```

**Option B: Add Architecture Filtering** (recommended long-term)
```matlab
% Filter to B architecture runs for BSBSSP testing
runs_B = query('SELECT * FROM runs WHERE architecture = ''B''');
```

**Option C: Use Compatibility View** (future-proof)
```matlab
% Queries continue to work even if runs table schema changes in M6+
runs = query('SELECT * FROM runs_matlab_compat ORDER BY started_at DESC');
```

All views preserve exact column shape and semantics.

### 6️⃣ New Queryability (Examples)

```sql
-- A vs B comparison (same scenario, different architecture)
SELECT r_a.run_id as run_A, r_b.run_id as run_B,
       r_a.failure_family, r_a.healing_id, r_a.load, r_a.scale
FROM runs r_a
JOIN runs r_b ON r_a.failure_family = r_b.failure_family 
  AND r_a.healing_id = r_b.healing_id
  AND r_a.load = r_b.load AND r_a.scale = r_b.scale
  AND r_a.seed = r_b.seed
WHERE r_a.architecture = 'A' AND r_b.architecture = 'B'
  AND r_a.run_status = 'complete' AND r_b.run_status = 'complete';

-- Import status summary
SELECT * FROM runs_completeness_summary;

-- Scenario coverage
SELECT * FROM runs_scenario_axes;

-- Topology variants
SELECT * FROM runs_topology_lineage;
```

## Schema Changes Summary

### `runs` Table

**Added Columns** (all nullable + safe defaults, except architecture/routing_engine which default to A/baseline):

| Column | Type | Purpose | Extract From |
|--------|------|---------|--------------|
| architecture | CHAR | A or B | run_meta.json |
| routing_engine | TEXT | baseline or bsbssp_v1_approx | run_meta.json |
| failure_family | TEXT | F0-F4 scenario | run_meta.json |
| healing_id | TEXT | H0-H4 healing variant | run_meta.json |
| variant | TEXT | V1-V3 scenario variant | run_meta.json |
| load | TEXT | L1-L3 traffic load | run_meta.json |
| scale | TEXT | S1-S6 network scale | run_meta.json |
| seed | INT | Random seed | run_meta.json |
| map_id | TEXT | Topology package ID | run_meta.json |
| map_signature | TEXT | SHA256 topology hash | run_meta.json |
| run_status | TEXT | Import status | importer validation |
| external_run_id_new | TEXT | Stable external ID | run_meta.json (optional) |

**Preserved Columns** (unchanged, all MATLAB queries still work):
- run_id, scenario_name, scenario_type, sim_time_s, node_count, cluster_count, traffic_interval_s, aggregation_interval_s, failure_time_s, recovery_delay_s, recovery_enabled, schema_version, experiment_version, notes, started_at

**New Indexes**:
- idx_runs_architecture
- idx_runs_routing_engine
- idx_runs_failure_family
- idx_runs_architecture_status

### Reference Tables

**scenario_axes_enum**: Frozen vocabulary
- 22 rows defining allowed values for each axis (F0-F4, H0-H4, V1-V3, L1-L3, S1-S6)

**event_code_reference**: Event taxonomy
- 12 rows defining event types and their classes

### Views

| View | Purpose | Columns |
|------|---------|---------|
| runs_matlab_compat | MATLAB backward compatibility | Same 11 cols as old runs table |
| runs_extended | Full M5 schema | All runs cols including new ones |
| runs_by_architecture | Architecture summary | architecture, routing_engine, run_count, earliest, latest |
| runs_scenario_axes | Scenario coverage | All axes + run_count + timespan |
| runs_topology_lineage | Topology pairing | map_id, map_signature, architectures, run_count |
| runs_completeness_summary | Import status | run_status, count, percentage |

## Deployment Steps

### Quick Deploy (5-minute window)

1. **Backup current DB** (recommended)
   ```bash
   pg_dump $PGDATABASE > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Apply schema extension**
   ```bash
   psql -h $PGHOST -U $PGUSER -d $PGDATABASE \
     -f sql/m5_schema_extension.sql --set PGSCHEMA=wsn
   ```

3. **Apply compatibility views**
   ```bash
   psql -h $PGHOST -U $PGUSER -d $PGDATABASE \
     -f sql/m5_matlab_compatibility_views.sql --set PGSCHEMA=wsn
   ```

4. **Deploy updated importer code**
   ```bash
   cp importer/import_run_to_postgres.py importer/import_run_to_postgres.py.bak
   # Deploy new version
   ```

5. **Re-import M4 runs** (if already imported with old importer)
   ```bash
   for run_dir in export/*/; do
     python3 importer/import_run_to_postgres.py \
       --run-dir "$run_dir" --env-file config/.env --mode replace
   done
   ```

6. **Verify with `sql/m5_verify_queryability.sql`**
   ```bash
   psql -h $PGHOST -U $PGUSER -d $PGDATABASE \
     -f sql/m5_verify_queryability.sql
   ```

### Full Deployment Guide

See **`docs/M5_IMPLEMENTATION_PLAYBOOK.md`** for step-by-step instructions with verification at each step.

## Backward Compatibility

✅ **All existing MATLAB queries continue to work**  
✅ **Old export packages (pre-M4) still import successfully**  
✅ **No columns renamed or deleted**  
✅ **New columns have safe defaults (NULL or A/baseline)**  
✅ **Idempotent schema migration (safe to re-run)**  

## Operational Readiness

### Documentation
- ✅ Schema contract (frozen, binding on all tools)
- ✅ Operator guide (deployment, troubleshooting)
- ✅ Implementation playbook (step-by-step with timeline estimates)
- ✅ Queryability verification (comprehensive test suite)

### Code Changes
- ✅ Importer updated to extract M4 metadata
- ✅ Schema DDL written and idempotent
- ✅ Views created for MATLAB compatibility

### Testing
- ✅ Dry-run validation ready
- ✅ Verification queries ready
- ✅ Rollback procedure documented

## Known Limitations / Future Work (M6+)

- Scenario axes are string enums (not yet foreign keys; can add validation trigger in M6)
- Event codes are reference-only (not yet enforced in events table; can add FK constraint in M6)
- No batch/windowing table yet (planned for feature selection in M6)
- No event class categorical query optimization (can add in M6)

## Files Summary

```
docs/
  M5_DB_HARDENING_PLAN.md           - Design philosophy
  M5_SCHEMA_CONTRACT.md              - Formal contract (frozen)
  M5_OPERATOR_GUIDE.md               - Deployment & operations
  M5_IMPLEMENTATION_PLAYBOOK.md      - Step-by-step guide (THIS SECTION)
  M4_EVENT_AND_METADATA_COMPATIBILITY.md - Updated
sql/
  m5_schema_extension.sql            - New columns, indexes, reference tables
  m5_matlab_compatibility_views.sql  - 6 views for compatibility + queryability
  m5_verify_queryability.sql         - Comprehensive verification suite
importer/
  import_run_to_postgres.py          - Updated insert_run() function
```

## Success Metrics

Post-deployment, verify:
- ✅ MATLAB queries execute without error (backward compatibility)
- ✅ All M4 runs show architecture B (architecture identity)
- ✅ All M4 runs show scenario axes populated (axes queryability)
- ✅ runs_by_architecture shows 2+ groups (A/B isolation)
- ✅ runs_scenario_axes shows full axis matrix (coverage)
- ✅ runs_topology_lineage shows paired variants (A/B pairing)
- ✅ All verification queries take <1s (performance)

## Support

**Questions about M5 DB changes?** See the appropriate doc:
- *What changed?* → `M5_DB_HARDENING_PLAN.md`
- *How do I deploy?* → `M5_IMPLEMENTATION_PLAYBOOK.md`
- *What's guaranteed?* → `M5_SCHEMA_CONTRACT.md`
- *How do I operate it?* → `M5_OPERATOR_GUIDE.md`
- *Does my query work?* → `sql/m5_verify_queryability.sql`

---

**M5 Status**: ✅ Ready for deployment  
**Deployment Window**: 5-60 minutes (including M4 re-import)  
**Risk Level**: Low (additive-only, idempotent, backward compatible)  
**Rollback Time**: <5 minutes (if needed)
