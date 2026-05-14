# S1_50_nodes

Scale node count: 50.

## Run categories
- baseline: F0_H0_A_<scale>_L1_seed01
- no_healing: F1_H0_A_<scale>_L1_seed01
- active_healing: F1_H1_A_<scale>_L1_seed01, F2_H2_A_<scale>_L1_seed01, F3_H3_A_<scale>_L1_seed01, F4_H4_B_<scale>_L2_seed01
- stress_healing: F4_H4_B_<scale>_L2_seed01
- ml_batch: reusable H0 vs active healing comparison specs

## Maps
- Present seeds: seed01, seed02
- If seed02 map is not currently present for a tier, generate it with tools/generate_map.py if needed.

## No-healing rule
- Use F1_H0_A_<scale>_L1_seed01 for the local no-healing V2 spec.
- That spec keeps failure_injection.enabled=true, recovery.enabled=false, and timing.recovery_delay_s=null.

## Notes
- expected_outputs stays inside this scale folder.
- simulations_50_to_5000 contains simple local run wrappers.
- local_outputs is the writable destination for local run results.
