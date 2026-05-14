-- M7 metadata gate compatibility views
-- Purpose: expose required M7 field names without altering base M5 tables.

CREATE OR REPLACE VIEW runs_m7_metadata_gate AS
SELECT
  run_id,
  scenario_name,
  experiment_version,
  architecture AS architecture_id,
  failure_family AS failure_family_id,
  healing_id,
  variant AS variant_id,
  load AS load_id,
  scale AS scale_id,
  seed,
  run_status,
  map_id AS topology_map_id,
  CASE
    WHEN map_id IS NULL THEN NULL
    ELSE 'm2_map_v1'
  END AS topology_map_version,
  map_signature,
  routing_engine,
  started_at
FROM runs;

CREATE OR REPLACE VIEW events_m7_metadata_gate AS
SELECT
  e.event_id,
  e.run_id,
  e.sim_time_s,
  e.event_type,
  e.severity,
  e.cluster_id,
  e.node_id,
  e.message,
  e.details,
  r.event_code AS event_code,
  r.event_class
FROM events e
LEFT JOIN event_code_reference r
  ON e.event_type = r.event_code;
