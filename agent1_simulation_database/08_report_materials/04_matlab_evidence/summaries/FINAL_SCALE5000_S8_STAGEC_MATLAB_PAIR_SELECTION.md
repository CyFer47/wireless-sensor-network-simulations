# FINAL_SCALE5000 S8 Stage C — Representative Pair Selection

Date: 2026-05-01

Deterministic selection rule (applied):

- For each scenario key `(scale, architecture, failure_family, healing_id, load, seed)`, select the latest complete `run_id` (ORDER BY `run_id` DESC, pick `rn=1`).

Selected representative pairs (control vs healing) used in MATLAB QA:

- F1: `F1_H0_A_S8_L1_seed01` -> run_id **995**  vs `F1_H1_A_S8_L1_seed01` -> run_id **969**
- F2: `F2_H0_A_S8_L1_seed01` -> run_id **1003** vs `F2_H2_A_S8_L1_seed01` -> run_id **975**
- F3: `F3_H0_A_S8_L1_seed01` -> run_id **1011** vs `F3_H3_A_S8_L1_seed01` -> run_id **983**
- F4: `F4_H0_B_S8_L2_seed02` -> run_id **1026** vs `F4_H4_B_S8_L2_seed02` -> run_id **994**

All selected pairs have matching `architecture`, `load`, `seed`, `scale` and `map_id`/`map_signature` as reported in the verifier JSON.
