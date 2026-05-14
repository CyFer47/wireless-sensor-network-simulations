# Phase2A Patch and Failed-Only Rerun Report

**Date**: 2026-05-13  
**Scope**: Patch the missing scale rules and rerun only the 96 previously failed Phase2A specs.

## Root Cause

Phase2A failures were caused by missing `kScaleRules` entries in `ns3/test-ns3/m3-scenario-library.cc`. The batch used `S12` for 500-node runs and `S13` for 1000-node runs, but the simulator only defined `S1` through `S7`. The code path `kScaleRules.at(gState.scale)` threw `std::out_of_range`, which surfaced as exit code 250.

## Patch Applied

Added the canonical scale rules to `kScaleRules`:

```cpp
{"S12", {500, 20, 1, 320.0, 320.0}},
{"S13", {1000, 40, 2, 480.0, 480.0}},
```

No other simulation logic was changed.

## Smoke Test Result

The smallest failing scenario, `S500_B_L1_F0_H0_seed01`, was run first after the rebuild. It completed successfully, with no `std::out_of_range` and no exit code 250.

## Failed-Only Rerun Result

All 96 previously failed Phase2A specs were rerun. Every one completed successfully and imported normally.

- Attempted: 96
- Successful: 96
- Failed: 0
- Exit code 250 remaining: 0

## Database Import Summary

Successful rerun results were imported into PostgreSQL using the existing replace-mode importer for each run. No old rows were deleted or edited.

## Updated Export Summary

New output folder:

`/home/cyfer/FYP/outputs/phase2A_energy_dataset_after_patch`

Created files:

- `phase2A_run_summary.csv`
- `phase2A_energy_summary.csv`
- `phase2A_event_summary.csv`
- `phase2A_healing_comparison.csv`
- `phase2A_scale_comparison.csv`
- `phase2A_h0_vs_h1_h3_h4.csv`
- `phase2A_failed_runs.csv` with zero rows
- `phase2A_dashboard_run_index.csv`
- `phase2A_agent1_execution_report.txt`

## MATLAB Validation Readiness

Agent2 MATLAB validation can proceed. The simulator patch is in place, the smoke test passed, and the failed-only rerun completed cleanly.
