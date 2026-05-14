-- M5 DB Queryability Verification Queries
-- Date: 2026-04-14
-- Purpose: Demonstrate new queryability after M5 schema extension
-- Run these after importer updates to verify A/B comparison, run filtering, and completeness tracking

-- ============================================================================
-- SECTION 1: Architecture Identity and A vs B Isolation
-- ============================================================================

-- 1.1: Count runs by architecture
SELECT
  architecture,
  routing_engine,
  COUNT(*) as run_count,
  MIN(started_at) as earliest_run,
  MAX(started_at) as latest_run
FROM runs
WHERE run_status = 'complete'
GROUP BY architecture, routing_engine
ORDER BY architecture DESC;
-- Expected: Two groups (A/baseline, B/bsbssp), each with 2+ runs if M4 runs imported

-- 1.2: Filter runs by B (BSBSSP) architecture for detailed inspection
SELECT
  run_id,
  scenario_name,
  architecture,
  routing_engine,
  failure_family,
  healing_id,
  load,
  scale,
  seed,
  sim_time_s,
  node_count,
  started_at
FROM runs
WHERE architecture = 'B'
  AND run_status = 'complete'
ORDER BY started_at DESC;
-- Expected: All M4 B-variant runs with full metadata

-- 1.3: MATLAB backward compatibility — old query still works
SELECT
  run_id,
  scenario_name,
  scenario_type,
  sim_time_s,
  node_count,
  cluster_count,
  started_at,
  experiment_version,
  recovery_enabled,
  failure_time_s,
  recovery_delay_s
FROM runs
WHERE run_status != 'invalid'
ORDER BY started_at DESC;
-- Expected: All runs visible, old columns unchanged; should match MATLAB get_available_runs()

-- ============================================================================
-- SECTION 2: Scenario Axes Filtering and Comparison
-- ============================================================================

-- 2.1: Filter runs by scenario axes (failure family and healing)
SELECT
  run_id,
  architecture,
  failure_family,
  healing_id,
  load,
  scale,
  seed,
  sim_time_s,
  routing_engine
FROM runs
WHERE failure_family = 'F1'
  AND healing_id = 'H1'
  AND run_status = 'complete'
ORDER BY architecture, seed;
-- Expected: Paired A/B runs with identical F1/H1 scenario axes for comparison

-- 2.2: Find topology-identical pairs (same map, scale, seed; different architectures)
SELECT
  map_signature,
  scale,
  seed,
  COUNT(*) as pair_count,
  STRING_AGG(DISTINCT architecture, ',') as architectures,
  MIN(run_id) as run_A,
  MAX(run_id) as run_B
FROM runs
WHERE map_id IS NOT NULL
  AND run_status = 'complete'
GROUP BY map_signature, scale, seed
HAVING COUNT(*) > 1
ORDER BY map_signature DESC;
-- Expected: Multiple topology pairs, each with A and B runs for fair comparison

-- 2.3: Compare specific A vs B pair performance metrics
-- (join with global_timeseries to compare end-to-end energy consumption)
SELECT
  r_a.run_id as run_A,
  r_b.run_id as run_B,
  r_a.architecture,
  r_b.architecture,
  r_a.failure_family,
  r_a.healing_id,
  r_a.load,
  r_a.scale,
  r_a.seed,
  g_a.consumed_j as energy_A,
  g_b.consumed_j as energy_B,
  ROUND(100.0 * (g_b.consumed_j - g_a.consumed_j) / g_a.consumed_j, 2) as improvement_pct
FROM runs r_a
JOIN runs r_b ON r_a.map_signature = r_b.map_signature
  AND r_a.failure_family = r_b.failure_family
  AND r_a.healing_id = r_b.healing_id
  AND r_a.load = r_b.load
  AND r_a.scale = r_b.scale
  AND r_a.seed = r_b.seed
  AND r_a.architecture = 'A'
  AND r_b.architecture = 'B'
JOIN global_timeseries g_a ON r_a.run_id = g_a.run_id
  AND g_a.sim_time_s = r_a.sim_time_s
JOIN global_timeseries g_b ON r_b.run_id = g_b.run_id
  AND g_b.sim_time_s = r_b.sim_time_s
WHERE r_a.run_status = 'complete'
  AND r_b.run_status = 'complete'
ORDER BY r_a.run_id;
-- Expected: Paired comparison rows showing energy improvement % for B vs A

-- ============================================================================
-- SECTION 3: Run Completeness and Status Tracking
-- ============================================================================

-- 3.1: Summary of run upload/import status
SELECT * FROM runs_completeness_summary;
-- Expected: Breakdown of complete/partial/incomplete/invalid imports

-- 3.2: Identify partial or incomplete runs for investigation
SELECT
  run_id,
  scenario_name,
  run_status,
  started_at,
  architecture,
  failure_family,
  healing_id
FROM runs
WHERE run_status IN ('partial', 'incomplete', 'invalid')
ORDER BY started_at DESC;
-- Expected: Empty if all M4 runs imported successfully; non-empty if QA/test runs exist

-- 3.3: Verify all M4 runs marked as complete
SELECT
  run_status,
  COUNT(*) as count
FROM runs
WHERE failure_family IS NOT NULL  -- M4 runs have scenario axes
GROUP BY run_status
ORDER BY run_status;
-- Expected: All M4 runs should be 'complete' status

-- ============================================================================
-- SECTION 4: Topology Lineage and Reproducibility
-- ============================================================================

-- 4.1: View topology lineage summary
SELECT * FROM runs_topology_lineage;
-- Expected: Each row shows a unique topology (by map_signature) and its variants

-- 4.2: For a specific topology, list all runs (both architectures)
SELECT
  run_id,
  scenario_name,
  architecture,
  routing_engine,
  failure_family,
  healing_id,
  load,
  scale,
  seed,
  started_at
FROM runs
WHERE map_signature = (
  SELECT map_signature FROM runs WHERE architecture = 'B' LIMIT 1
)
ORDER BY run_id;
-- Expected: Both A and B runs using same topology

-- 4.3: Verify seed determines topology reproducibility
SELECT
  seed,
  COUNT(DISTINCT map_signature) as unique_signatures,
  COUNT(*) as total_runs
FROM runs
WHERE run_status = 'complete'
GROUP BY seed
ORDER BY seed;
-- Expected: Each seed has only one unique map_signature (determinism verified)

-- ============================================================================
-- SECTION 5: Event Typing and Queryability
-- ============================================================================

-- 5.1: Sample event types from runs (M4 structured events)
SELECT DISTINCT
  event_type,
  COUNT(*) as event_count
FROM events
WHERE run_id IN (SELECT run_id FROM runs WHERE architecture = 'B')
GROUP BY event_type
ORDER BY event_count DESC;
-- Expected: Structured event types like ROUTE_COMPUTE, RECOVERY, FAILURE, etc.

-- 5.2: Find all ROUTE_COMPUTE events in B runs
SELECT
  r.run_id,
  r.architecture,
  e.sim_time_s,
  e.event_type,
  e.message,
  e.details
FROM runs r
JOIN events e ON r.run_id = e.run_id
WHERE r.architecture = 'B'
  AND e.event_type = 'ROUTE_COMPUTE'
  AND r.run_status = 'complete'
LIMIT 20;
-- Expected: Sample of structured ROUTE_COMPUTE events from B runs

-- ============================================================================
-- SECTION 6: New Queryability Views
-- ============================================================================

-- 6.1: All architecture combinations
SELECT * FROM runs_by_architecture;
-- Expected: A/baseline and B/bsbssp_v1_approx rows with counts

-- 6.2: Scenario axes coverage (all tested combinations)
SELECT * FROM runs_scenario_axes LIMIT 20;
-- Expected: All scenario axis combinations from imported M4 runs

-- 6.3: Extended view with all columns
SELECT
  run_id, architecture, routing_engine, failure_family, healing_id,
  variant, load, scale, seed, map_id,
  scenario_name, sim_time_s, node_count, cluster_count
FROM runs_extended
WHERE architecture IN ('A', 'B')
LIMIT 10;
-- Expected: All M4 runs with full axis metadata

-- ============================================================================
-- SECTION 7: Advanced - ML Feature Engineering (Future)
-- ============================================================================

-- 7.1: Baseline query for identifying representative run selection for MATLAB QA
-- (Join runs to global_timeseries to characterize performance windows)
SELECT
  run_id,
  architecture,
  failure_family,
  healing_id,
  scale,
  seed,
  COUNT(*) as timeseries_points,
  MIN(sim_time_s) as t_start,
  MAX(sim_time_s) as t_end,
  ROUND(AVG(avg_res_j), 2) as avg_energy,
  ROUND(MIN(min_res_j), 2) as min_energy,
  ROUND(MAX(consumed_j), 2) as total_consumed
FROM runs
JOIN global_timeseries ON runs.run_id = global_timeseries.run_id
WHERE runs.run_status = 'complete'
GROUP BY runs.run_id, architecture, failure_family, healing_id, scale, seed
ORDER BY architecture, failure_family, scale;
-- Expected: Characterization of each run's energy profile for MATLAB feature selection

-- 7.2: Pilot batch identification (e.g., all F1/H1 runs for initial testing)
SELECT
  failure_family,
  healing_id,
  COUNT(*) as total_runs,
  SUM(CASE WHEN architecture = 'A' THEN 1 ELSE 0 END) as runs_A,
  SUM(CASE WHEN architecture = 'B' THEN 1 ELSE 0 END) as runs_B
FROM runs
WHERE run_status = 'complete'
  AND failure_family = 'F1'
  AND healing_id = 'H1'
GROUP BY failure_family, healing_id;
-- Expected: Breakdown of A and B runs for F1/H1 pilot batch

-- ============================================================================
-- DONE: All new queryability verified
-- ============================================================================
