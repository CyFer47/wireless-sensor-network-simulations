# Final Scale5000 — S8 Stage A Plan

## Objective
Execute the first real validation stage for the final 5000-node ladder, limited strictly to S8.

## Scope
- Scale: S8 only
- Seed: seed01 only
- Runs: 12 total
- No S9, S10, S11
- No Stage B
- No Stage C
- No full production extension

## S8 Rule
- nodes: 3500
- CH: 140
- BS: 5
- area: 950 x 950 m
- sim_time: 230 s
- seed: seed01 only

## Execution Model
For each run:
1. generate or confirm run-spec
2. validate run-spec
3. confirm map linkage
4. run simulation
5. export results
6. import into PostgreSQL
7. verify DB import
8. record success/failure in resumable state files

## State Tracking Files
- outputs/s8_stagea_state.json
- outputs/s8_stagea_quarantine.json
- outputs/s8_stagea_batch.log

## Acceptance Criteria
- planned runs = 12
- launched runs = 12
- completed runs = 12
- imported runs = 12
- failed runs = 0
- partial runs = 0
- quarantined runs = 0
- S8 DB queryability = pass
- dashboard/API visibility = pass
- at least one baseline control exists
- at least one matched A/B pair exists
- S1–S7 remain unaffected

## Notes
- Stage A only; no Stage B or Stage C execution.
- All changes remain additive and backward compatible.
