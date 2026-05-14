# FINAL_SCALE5000 S10 MATLAB Comparison Summary

| run_id | label | raw_tx | raw_rx | raw_delivery_pct | agg_tx | agg_rx | avg_res_j | min_res_j | consumed_j | failed_chs | recovered_clusters |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1132 | H0 | 1135125 | 1135125 | 100.000 | 1432 | 1432 | 1.718776 | 0.000000 | 1263.601700 | 1 | 0 |
| 1100 | ACTIVE | 1140228 | 1140228 | 100.000 | 1440 | 1440 | 1.717469 | 0.000000 | 1269.482500 | 0 | 1 |
| 1172 | H0 | 1132575 | 1132575 | 100.000 | 1432 | 1432 | 1.719643 | 0.000000 | 1261.606700 | 1 | 0 |
| 1112 | ACTIVE | 1140108 | 1140108 | 100.000 | 1440 | 1440 | 1.717890 | 0.000000 | 1269.493600 | 0 | 1 |
| 1180 | H0 | 1134615 | 1134615 | 100.000 | 1432 | 1432 | 1.719288 | 0.000000 | 1263.202700 | 1 | 0 |
| 1120 | ACTIVE | 1134647 | 1134647 | 100.000 | 1440 | 1440 | 1.719266 | 0.000000 | 1263.300900 | 0 | 1 |
| 1195 | H0 | 1136910 | 1136910 | 100.000 | 1432 | 1432 | 1.597624 | 0.000000 | 1810.689800 | 1 | 0 |
| 1131 | ACTIVE | 1131983 | 1131983 | 100.000 | 1440 | 1440 | 1.599365 | 0.000000 | 1802.859740 | 0 | 1 |

Event-marker delay values are treated as proxy timing derived from event logs (not packet latency).

Event marker check summary (F4 representative pair):

- H0 run_id 1195 markers: failure_injection=10s, recovery_start=NA, recovery_applied=NA, first_aggregate=30s, first_recovered_agg=NA, first_recovered_raw=NA
- ACTIVE run_id 1131 markers: failure_injection=10s, recovery_start=22s, recovery_applied=22s, first_aggregate=30s, first_recovered_agg=30s, first_recovered_raw=NA

Interpretation:

- H0 recovery markers being NA is expected because recovery is disabled in control runs.
- ACTIVE runs show recovery start/applied markers and recovered aggregate marker, so event marker usability is PASS.

Data-size summary for representative comparisons:

- run_summary rows: 1 per run
- global_timeseries rows: 28 per run
- cluster_timeseries rows: 5040 per run
- node_final_summary rows: 4506 per run
- events rows: scenario dependent (1435 to 790627 in selected representatives)

Comparison result:

- H0 vs ACTIVE comparisons are report-usable for all F1-F4 representative pairs.
- `recovered_clusters` is consistently 0 for H0 and 1 for ACTIVE in representative set.
