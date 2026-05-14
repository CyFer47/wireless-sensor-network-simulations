# FINAL_SCALE5000 S10 MATLAB Representative Selection

Selection policy used:

- For each scenario key (`scale + architecture + failure_family + healing_id + load + seed`), select latest complete `run_id`.

Stage A representative runs (requested readability set):

- F0_H0_A_S10_L1_seed01 => run_id 1096
- F1_H1_A_S10_L1_seed01 => run_id 1100
- F1_H1_B_S10_L1_seed01 => run_id 1102
- F4_H4_B_S10_L2_seed01 => run_id 1107

Stage B representative runs (one per family):

- F1_H1 => run_id 1100
- F2_H2 => run_id 1112
- F3_H3 => run_id 1120
- F4_H4 => run_id 1104

Stage C representative matched pairs (one per family):

- F1_H0_A_S10_L1_seed01 vs F1_H1_A_S10_L1_seed01 => run_id 1132 vs 1100
- F2_H0_A_S10_L1_seed01 vs F2_H2_A_S10_L1_seed01 => run_id 1172 vs 1112
- F3_H0_A_S10_L1_seed01 vs F3_H3_A_S10_L1_seed01 => run_id 1180 vs 1120
- F4_H0_B_S10_L2_seed02 vs F4_H4_B_S10_L2_seed02 => run_id 1195 vs 1131
