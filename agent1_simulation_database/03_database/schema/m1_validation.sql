-- Milestone 1 schema validation for PostgreSQL (psql)
-- Usage:
--   psql -h localhost -p 5432 -U postgres -d wsn_sim -f m1_validation.sql

\set ON_ERROR_STOP on

BEGIN;
SET search_path TO wsn, public;

-- 1) Insert one run and capture run_id
INSERT INTO runs (
    scenario_name,
    scenario_type,
    sim_time_s,
    node_count,
    cluster_count,
    traffic_interval_s,
    aggregation_interval_s,
    failure_time_s,
    recovery_delay_s,
    recovery_enabled,
    schema_version,
    experiment_version,
    notes
) VALUES (
    'cluster-dashboard-m1',
    'wsn-self-healing',
    30.0,
    19,
    3,
    3.0,
    6.0,
    13.0,
    1.0,
    true,
    'm1_v1',
    'exp_seed_1',
    'Milestone 1 validation row'
)
RETURNING run_id \gset

-- 2) Insert a few static nodes (CH, member, BS)
INSERT INTO nodes_static (run_id, node_id, role, original_cluster_id, original_ch_id, initial_energy_j, x, y, z)
VALUES
    ( :run_id, 0,  'ch',     0, 0,  2.0, 18.0, 18.0, 0.0),
    ( :run_id, 1,  'member', 0, 0,  2.0, 14.0, 21.0, 0.0),
    ( :run_id, 6,  'ch',     1, 6,  2.0, 80.0, 20.0, 0.0),
    ( :run_id, 12, 'ch',     2, 12, 2.0, 50.0, 72.0, 0.0),
    ( :run_id, 18, 'bs',     NULL, NULL, 0.0, 50.0, 50.0, 0.0);

-- 3) Insert global snapshot rows
INSERT INTO global_timeseries (
    run_id, sim_time_s,
    raw_tx_cum, raw_rx_cum, agg_tx_cum, agg_rx_cum,
    direct_agg_rx_cum, relayed_agg_rx_cum, relay_fwd_cum,
    avg_res_j, min_res_j, consumed_j,
    low_nodes, failed_chs, recovered_clusters, pending_raw_total
) VALUES
    ( :run_id,  0.0, 0, 0, 0, 0, 0, 0, 0, 2.000000, 2.000000, 0.000000, 0, 0, 0, 0),
    ( :run_id, 10.0, 16, 16, 3, 3, 2, 1, 1, 1.998000, 1.993000, 0.033000, 0, 1, 1, 1);

-- 4) Insert cluster snapshot rows
INSERT INTO cluster_timeseries (
    run_id, sim_time_s, cluster_id,
    original_ch_id, current_ch_id, status, mode, next_hop,
    members_count, raw_rx_cum, pending_raw, agg_tx_cum, relay_fwd_cum,
    ch_res_j, avg_mem_res_j, cluster_consumed_j
) VALUES
    ( :run_id, 10.0, 0, 0, 0, 'normal',    'direct', 'BS(18)',   5, 6, 1, 1, 0, 1.995000, 1.999000, 0.011000),
    ( :run_id, 10.0, 1, 6, 6, 'normal',    'direct', 'BS(18)',   5, 5, 0, 1, 1, 1.993000, 1.999000, 0.012000),
    ( :run_id, 10.0, 2, 12,6, 'recovered', 'direct', 'BS(18)',   5, 5, 0, 1, 0, 1.993000, 1.999000, 0.010000);

-- 5) Insert events
INSERT INTO events (run_id, sim_time_s, event_type, severity, cluster_id, node_id, message, details)
VALUES
    ( :run_id, 7.0, 'FAIL',  'WARN', 2, 12, 'CH12 failure injected', '{"source":"validation"}'),
    ( :run_id, 8.0, 'REC',   'INFO', 2,  6, 'Recovery trigger for cluster 2', '{"delay_s":1.0}'),
    ( :run_id, 8.4, 'REC',   'INFO', 2,  6, 'Recovery applied: members reattached to CH6', '{"active_ch":6}');

-- 6) Insert final run summary
INSERT INTO run_summary (
    run_id, final_sim_time_s,
    raw_tx_cum, raw_rx_cum, agg_tx_cum, agg_rx_cum,
    direct_agg_rx_cum, relayed_agg_rx_cum, relay_fwd_cum,
    failed_chs, recovered_clusters,
    avg_res_j, min_res_j, consumed_j,
    low_nodes, pending_raw_total
) VALUES (
    :run_id, 30.0,
    16, 16, 3, 3,
    2, 1, 1,
    1, 1,
    1.998000, 1.993000, 0.033000,
    0, 1
);

-- 7) Insert final node summary rows
INSERT INTO node_final_summary (run_id, node_id, role, cluster_id, residual_j, consumed_j, final_status)
VALUES
    ( :run_id, 0,  'ch',     0,    1.995000, 0.005000, 'normal' ),
    ( :run_id, 1,  'member', 0,    1.998000, 0.002000, 'normal' ),
    ( :run_id, 6,  'ch',     1,    1.993000, 0.007000, 'normal' ),
    ( :run_id, 12, 'ch',     2,    1.995000, 0.005000, 'failed' ),
    ( :run_id, 18, 'bs',     NULL, 0.000000, 0.000000, 'n/a'    );

-- Validation checks
DO $$
DECLARE
    c_runs INTEGER;
    c_global INTEGER;
    c_cluster INTEGER;
    c_events INTEGER;
    c_summary INTEGER;
BEGIN
    SELECT COUNT(*) INTO c_runs FROM runs WHERE run_id = :run_id;
    SELECT COUNT(*) INTO c_global FROM global_timeseries WHERE run_id = :run_id;
    SELECT COUNT(*) INTO c_cluster FROM cluster_timeseries WHERE run_id = :run_id;
    SELECT COUNT(*) INTO c_events FROM events WHERE run_id = :run_id;
    SELECT COUNT(*) INTO c_summary FROM run_summary WHERE run_id = :run_id;

    IF c_runs <> 1 OR c_global < 1 OR c_cluster < 1 OR c_events < 1 OR c_summary <> 1 THEN
        RAISE EXCEPTION 'Validation failed. runs=%, global=%, cluster=%, events=%, run_summary=%',
            c_runs, c_global, c_cluster, c_events, c_summary;
    END IF;
END $$;

-- Readable output
SELECT 'run_id' AS key, :run_id::TEXT AS value
UNION ALL
SELECT 'events', COUNT(*)::TEXT FROM events WHERE run_id = :run_id
UNION ALL
SELECT 'global_snapshots', COUNT(*)::TEXT FROM global_timeseries WHERE run_id = :run_id
UNION ALL
SELECT 'cluster_snapshots', COUNT(*)::TEXT FROM cluster_timeseries WHERE run_id = :run_id
UNION ALL
SELECT 'node_final_rows', COUNT(*)::TEXT FROM node_final_summary WHERE run_id = :run_id;

ROLLBACK;
