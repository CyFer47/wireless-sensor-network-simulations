# Final Scale5000 S8 Stage B: Query Proof

## Query Scope

Validation scope is restricted to Stage B target families at scale S8:

- `scale = 'S8'`
- `failure_family IN ('F1','F2','F3','F4')`
- `healing_id IN ('H1','H2','H3','H4')`
- `run_status = 'complete'`

## Top-Level Proof

SQL result:

- `total_s8_rows = 36`
- `stageb_family_rows = 32`
- `stageb_complete_rows = 32`
- `newest_run_id = 994`

Interpretation:

- All 32 Stage B-target rows exist and are complete.
- S8 now includes baseline Stage A rows plus Stage B matrix rows.

## Balance Proof

### Architecture

- A: 16
- B: 16

### Load

- L1: 16
- L2: 16

### Seed

- seed01: 16
- seed02: 16

## Family Visibility Proof

- F1/H1: 8
- F2/H2: 8
- F3/H3: 8
- F4/H4: 8

All required failure/healing families are fully visible.

## Map Lineage Proof

Query result:

- `missing_map_lineage = 0`

Meaning all Stage B complete rows have both:

- `map_id`
- `map_signature`

Recent rows include:

- `run_id=994` `F4_H4_B_S8_L2_seed02` `map_id=map_S8_seed02`
- `run_id=993` `F4_H4_B_S8_L1_seed02` `map_id=map_S8_seed02`
- `run_id=992` `F4_H4_A_S8_L2_seed02` `map_id=map_S8_seed02`
- `run_id=989` `F3_H3_B_S8_L2_seed01` `map_id=map_S8_seed01`

## Stage B Execution Delta

From state tracking:

- total state entries: 32
- status ok: 32
- status failed: 0
- reused complete rows: 9
- executed new rows: 23
- quarantined rows: 0

## S1-S7 Integrity Snapshot

Scale counts observed post-run:

- S1: 144
- S2: 144
- S3: 144
- S4: 144
- S5: 144
- S6: 144
- S7: 12
- S8: 36

No evidence of S1-S7 regression in aggregate scale counts.

## API Visibility Proof

Endpoints checked:

1. `/api/health` -> status `ok`, database `connected`
2. `/api/debug/db-check` -> tcp/auth/schema/table checks pass
3. `/api/runs?page=1&size=12&sort=run_id&order=desc` -> latest S8 Stage B rows visible (`run_id` 994, 993, 992, ...)

Conclusion: dashboard/API visibility is **PASS** for Stage B rows.
