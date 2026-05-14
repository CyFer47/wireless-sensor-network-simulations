# Export Contract (Milestone 2)

This contract defines how one ns-3 run is exported to disk for DB ingestion.

## Per-run folder naming
- Pattern: `run_<external_run_id>`
- `external_run_id` is timestamp-based and unique for the run.

Example:
- `outputs/run_20260324_151530_123/`

## Required files
- `run_meta.json`
- `nodes_static.csv`
- `global_timeseries.csv`
- `cluster_timeseries.csv`
- `events.csv`
- `run_summary.json`
- `node_final_summary.csv`

## Time convention
- `sim_time`/`sim_time_s` values are simulation seconds from start.
- Numeric precision target: 3 decimals for time, 6 decimals for energy.

## Null/optional convention
- CSV nullable integer fields are blank (empty string).
- JSON optional fields may be absent or null.

## File -> table mapping
- `run_meta.json` -> `wsn.runs`
- `nodes_static.csv` -> `wsn.nodes_static`
- `global_timeseries.csv` -> `wsn.global_timeseries`
- `cluster_timeseries.csv` -> `wsn.cluster_timeseries`
- `events.csv` -> `wsn.events`
- `run_summary.json` -> `wsn.run_summary`
- `node_final_summary.csv` -> `wsn.node_final_summary`

## Required columns and types

### run_meta.json
- `external_run_id` (string, required)
- `schema_version` (string)
- `scenario_name` (string)
- `scenario_type` (string)
- `sim_time_s` (number)
- `node_count` (int)
- `cluster_count` (int)
- `traffic_interval_s` (number)
- `aggregation_interval_s` (number)
- `failure_time_s` (number, optional)
- `recovery_delay_s` (number, optional)
- `recovery_enabled` (bool)

### nodes_static.csv
- `external_run_id` string
- `node_id` int
- `role` text (`member|ch|bs`)
- `original_cluster_id` int nullable
- `original_ch_id` int nullable
- `initial_energy_j` numeric
- `x`,`y`,`z` numeric

### global_timeseries.csv
- `external_run_id` string
- `sim_time` numeric
- `raw_tx_cum`,`raw_rx_cum`,`agg_tx_cum`,`agg_rx_cum` bigint
- `direct_agg_rx_cum`,`relayed_agg_rx_cum`,`relay_fwd_cum` bigint
- `avg_res_j`,`min_res_j`,`consumed_j` numeric
- `low_nodes`,`failed_chs`,`recovered_clusters` int
- `pending_raw_total` bigint

### cluster_timeseries.csv
- `external_run_id` string
- `sim_time` numeric
- `cluster_id` int
- `original_ch_id`,`current_ch_id` int
- `status`,`mode`,`next_hop` text
- `members_count` int
- `raw_rx_cum`,`pending_raw`,`agg_tx_cum`,`relay_fwd_cum` bigint
- `ch_res_j`,`avg_mem_res_j`,`cluster_consumed_j` numeric

### events.csv
- `external_run_id` string
- `sim_time` numeric
- `event_type` text
- `severity` text
- `cluster_id` int nullable
- `node_id` int nullable
- `message` text
- `details_json` JSON text (object recommended)

### run_summary.json
- `external_run_id` string
- `final_sim_time` numeric
- final cumulative metrics aligned with `run_summary` table columns

### node_final_summary.csv
- `external_run_id` string
- `node_id` int
- `role` text
- `cluster_id` int nullable
- `residual_j`,`consumed_j` numeric
- `final_status` text

## Run ID strategy
- Export uses `external_run_id` string (timestamp-based).
- Importer inserts one row into `wsn.runs` and stores this in `runs.experiment_version`.
- DB-generated numeric `run_id` is used for FK rows in all other tables.
