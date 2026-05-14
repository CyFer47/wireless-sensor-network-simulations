# FINAL_SCALE5000 S10 MATLAB Review

Live MATLAB connection and review status:

- `test_db_connection()`: PASS (JDBC fallback succeeded)
- `s10_combined_matlab_review_agent2`: PASS
- `s10_combined_count_probe`: PASS

S10 visibility checks (latest complete run per deterministic scenario key):

- S10 rows visible in MATLAB: 68
- Final unique S10 scenario count: 68
- Stage A target rows visible: 12
- Stage B target rows visible: 32
- Stage C target rows visible: 64
- H0 control rows (Stage C): 32
- Active-healing rows (Stage C): 32
- Duplicate/re-import risk after latest-complete selection: not present

Scale-rule field checks:

- node_count values present: 4500
- cluster_count values present: 180
- map_id non-null rows: 0
- map_signature non-empty rows: 68
- run_status complete filter: applied for all counts

Stage A readability checks (requested runs, latest complete):

- F0_H0_A_S10_L1_seed01 => run_id 1096
- F1_H1_A_S10_L1_seed01 => run_id 1100
- F1_H1_B_S10_L1_seed01 => run_id 1102
- F4_H4_B_S10_L2_seed01 => run_id 1107

Stage A representative row counts:

| run_id | run_summary | global_timeseries | cluster_timeseries | events | node_final_summary |
|---:|---:|---:|---:|---:|---:|
| 1096 | 1 | 28 | 5040 | 1441 | 4506 |
| 1100 | 1 | 28 | 5040 | 790627 | 4506 |
| 1102 | 1 | 28 | 5040 | 790628 | 4506 |
| 1107 | 1 | 28 | 5040 | 13851 | 4506 |

Stage B readability checks:

- Family counts: F1/H1=8, F2/H2=8, F3/H3=8, F4/H4=8
- Architecture counts: A=16, B=16
- Load counts: L1=16, L2=16
- Seed counts: seed01=16, seed02=16

Stage C matched pairability: PASS

- Pairability basis: map_signature (map_id is null in this dataset)
- All 32 expected matched H0-vs-active pairs are valid

## Full Stage C Pairability Rows

| Family | Healing | Arch | Load | Seed | H0 run_id | Active run_id | Map basis | Pair OK |
|---|---|---|---|---:|---:|---:|---|---|
| F1 | H1 | A | L1 | 1 | 1132 | 1100 | map_signature | PASS |
| F1 | H1 | A | L1 | 2 | 1133 | 1108 | map_signature | PASS |
| F1 | H1 | A | L2 | 1 | 1134 | 1101 | map_signature | PASS |
| F1 | H1 | A | L2 | 2 | 1135 | 1109 | map_signature | PASS |
| F1 | H1 | B | L1 | 1 | 1136 | 1102 | map_signature | PASS |
| F1 | H1 | B | L1 | 2 | 1137 | 1110 | map_signature | PASS |
| F1 | H1 | B | L2 | 1 | 1138 | 1103 | map_signature | PASS |
| F1 | H1 | B | L2 | 2 | 1171 | 1111 | map_signature | PASS |
| F2 | H2 | A | L1 | 1 | 1172 | 1112 | map_signature | PASS |
| F2 | H2 | A | L1 | 2 | 1173 | 1113 | map_signature | PASS |
| F2 | H2 | A | L2 | 1 | 1174 | 1114 | map_signature | PASS |
| F2 | H2 | A | L2 | 2 | 1175 | 1115 | map_signature | PASS |
| F2 | H2 | B | L1 | 1 | 1176 | 1116 | map_signature | PASS |
| F2 | H2 | B | L1 | 2 | 1177 | 1117 | map_signature | PASS |
| F2 | H2 | B | L2 | 1 | 1178 | 1118 | map_signature | PASS |
| F2 | H2 | B | L2 | 2 | 1179 | 1119 | map_signature | PASS |
| F3 | H3 | A | L1 | 1 | 1180 | 1120 | map_signature | PASS |
| F3 | H3 | A | L1 | 2 | 1181 | 1121 | map_signature | PASS |
| F3 | H3 | A | L2 | 1 | 1182 | 1122 | map_signature | PASS |
| F3 | H3 | A | L2 | 2 | 1183 | 1123 | map_signature | PASS |
| F3 | H3 | B | L1 | 1 | 1184 | 1124 | map_signature | PASS |
| F3 | H3 | B | L1 | 2 | 1185 | 1125 | map_signature | PASS |
| F3 | H3 | B | L2 | 1 | 1186 | 1126 | map_signature | PASS |
| F3 | H3 | B | L2 | 2 | 1187 | 1127 | map_signature | PASS |
| F4 | H4 | A | L1 | 1 | 1188 | 1104 | map_signature | PASS |
| F4 | H4 | A | L1 | 2 | 1189 | 1128 | map_signature | PASS |
| F4 | H4 | A | L2 | 1 | 1190 | 1105 | map_signature | PASS |
| F4 | H4 | A | L2 | 2 | 1191 | 1129 | map_signature | PASS |
| F4 | H4 | B | L1 | 1 | 1192 | 1106 | map_signature | PASS |
| F4 | H4 | B | L1 | 2 | 1193 | 1130 | map_signature | PASS |
| F4 | H4 | B | L2 | 1 | 1194 | 1107 | map_signature | PASS |
| F4 | H4 | B | L2 | 2 | 1195 | 1131 | map_signature | PASS |
