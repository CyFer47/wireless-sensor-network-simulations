-- M5 MATLAB Compatibility Views
-- Date: 2026-04-14
-- Purpose: Provide MATLAB queries with stable column interface while new columns exist
-- Philosophy: Views present old column shape; no breaking changes to existing queries

-- View: runs_matlab_compat
-- Provides the exact columns MATLAB queries expect from the runs table
-- Existing columns passed through; new M5 columns available separately
CREATE OR REPLACE VIEW runs_matlab_compat AS
SELECT
  run_id,
  scenario_name,
  CASE WHEN scenario_type IS NULL THEN 'implicit' ELSE scenario_type END AS scenario_type,
  sim_time_s,
  node_count,
  cluster_count,
  started_at,
  experiment_version,
  recovery_enabled,
  failure_time_s,
  recovery_delay_s
FROM runs
WHERE run_status != 'invalid';  -- Filter out bad imports

-- View: runs_extended
-- Full runs table with both old and new columns for advanced queries
CREATE OR REPLACE VIEW runs_extended AS
SELECT
  run_id,
  -- Old columns (MATLAB-safe)
  scenario_name,
  scenario_type,
  sim_time_s,
  node_count,
  cluster_count,
  started_at,
  experiment_version,
  recovery_enabled,
  failure_time_s,
  recovery_delay_s,
  -- New M5 columns (scenario axes and architecture)
  architecture,
  failure_family,
  healing_id,
  variant,
  load,
  scale,
  seed,
  map_id,
  map_signature,
  routing_engine,
  run_status,
  external_run_id_new
FROM runs
WHERE run_status != 'invalid';

-- View: runs_by_architecture
-- Quick filtering by A vs B
CREATE OR REPLACE VIEW runs_by_architecture AS
SELECT
  architecture,
  COUNT(*) as run_count,
  routing_engine,
  MIN(started_at) as earliest_run,
  MAX(started_at) as latest_run
FROM runs
WHERE run_status = 'complete'
GROUP BY architecture, routing_engine
ORDER BY architecture, routing_engine;

-- View: runs_scenario_axes
-- Summarize all scenario axes combinations
CREATE OR REPLACE VIEW runs_scenario_axes AS
SELECT
  architecture,
  failure_family,
  healing_id,
  variant,
  load,
  scale,
  seed,
  COUNT(*) as run_count,
  MIN(started_at) as earliest,
  MAX(started_at) as latest,
  STRING_AGG(DISTINCT scenario_name, ', ') as scenario_names
FROM runs
WHERE run_status = 'complete'
GROUP BY architecture, failure_family, healing_id, variant, load, scale, seed
ORDER BY architecture, failure_family, healing_id, variant, load, scale, seed;

-- View: runs_topology_lineage
-- Track unique topologies and their runs
CREATE OR REPLACE VIEW runs_topology_lineage AS
SELECT
  map_id,
  map_signature,
  scale,
  seed,
  node_count,
  cluster_count,
  COUNT(*) as run_count,
  STRING_AGG(DISTINCT architecture, ', ') as architectures,
  STRING_AGG(DISTINCT routing_engine, ', ') as routing_engines,
  MIN(started_at) as first_run,
  MAX(started_at) as last_run
FROM runs
WHERE run_status = 'complete' AND map_id IS NOT NULL
GROUP BY map_id, map_signature, scale, seed, node_count, cluster_count
ORDER BY map_id, map_signature, scale;

-- View: runs_completeness_summary
-- Quick check on import status
CREATE OR REPLACE VIEW runs_completeness_summary AS
SELECT
  run_status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM runs
GROUP BY run_status
ORDER BY run_status;
