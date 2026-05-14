# Final Scale5000 S8 Stage B: Results

## Final Outcome

S8 Stage B healing-family validation completed successfully at scale S8 (3500 nodes).

## Stage B Completion Summary

| Metric | Value |
|--------|-------|
| Stage B target unique rows | 32 |
| Stage B target complete rows | 32 |
| Existing complete rows reused | 9 |
| New rows executed in this Stage B pass | 23 |
| New rows completed | 23 |
| New rows imported | 23 |
| Failed runs | 0 |
| Partial runs | 0 |
| Quarantined runs | 0 |
| Total S8 rows after Stage B | 36 |
| Newest run_id | 994 |

## Why Reused = 9 (Not 8)

At Stage B launch, DB pre-check found 9 complete Stage B-target rows already present:

1. 8 expected overlap rows from Stage A (`F1_H1 seed01` + `F4_H4 seed01` across A/B and L1/L2)
2. 1 already-complete Stage B row (`F1_H1_B_S8_L1_seed02`)

The Stage B runner used DB-aware reuse and executed only the remaining 23 missing rows.

## Distribution Checks (Stage B target set only)

| Axis | Count |
|------|-------|
| Architecture A | 16 |
| Architecture B | 16 |
| Load L1 | 16 |
| Load L2 | 16 |
| seed01 | 16 |
| seed02 | 16 |
| F1/H1 | 8 |
| F2/H2 | 8 |
| F3/H3 | 8 |
| F4/H4 | 8 |

All distribution checks are balanced and match Stage B requirements.

## State/Resumability Artifacts

- `agent1_simulation_platform/outputs/s8_stageb_state.json`
  - 32 entries
  - 32 status=`ok`
  - 0 status=`failed`
- `agent1_simulation_platform/outputs/s8_stageb_quarantine.json`
  - empty list (`[]`)
- `agent1_simulation_platform/outputs/s8_stageb_batch.log`
  - Full execution trace

## S8 Totals After Stage B

- S8 total rows in DB: **36**
  - 4 baseline rows from Stage A (`F0_H0`)
  - 32 Stage B-target rows (`F1..F4/H1..H4`, A/B, L1/L2, seed01/seed02)

## Stage A Continuity Note

- Logical Stage A overlap rows remain present and complete in DB.
- During early Stage B recovery, three F1/H1 seed01 rows were re-imported and now carry newer run_ids:
  - `F1_H1_A_S8_L1_seed01` -> run_id 969
  - `F1_H1_A_S8_L2_seed01` -> run_id 970
  - `F1_H1_B_S8_L1_seed01` -> run_id 971
- `F1_H1_B_S8_L2_seed01` remains at run_id 958.

## Acceptance Result

S8 Stage B acceptance criteria are satisfied for the Stage B target matrix:

- 32 target rows exist and are complete
- all balance constraints pass
- no failed/partial/quarantined runs
- dashboard/API visibility passes

