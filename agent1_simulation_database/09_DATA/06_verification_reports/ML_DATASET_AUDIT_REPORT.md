# ML Dataset Audit Report

- Workspace: /home/cyfer/FYP/WSN_simulation
- Database: wsn_sim / schema wsn
- Backup used for freeze: /home/cyfer/FYP/archive/db_backups/wsn_sim_before_ml_dataset_export.sql

## Selection rule

Latest-complete rows were selected with deterministic key partitioning on scale + architecture + failure_family + healing_id + load + seed, ordered by run_id descending.

## Row counts

- Complete rows in runs table: 1152
- Valid complete rows with all key fields present: 1150
- Latest-complete selected rows: 1148
- Duplicate scenario keys before selection: 2
- Duplicate scenario keys after selection: 0
- Missing key-field rows: [{'run_id': 3, 'scenario_name': 'cluster-dashboard-m1', 'scenario_type': 'wsn-self-healing', 'scale': None, 'architecture': 'A', 'failure_family': None, 'healing_id': None, 'variant': None, 'load': None, 'seed': None, 'map_id': None, 'map_signature': None, 'run_status': 'complete'}, {'run_id': 4, 'scenario_name': 'cluster-dashboard-m1', 'scenario_type': 'wsn-self-healing', 'scale': None, 'architecture': 'A', 'failure_family': None, 'healing_id': None, 'variant': None, 'load': None, 'seed': None, 'map_id': None, 'map_signature': None, 'run_status': 'complete'}]

## Counts by scale

| scale | count |
| --- | --- |
| S1 | 144 |
| S10 | 68 |
| S11 | 68 |
| S2 | 144 |
| S3 | 144 |
| S4 | 144 |
| S5 | 144 |
| S6 | 144 |
| S7 | 12 |
| S8 | 68 |
| S9 | 68 |

## Counts by node_count

| node_count | count |
| --- | --- |
| 100 | 144 |
| 1600 | 144 |
| 200 | 144 |
| 3000 | 12 |
| 3500 | 68 |
| 400 | 144 |
| 4000 | 68 |
| 4500 | 68 |
| 50 | 144 |
| 5000 | 68 |
| 800 | 144 |

## Counts by seed

| seed | count |
| --- | --- |
| 1 | 372 |
| 2 | 344 |
| 3 | 216 |
| 4 | 216 |

## Counts by architecture

| architecture | count |
| --- | --- |
| A | 574 |
| B | 574 |

## Counts by failure_family

| failure_family | count |
| --- | --- |
| F0 | 116 |
| F1 | 260 |
| F2 | 256 |
| F3 | 256 |
| F4 | 260 |

## Counts by healing_id

| healing_id | count |
| --- | --- |
| H0 | 628 |
| H1 | 132 |
| H2 | 128 |
| H3 | 128 |
| H4 | 132 |

## Counts by load

| load | count |
| --- | --- |
| L1 | 574 |
| L2 | 574 |

## Counts by run_status

| run_status | count |
| --- | --- |
| complete | 1148 |

## Duplicate keys before latest-complete selection

| scale | architecture | failure_family | healing_id | load | seed | count | min_run_id | max_run_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | A | F0 | H0 | L1 | 1 | 2 | 73 | 1264 |
| S1 | A | F1 | H1 | L1 | 1 | 2 | 170 | 1265 |

## Missing key fields

| run_id | scenario_name | scenario_type | scale | architecture | failure_family | healing_id | variant | load | seed | map_id | map_signature | run_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | cluster-dashboard-m1 | wsn-self-healing |  | A |  |  |  |  |  |  |  | complete |
| 4 | cluster-dashboard-m1 | wsn-self-healing |  | A |  |  |  |  |  |  |  | complete |

## Event marker availability

| marker | selected rows with marker |
| --- | --- |
| failure_injection_s present | 1032 |
| recovery_start_s present | 0 |
| recovery_applied_s present | 520 |
| first_aggregate_s present | 1148 |
| first_recovered_aggregate_s present | 520 |

## Event marker notes

- Observed event classes include FAILURE, RECOVERY, AGGREGATE, INIT, ROUTE_COMPUTE, RELAY, DEGRADE, RELAY_OVERLOAD, OVERFLOW, RAW, AGG, REC, and FAIL.
- Recovery timing fields were derived from event messages and earliest matching event times where available.
