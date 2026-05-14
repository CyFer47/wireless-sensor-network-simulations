-- M5 Schema Extension: Minimal Additive Hardening
-- Date: 2026-04-14
-- Purpose: Add scenario axes and architecture identity columns to runs table
-- Philosophy: Additive only, no deletions or renames; idempotent and safe to re-run

-- Add new columns to runs table for scenario axes and architecture tracking
ALTER TABLE runs ADD COLUMN IF NOT EXISTS architecture CHAR(1) DEFAULT 'A';
COMMENT ON COLUMN runs.architecture IS 'A or B; architecture version of this run';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS failure_family TEXT;
COMMENT ON COLUMN runs.failure_family IS 'Failure scenario family (F0, F1, F2, F3, F4)';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS healing_id TEXT;
COMMENT ON COLUMN runs.healing_id IS 'Healing scenario ID (H0, H1, H2, H3, H4)';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS variant TEXT;
COMMENT ON COLUMN runs.variant IS 'Scenario variant code (V1, V2, V3)';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS load TEXT;
COMMENT ON COLUMN runs.load IS 'Traffic load level (L1, L2, L3)';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS scale TEXT;
COMMENT ON COLUMN runs.scale IS 'Scale/topology variant (S1, S2, S3, S4, S5, S6)';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS seed INT;
COMMENT ON COLUMN runs.seed IS 'Random seed for determinism anchor';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS map_id TEXT;
COMMENT ON COLUMN runs.map_id IS 'Topology map package identifier';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS map_signature TEXT;
COMMENT ON COLUMN runs.map_signature IS 'Deterministic SHA256 of topology package';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS routing_engine TEXT DEFAULT 'baseline';
COMMENT ON COLUMN runs.routing_engine IS 'baseline (A) or bsbssp_v1_approx (B)';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS run_status TEXT DEFAULT 'complete';
COMMENT ON COLUMN runs.run_status IS 'complete, partial, incomplete, invalid; upload status';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS external_run_id_new TEXT;
COMMENT ON COLUMN runs.external_run_id_new IS 'Stable external ID anchor (future use; experiment_version remains primary)';

-- Add index for fast filtering by architecture and routing_engine
CREATE INDEX IF NOT EXISTS idx_runs_architecture ON runs(architecture);
CREATE INDEX IF NOT EXISTS idx_runs_routing_engine ON runs(routing_engine);
CREATE INDEX IF NOT EXISTS idx_runs_failure_family ON runs(failure_family);
CREATE INDEX IF NOT EXISTS idx_runs_architecture_status ON runs(architecture, run_status);

-- Optional: Create lookup table for scenario axes vocabulary (frozen reference)
CREATE TABLE IF NOT EXISTS scenario_axes_enum (
  axis_name TEXT NOT NULL,
  axis_value TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (axis_name, axis_value)
);

-- Populate scenario axes reference table
INSERT INTO scenario_axes_enum (axis_name, axis_value, description) VALUES
  ('failure_family', 'F0', 'No failures'),
  ('failure_family', 'F1', 'Single node failure at t=failure_time_s'),
  ('failure_family', 'F2', 'Cascade failure'),
  ('failure_family', 'F3', 'Network partition'),
  ('failure_family', 'F4', 'Byzantine failures'),
  ('healing_id', 'H0', 'No recovery'),
  ('healing_id', 'H1', 'Immediate recovery'),
  ('healing_id', 'H2', 'Delayed recovery'),
  ('healing_id', 'H3', 'Probabilistic recovery'),
  ('healing_id', 'H4', 'Multi-phase recovery'),
  ('variant', 'V1', 'Baseline'),
  ('variant', 'V2', 'Conservative'),
  ('variant', 'V3', 'Aggressive'),
  ('load', 'L1', 'Light traffic (1 msg/s)'),
  ('load', 'L2', 'Moderate traffic (5 msg/s)'),
  ('load', 'L3', 'Heavy traffic (10 msg/s)'),
  ('scale', 'S1', 'Small (10 nodes)'),
  ('scale', 'S2', '20 nodes'),
  ('scale', 'S3', '50 nodes'),
  ('scale', 'S4', '100 nodes'),
  ('scale', 'S5', '200 nodes'),
  ('scale', 'S6', '500 nodes')
ON CONFLICT DO NOTHING;

-- Optional: Create event code reference table (frozen taxonomy)
CREATE TABLE IF NOT EXISTS event_code_reference (
  event_code TEXT PRIMARY KEY,
  event_class TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate event code reference
INSERT INTO event_code_reference (event_code, event_class, description) VALUES
  ('FAILURE', 'system', 'Node or link failure event'),
  ('RECOVERY', 'system', 'Recovery or healing event'),
  ('ROUTE_COMPUTE', 'protocol', 'Routing algorithm compute step'),
  ('ROUTE_UPDATE', 'protocol', 'Routing table update or propagation'),
  ('DATA_SEND', 'traffic', 'Data packet transmission'),
  ('DATA_RECEIVE', 'traffic', 'Data packet reception'),
  ('CLUSTER_MERGE', 'cluster', 'Cluster formation or merge'),
  ('CLUSTER_SPLIT', 'cluster', 'Cluster split or dissolution'),
  ('CH_ELECTION', 'cluster', 'Cluster head election'),
  ('AGG_COMPLETE', 'aggregation', 'Data aggregation window complete'),
  ('SIM_START', 'system', 'Simulation start marker'),
  ('SIM_END', 'system', 'Simulation end marker')
ON CONFLICT DO NOTHING;

-- Verify migration
SELECT 
  'runs' AS table_name,
  COUNT(column_name) AS new_column_count,
  ARRAY_AGG(column_name) AS columns
FROM information_schema.columns
WHERE table_name = 'runs' AND (
  column_name IN ('architecture', 'failure_family', 'healing_id', 'variant', 'load', 'scale', 'seed', 'map_id', 'map_signature', 'routing_engine', 'run_status', 'external_run_id_new')
)
GROUP BY table_name;
