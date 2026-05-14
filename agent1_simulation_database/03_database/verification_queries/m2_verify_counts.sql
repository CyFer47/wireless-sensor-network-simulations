-- Milestone 2 verification SQL
-- Usage:
--   psql -h <host> -U <user> -d wsn_sim -v ext_run_id='20260324_123456_123' -f sql/m2_verify_counts.sql

\set ON_ERROR_STOP on

WITH target_run AS (
    SELECT run_id
    FROM wsn.runs
    WHERE experiment_version = :'ext_run_id'
    ORDER BY run_id DESC
    LIMIT 1
)
SELECT 'runs' AS table_name, COUNT(*)::BIGINT AS row_count
FROM wsn.runs r
JOIN target_run t ON t.run_id = r.run_id
UNION ALL
SELECT 'nodes_static', COUNT(*)::BIGINT
FROM wsn.nodes_static n
JOIN target_run t ON t.run_id = n.run_id
UNION ALL
SELECT 'global_timeseries', COUNT(*)::BIGINT
FROM wsn.global_timeseries g
JOIN target_run t ON t.run_id = g.run_id
UNION ALL
SELECT 'cluster_timeseries', COUNT(*)::BIGINT
FROM wsn.cluster_timeseries c
JOIN target_run t ON t.run_id = c.run_id
UNION ALL
SELECT 'events', COUNT(*)::BIGINT
FROM wsn.events e
JOIN target_run t ON t.run_id = e.run_id
UNION ALL
SELECT 'run_summary', COUNT(*)::BIGINT
FROM wsn.run_summary s
JOIN target_run t ON t.run_id = s.run_id
UNION ALL
SELECT 'node_final_summary', COUNT(*)::BIGINT
FROM wsn.node_final_summary f
JOIN target_run t ON t.run_id = f.run_id
ORDER BY table_name;
