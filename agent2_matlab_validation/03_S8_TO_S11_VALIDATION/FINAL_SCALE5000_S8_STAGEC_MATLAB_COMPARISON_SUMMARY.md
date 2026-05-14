# FINAL_SCALE5000 S8 Stage C — Comparison Summary

Date: 2026-05-01

Representative comparison metrics (control vs healing) — selected runs and compact metrics.

Selected run metrics (excerpt):

- run_id 995 (F1 H0 A L1 seed01): final_raw_rx=246752, final_agg_rx=7795, avg_res_j=1.8888, consumed_j=0.1079, low_nodes=20
- run_id 969 (F1 H1 A L1 seed01): final_raw_rx=248608, final_agg_rx=7839, avg_res_j=1.8879, consumed_j=0.1087, low_nodes=20

- run_id 1003 (F2 H0 A L1 seed01): final_raw_rx=248109, final_agg_rx=7795, avg_res_j=1.8887, consumed_j=0.1085, low_nodes=19
- run_id 975 (F2 H2 A L1 seed01): final_raw_rx=248631, final_agg_rx=7839, avg_res_j=1.8884, consumed_j=0.1088, low_nodes=19

- run_id 1011 (F3 H0 A L1 seed01): final_raw_rx=246634, final_agg_rx=7795, avg_res_j=1.8893, consumed_j=0.1079, low_nodes=19
- run_id 983 (F3 H3 A L1 seed01): final_raw_rx=246806, final_agg_rx=7839, avg_res_j=1.8892, consumed_j=0.1080, low_nodes=19

- run_id 1026 (F4 H0 B L2 seed02): final_raw_rx=246988, final_agg_rx=7795, avg_res_j=1.8551, consumed_j=0.1421, low_nodes=9
- run_id 994 (F4 H4 B L2 seed02): final_raw_rx=245852, final_agg_rx=7839, avg_res_j=1.8557, consumed_j=0.1415, low_nodes=9

Interpretation notes:

- Metrics shown are direct extracts: cumulative RX/TX from `global_timeseries`, and residual/consumed aggregates from `node_final_summary`.
- `low_nodes` is a simple count of nodes with residual_j < 0.1; `recovered_clusters` was not computed here (requires cluster-recovery logic).
- Differences between control and healing in these representative pairs are small for F1–F3; F4 shows increased consumed_j in control vs healing pair (proxy for healing activity), consistent with Stage B observations.

Limitations:

- These are representative single-pair snapshots, not full-run statistical aggregates.
- Do not interpret as final production conclusions without broader aggregation across repeats.
