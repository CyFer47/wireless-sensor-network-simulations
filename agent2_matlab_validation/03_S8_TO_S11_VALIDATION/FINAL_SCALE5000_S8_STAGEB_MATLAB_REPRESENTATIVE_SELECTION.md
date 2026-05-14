# FINAL_SCALE5000 S8 Stage B MATLAB Representative Selection

Date: 2026-05-01

## Deterministic selection rule (required)

For each Stage B scenario key, select the **latest complete run_id**.

Scenario key:

- `scale`
- `architecture`
- `failure_family`
- `healing_id`
- `load`
- `seed`

SQL concept:

`ROW_NUMBER() OVER (PARTITION BY scale, architecture, failure_family, healing_id, load, seed ORDER BY run_id DESC) = 1`

Rationale:

- Stage B had recovery/re-import events in early sequence history.
- Fixed run-id references are fragile for Stage B/C continuity.
- Latest-complete-per-key is deterministic and robust to re-imported rows.

## Stage B representative runs used in MATLAB QA

- Family `F1/H1`: run_id **974** (`B`,`L2`,`seed02`)
- Family `F2/H2`: run_id **982** (`B`,`L2`,`seed02`)
- Family `F3/H3`: run_id **990** (`B`,`L2`,`seed02`)
- Family `F4/H4`: run_id **994** (`B`,`L2`,`seed02`)

## Continuity caveat disposition

- Re-import focus ids `969/970/971` were verified in MATLAB and mapped to:
  - `969`: `A F1/H1 L1 seed01`
  - `970`: `A F1/H1 L2 seed01`
  - `971`: `B F1/H1 L1 seed01`
- Duplicate-key scan in complete S8 Stage B family space returned none.
- Caveat outcome for MATLAB representative selection: **accepted**, with the deterministic rule above enforced.
