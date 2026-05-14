# Dataset Dictionary

## ml_run_outcomes.csv

| column | meaning |
| --- | --- |
| run_id | Primary database run identifier. |
| experiment_version | Export version / external experiment identifier. |
| scale | WSN scale label (S1-S11). |
| node_count | Total node count for the run. |
| cluster_count | Cluster count used by the scenario. |
| architecture | Scenario architecture (A or B). |
| failure_family | Failure family label (F0-F4). |
| healing_id | Healing policy label (H0-H4). |
| variant | Scenario variant label (V1-V3). |
| load | Traffic load label (L1 or L2). |
| seed | Topology seed. |
| map_id | Topology package identifier. |
| map_signature | SHA256 signature of the topology package. |
| sim_time_s | Final simulation time in seconds. |
| run_status | Run completion status. |
| final_raw_tx | Final cumulative raw transmissions. |
| final_raw_rx | Final cumulative raw receptions. |
| final_raw_delivery_ratio | final_raw_rx / final_raw_tx when available. |
| final_agg_tx | Final cumulative aggregate transmissions. |
| final_agg_rx | Final cumulative aggregate receptions. |
| final_agg_delivery_ratio | final_agg_rx / final_agg_tx when available. |
| final_avg_res_j | Final average residual energy (J). |
| final_min_res_j | Final minimum residual energy (J). |
| final_consumed_j | Final consumed energy (J). |
| final_failed_chs | Final failed CH count. |
| final_recovered_clusters | Final recovered cluster count. |
| low_nodes | Final low-energy node count. |
| failure_injection_s | First failure marker time, if detected. |
| recovery_start_s | Recovery start marker time, if detected. |
| recovery_applied_s | Recovery applied marker time, if detected. |
| first_aggregate_s | First aggregate event time, if detected. |
| first_recovered_aggregate_s | First aggregate event at or after recovery application, if detected. |
| traffic_recovery_delay_s | First recovered aggregate minus failure injection time. |
| recovery_applied_delay_s | Recovery applied minus failure injection time. |
| split | Deterministic split label: train, validation, or test. |

## ml_healing_candidates.csv

| column | meaning |
| --- | --- |
| run_id | Primary database run identifier. |
| base_condition_key | Deterministic base condition key: scale|architecture|failure_family|load|seed|map_signature. |
| scale | WSN scale label. |
| architecture | Scenario architecture. |
| failure_family | Failure family label. |
| load | Traffic load label. |
| seed | Topology seed. |
| map_signature | Topology package signature. |
| candidate_healing_id | Healing candidate label. |
| final_raw_tx | Final cumulative raw transmissions. |
| final_raw_rx | Final cumulative raw receptions. |
| final_raw_delivery_ratio | final_raw_rx / final_raw_tx when available. |
| final_agg_tx | Final cumulative aggregate transmissions. |
| final_agg_rx | Final cumulative aggregate receptions. |
| final_agg_delivery_ratio | final_agg_rx / final_agg_tx when available. |
| final_avg_res_j | Final average residual energy (J). |
| final_min_res_j | Final minimum residual energy (J). |
| final_consumed_j | Final consumed energy (J). |
| final_failed_chs | Final failed CH count. |
| final_recovered_clusters | Final recovered cluster count. |
| low_nodes | Final low-energy node count. |
| traffic_recovery_delay_s | Derived traffic recovery delay when available. |
| score | Reserved for Phase 05 scoring; blank in this export. |
| is_best_candidate | Reserved for Phase 05 labeling; blank in this export. |
| split | Deterministic split label. |

## ml_best_healing_labels.csv

| column | meaning |
| --- | --- |
| base_condition_key | Deterministic base condition key. |
| scale | WSN scale label. |
| architecture | Scenario architecture. |
| failure_family | Failure family label. |
| load | Traffic load label. |
| seed | Topology seed. |
| map_signature | Topology package signature. |
| best_healing_id | Reserved for future best-label assignment; blank in this export. |
| split | Deterministic split label. |

## ml_recovery_time_regression.csv

| column | meaning |
| --- | --- |
| run_id | Primary database run identifier. |
| scale | WSN scale label. |
| architecture | Scenario architecture. |
| failure_family | Failure family label. |
| healing_id | Healing policy label. |
| load | Traffic load label. |
| seed | Topology seed. |
| map_signature | Topology package signature. |
| final_raw_tx | Final cumulative raw transmissions. |
| final_raw_rx | Final cumulative raw receptions. |
| final_raw_delivery_ratio | final_raw_rx / final_raw_tx when available. |
| final_agg_tx | Final cumulative aggregate transmissions. |
| final_agg_rx | Final cumulative aggregate receptions. |
| final_agg_delivery_ratio | final_agg_rx / final_agg_tx when available. |
| final_avg_res_j | Final average residual energy (J). |
| final_min_res_j | Final minimum residual energy (J). |
| final_consumed_j | Final consumed energy (J). |
| final_failed_chs | Final failed CH count. |
| final_recovered_clusters | Final recovered cluster count. |
| low_nodes | Final low-energy node count. |
| traffic_recovery_delay_s | Primary regression target where available. |
| recovery_applied_delay_s | Fallback target when recovered aggregate is not observed. |
| recovery_target_source | Which target source was used: first_recovered_aggregate, recovery_applied, or missing. |
| split | Deterministic split label. |

## dataset_split_manifest.csv

| column | meaning |
| --- | --- |
| run_id | Primary database run identifier. |
| scenario_key | Deterministic scenario key: scale|architecture|failure_family|healing_id|load|seed. |
| scale | WSN scale label. |
| seed | Topology seed. |
| map_signature | Topology package signature. |
| split | Deterministic split label. |
| split_reason | Human-readable reason for the split assignment. |
