-- ============================================================================
-- Milestone 3: Replay-Oriented SQL Queries
-- ============================================================================
-- Purpose: Helper queries for MATLAB export, web replay backend, and
--          advanced analysis. All queries are read-only.
--
-- Usage: Source this file in psql, then use the named queries below:
--   \i sql/m3_replay_queries.sql
--   SELECT * FROM m3_latest_run_metadata;
--
-- Audience: MATLAB export script, web backend developers, operators
-- ============================================================================

SET search_path TO wsn, public;

-- ============================================================================
-- 1. LATEST RUN LOOKUP
-- ============================================================================

-- Get metadata for the most recent run
CREATE OR REPLACE VIEW m3_latest_run_metadata AS
SELECT
    r.run_id,
    r.experiment_version,
    r.started_at,
    EXTRACT(EPOCH FROM (r.started_at)) :: INTEGER AS started_at_epoch,
    (SELECT COUNT(DISTINCT node_id) FROM nodes_static WHERE run_id = r.run_id) AS total_nodes,
    (SELECT COUNT(*) FROM events WHERE run_id = r.run_id) AS total_events
FROM runs r
WHERE r.run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY r.run_id DESC
LIMIT 1;

-- Get counts for a specific run_id
-- USAGE: SELECT * FROM m3_run_summary (1);
CREATE OR REPLACE VIEW m3_run_row_counts AS
WITH latest_run AS (
    SELECT MAX(run_id) AS run_id FROM runs
)
SELECT
    'nodes_static' AS table_name,
    COUNT(*) FROM nodes_static WHERE run_id = (SELECT run_id FROM latest_run)
UNION ALL
SELECT
    'global_timeseries',
    COUNT(*) FROM global_timeseries WHERE run_id = (SELECT run_id FROM latest_run)
UNION ALL
SELECT
    'cluster_timeseries',
    COUNT(*) FROM cluster_timeseries WHERE run_id = (SELECT run_id FROM latest_run)
UNION ALL
SELECT
    'events',
    COUNT(*) FROM events WHERE run_id = (SELECT run_id FROM latest_run)
UNION ALL
SELECT
    'run_summary',
    COUNT(*) FROM run_summary WHERE run_id = (SELECT run_id FROM latest_run)
UNION ALL
SELECT
    'node_final_summary',
    COUNT(*) FROM node_final_summary WHERE run_id = (SELECT run_id FROM latest_run);

-- ============================================================================
-- 2. GLOBAL TIMESERIES (Energy, Cluster Metrics Over Time)
-- ============================================================================

-- All global snapshots for a run, with energy distribution
-- USAGE: SELECT * FROM m3_global_timeseries_latest;
CREATE OR REPLACE VIEW m3_global_timeseries_latest AS
SELECT
    run_id,
    sim_time_s AS time_s,
    raw_tx_cum,
    raw_rx_cum,
    agg_tx_cum,
    agg_rx_cum,
    avg_res_j,
    min_res_j,
    max_res_j,
    consumed_j,
    low_nodes,
    failed_chs,
    recovered_clusters
FROM global_timeseries
WHERE run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY sim_time_s ASC;

-- All global timeseries for a specific run_id (parameterized via subquery)
-- USAGE: SELECT * FROM m3_global_timeseries_by_run WHERE run_id = 2;
CREATE OR REPLACE VIEW m3_global_timeseries_by_run AS
SELECT
    run_id,
    sim_time_s AS time_s,
    raw_tx_cum,
    raw_rx_cum,
    agg_tx_cum,
    agg_rx_cum,
    avg_res_j,
    min_res_j,
    max_res_j,
    consumed_j,
    low_nodes,
    failed_chs,
    recovered_clusters
FROM global_timeseries
ORDER BY run_id DESC, sim_time_s ASC;

-- ============================================================================
-- 3. CLUSTER TIMESERIES (Per-Cluster Snapshots)
-- ============================================================================

-- All cluster snapshots for the latest run
-- USAGE: SELECT * FROM m3_cluster_timeseries_latest;
CREATE OR REPLACE VIEW m3_cluster_timeseries_latest AS
SELECT
    run_id,
    cluster_id,
    sim_time_s AS time_s,
    original_ch_id,
    current_ch_id,
    status,
    mode,
    members_count,
    ch_res_j,
    avg_mem_res_j,
    cluster_consumed_j
FROM cluster_timeseries
WHERE run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY sim_time_s ASC, cluster_id ASC;

-- Cluster timeseries for a specific run
-- USAGE: SELECT * FROM m3_cluster_timeseries_by_run WHERE run_id = 2;
CREATE OR REPLACE VIEW m3_cluster_timeseries_by_run AS
SELECT
    run_id,
    cluster_id,
    sim_time_s AS time_s,
    original_ch_id,
    current_ch_id,
    status,
    mode,
    members_count,
    ch_res_j,
    avg_mem_res_j,
    cluster_consumed_j
FROM cluster_timeseries
ORDER BY run_id DESC, sim_time_s ASC, cluster_id ASC;

-- ============================================================================
-- 4. EVENTS (Failures, Recovery, Role Changes)
-- ============================================================================

-- All events for the latest run, with context
-- USAGE: SELECT * FROM m3_events_latest;
CREATE OR REPLACE VIEW m3_events_latest AS
SELECT
    run_id,
    event_id,
    sim_time_s AS time_s,
    event_type,
    severity,
    node_id,
    cluster_id,
    message,
    details
FROM events
WHERE run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY sim_time_s ASC;

-- Recent events for first inspection (top N)
-- USAGE: SELECT * FROM m3_recent_events_latest LIMIT 20;
CREATE OR REPLACE VIEW m3_recent_events_latest AS
SELECT
    run_id,
    event_id,
    sim_time_s AS time_s,
    event_type,
    severity,
    node_id,
    cluster_id,
    message,
    details
FROM events
WHERE run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY sim_time_s DESC
LIMIT 50;

-- ============================================================================
-- 5. NODE FINAL SUMMARY (End-of-Run Node State)
-- ============================================================================

-- Final energy state of all nodes in the latest run
-- USAGE: SELECT * FROM m3_node_final_summary_latest;
CREATE OR REPLACE VIEW m3_node_final_summary_latest AS
SELECT
    run_id,
    node_id,
    role,
    cluster_id,
    residual_j,
    consumed_j,
    final_status
FROM node_final_summary
WHERE run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY node_id ASC;

-- Final summary for a specific run
-- USAGE: SELECT * FROM m3_node_final_summary_by_run WHERE run_id = 2;
CREATE OR REPLACE VIEW m3_node_final_summary_by_run AS
SELECT
    run_id,
    node_id,
    role,
    cluster_id,
    residual_j,
    consumed_j,
    final_status
FROM node_final_summary
ORDER BY run_id DESC, node_id ASC;

-- Energy distribution summary for the latest run
-- USAGE: SELECT * FROM m3_node_energy_distribution_latest;
CREATE OR REPLACE VIEW m3_node_energy_distribution_latest AS
SELECT
    run_id,
    COUNT(*) AS node_count,
    MIN(residual_j) AS min_residual_j,
    MAX(residual_j) AS max_residual_j,
    AVG(residual_j) :: NUMERIC(10,3) AS avg_residual_j,
    AVG(consumed_j) :: NUMERIC(10,3) AS avg_consumed_j,
    COUNT(CASE WHEN final_status = 'normal' THEN 1 END) AS alive_count,
    COUNT(CASE WHEN final_status != 'normal' THEN 1 END) AS dead_count
FROM node_final_summary
WHERE run_id = (SELECT MAX(run_id) FROM runs)
GROUP BY run_id;

-- ============================================================================
-- 6. RUN SUMMARY (Overall Run Metrics)
-- ============================================================================

-- Complete summary for the latest run
-- USAGE: SELECT * FROM m3_run_summary_latest;
CREATE OR REPLACE VIEW m3_run_summary_latest AS
SELECT
    run_id,
    final_sim_time_s,
    raw_tx_cum,
    agg_tx_cum,
    agg_rx_cum,
    failed_chs,
    recovered_clusters,
    consumed_j,
    avg_res_j
FROM run_summary
WHERE run_id = (SELECT MAX(run_id) FROM runs)
LIMIT 1;

-- ============================================================================
-- 7. STATIC NODE INFO (Topology)
-- ============================================================================

-- All nodes in the latest run with initial/static properties
-- USAGE: SELECT * FROM m3_nodes_static_latest;
CREATE OR REPLACE VIEW m3_nodes_static_latest AS
SELECT
    run_id,
    node_id,
    x,
    y,
    z,
    initial_energy_j,
    original_cluster_id,
    role
FROM nodes_static
WHERE run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY node_id ASC;

-- ============================================================================
-- 8. CLUSTER RECOVERY TIMELINE (Failures and Recoveries)
-- ============================================================================

-- Extract failure and recovery events from events table
-- USAGE: SELECT * FROM m3_cluster_failure_timeline_latest;
CREATE OR REPLACE VIEW m3_cluster_failure_timeline_latest AS
SELECT
    e.run_id,
    e.sim_time_s AS time_s,
    e.cluster_id,
    e.event_type,
    e.node_id AS affected_node,
    e.message,
    e.details
FROM events e
WHERE e.run_id = (SELECT MAX(run_id) FROM runs)
  AND e.event_type IN ('CH_FAILURE', 'CLUSTER_RECOVERED', 'NODE_FAILURE')
ORDER BY e.sim_time_s ASC;

-- ============================================================================
-- 9. HELPER FUNCTION: Get row counts for any run_id
-- ============================================================================

-- SQL function to fetch row counts for a given run
-- USAGE: SELECT * FROM m3_run_row_counts_for_run(2);
--
-- Note: This is a view using CTEs, not a true function.
-- For parameterized queries, query the base tables directly with WHERE run_id = $1
--
-- Example for Python/application code:
--   SELECT COUNT(*) FROM nodes_static WHERE run_id = %s
--   SELECT COUNT(*) FROM global_timeseries WHERE run_id = %s
--   ... etc

-- ============================================================================
-- 10. SUMMARY QUERIES (Good for Operators/MATLAB Export)
-- ============================================================================

-- One-shot query: Get everything needed for MATLAB export in one go
-- USAGE: \i sql/m3_replay_queries.sql
--        SELECT run_id, experiment_version, started_at FROM m3_latest_run_metadata \gx

-- For MATLAB export, use the individual views above:
--   m3_nodes_static_latest          → nodes_static.csv
--   m3_global_timeseries_latest     → global_timeseries.csv
--   m3_cluster_timeseries_latest    → cluster_timeseries.csv
--   m3_events_latest                → events.csv
--   m3_node_final_summary_latest    → node_final_summary.csv
--   m3_run_summary_latest           → run_summary.csv

-- ============================================================================
-- Notes on Usage
-- ============================================================================
--
-- For MATLAB/Python Export:
--   1. Source this file to create views
--   2. Use psycopg2 to query views with SELECT * FROM m3_*_latest;
--   3. Write results to CSV using Python csv.writer
--   4. See importer/export_run_for_matlab.py for complete example
--
-- For Web Replay Backend:
--   1. Query m3_global_timeseries_by_run for animation timeline
--   2. Query m3_cluster_timeseries_by_run for cluster state per timestamp
--   3. Query m3_events_latest for event markers on timeline
--   4. Use m3_nodes_static_latest for initial node positions
--
-- For Operators/Inspection:
--   1. Run tools/inspect_latest_run.py (uses these views internally)
--   2. Or manually query m3_latest_run_metadata + m3_run_row_counts
--
-- All views use (SELECT MAX(run_id) FROM runs) for "latest" logic
-- Customize by changing WHERE run_id = X for specific runs

-- ============================================================================
-- VERIFICATION: List all M3 views created
-- ============================================================================
-- Run this to see all available views:
--   SELECT table_name FROM information_schema.views
--   WHERE table_schema = 'wsn' AND table_name LIKE 'm3_%'
--   ORDER BY table_name;

SET search_path TO wsn, public;
