# S7 Stage A Results

Date: 2026-04-22
Status: Completed

## Stage Scope

- Stage executed: `Stage A only`
- Stage B: not executed
- Stage C: not executed

## Top-Line Outcome

- planned runs: `12`
- launched runs: `12`
- completed runs: `12`
- imported runs: `12`
- failed runs: `0`
- partial runs: `0`
- quarantined runs: `0`

Result: all Stage A cells completed and imported cleanly.

## Breakdown

### By architecture

- A: `6`
- B: `6`

### By load

- L1: `6`
- L2: `6`

### By scenario group

- Group 1 baseline (`F0/H0`): `4`
- Group 2 healing pair (`F1/H1`): `4`
- Group 3 post-healing stress pair (`F4/H4`): `4`

## Import/Run Evidence

- Stage A state file: `outputs/s7_stagea_state.json`
- Stage A quarantine file: `outputs/s7_stagea_quarantine.json`
- Stage A batch log: `outputs/s7_stagea_batch.log`

Tail evidence from batch log confirms final runs imported successfully and batch ended cleanly.

## Last Run Markers

- last Stage A run label: `F4_H4_B_S7_L2_seed01`
- last state timestamp: `2026-04-22T10:35:42Z`
- latest S7 `run_id` observed: `948`

## MATLAB-Readiness Checks Required By Stage A

- baseline control run exists and exported: `F0_H0_A_S7_L1_seed01`
- matched A/B pair exists and exported:
  - `F1_H1_A_S7_L1_seed01`
  - `F1_H1_B_S7_L1_seed01`

Each checked run folder contains the full 7-file export package.

## Stage A Pass/Fail Decision

Stage A decision: `PASS`

Reason:

- 12/12 complete
- 12/12 import success
- 0 partial
- 0 quarantined
- S7 queryability and pairability verified

## Safety Recommendation

Based on Stage A only: safe to proceed to Stage B from a pipeline stability perspective.

(Proceed only if you explicitly approve Stage B execution.)
