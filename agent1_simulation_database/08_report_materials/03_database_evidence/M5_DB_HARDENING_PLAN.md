# M5 DB Hardening Plan

Date: 2026-04-14
Status: Foundation for M5

## Purpose

Make the PostgreSQL database a stable source of truth for:

- run provenance and scenario axes (failure, healing, variant, load, scale)
- architecture identity and routing engine selection
- topology lineage and map versioning
- run completeness/status signaling
- event typing and structured event metadata
- later representative run selection and ML feature windows

Current state:
- M1 schema is usable but lacks structured scenario metadata
- M3/M4 exports now include rich scenario fields in `run_meta.json`
- Importer reads these fields but doesn't store them in DB
- MATLAB queries work against existing tables but cannot filter by architecture/scenario axes
- No explicit run-status tracking

## Current Schema Strengths

- Solid core layout: `runs`, 7 dependent tables with proper FKs
- Time-indexed timeseries tables
- Event logging with JSON details column
- Working indexes on common queries
- YAML/SQL schemas documented
- Importer validated and backward-compatible

## Current Schema Gaps

Are in the `runs` table:
- No `architecture` field → cannot distinguish A vs B at query time
- No scenario axes: `failure_family`, `healing_id`, `variant`, `load`, `scale` → cannot filter/group by these
- No `seed` or topology lineage fields → cannot match/compare identical-topology runs
- No `map_id`/`map_signature` for topology accountability
- No `routing_engine` field for BSBSSP approximation tracking
- Missing `run_status` or `completeness` signal
- No explicit external-ID tracking beyond `experiment_version`

In the `events` table:
- `event_type` is text-only, no structured enum
- No event-class taxonomy
- No event-code reference lookups

## Minimal Change Strategy

**Additive approach**: Do not remove or rename existing columns.

1. Add new columns to `runs`:
   - `architecture` (char) — A or B, default A
   - `failure_family` (text) — F0..F4
   - `healing_id` (text) — H0..H4
   - `variant` (text) — V1..V3
   - `load` (text) — L1..L2
   - `scale` (text) — S1..S6
   - `seed` (int) — random seed determinism anchor
   - `map_id` (text) — topology map identifier
   - `map_signature` (text) — topology deterministic hash
   - `routing_engine` (text) — baseline or bsbssp_v1_approx
   - `run_status` (text) — uploaded, complete, partial, invalid
   - `external_run_id_new` (text) — stable external ID anchor (distinct from experiment_version)

2. Add reference/lookup tables (optional but useful):
   - `scenario_axes_enum` — frozen vocabulary for failure_family, healing_id, variant, load, scale
   - `run_catalog` — denormalized view for filtering/grouping

3. Add structured event handling (optional):
   - `event_code` (text) — stable event taxonomy
   - `events_reference` — lookup table for event codes

4. Backward-compatibility approach:
   - Keep all existing columns and data untouched
   - MATLAB queries continue working via compatibility views
   - Importer remains compatible with old exports

## What Will Be Added

- `sql/m5_schema_extension.sql`: migration with new columns
- `sql/m5_lookup_tables.sql`: scenario axes and event code references (optional)
- Updated importer logic to write new fields
- Compatibility views for existing MATLAB queries

## What Will Remain Compatible

- All existing table schemas unchanged (columns only added)
- All existing queries work as-is
- Existing export/import contract unchanged
- MATLAB/web-monitor code works without modification

## Migration Philosophy

1. Create migration file with `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
2. Migration is idempotent and safe to re-run
3. New columns default to NULL for pre-M4 runs
4. Importer detects new metadata fields and writes them if present
5. No data backfill required (M4+ runs will have rich metadata)

## Risks and Rollback

**Risk**: Schema migration fails on live DB
**Mitigation**: Test on copy first; migration is additive-only so partial failures are recoverable

**Risk**: Importer writes new fields to pre-M4 runs causing inconsistency
**Mitigation**: Importer explicitly checks for metadata presence before writing

**Risk**: MATLAB queries break
**Mitigation**: Use views to present old schema shape; no breaking changes to existing columns

**Rollback**: Simply omit the new columns from queries; old queries unaffected
