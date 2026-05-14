-- Milestone 1: WSN simulation storage foundation
-- Recommended DB: wsn_sim
-- Schema version label: m1_v1

BEGIN;

CREATE SCHEMA IF NOT EXISTS wsn;
SET search_path TO wsn, public;

-- 1) runs: one row per simulation run
CREATE TABLE IF NOT EXISTS runs (
    run_id BIGSERIAL PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    scenario_type TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sim_time_s NUMERIC(12,3) NOT NULL CHECK (sim_time_s >= 0),

    node_count INTEGER NOT NULL CHECK (node_count > 0),
    cluster_count INTEGER NOT NULL CHECK (cluster_count > 0),
    traffic_interval_s NUMERIC(12,3) NOT NULL CHECK (traffic_interval_s > 0),
    aggregation_interval_s NUMERIC(12,3) NOT NULL CHECK (aggregation_interval_s > 0),
    failure_time_s NUMERIC(12,3),
    recovery_delay_s NUMERIC(12,3),
    recovery_enabled BOOLEAN NOT NULL,

    schema_version TEXT NOT NULL DEFAULT 'm1_v1',
    experiment_version TEXT,
    notes TEXT
);

-- 2) nodes_static: static metadata per node per run
CREATE TABLE IF NOT EXISTS nodes_static (
    run_id BIGINT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    node_id INTEGER NOT NULL CHECK (node_id >= 0),
    role TEXT NOT NULL CHECK (role IN ('member', 'ch', 'bs')),
    original_cluster_id INTEGER,
    original_ch_id INTEGER,
    initial_energy_j NUMERIC(12,6) NOT NULL CHECK (initial_energy_j >= 0),
    x NUMERIC(12,4) NOT NULL,
    y NUMERIC(12,4) NOT NULL,
    z NUMERIC(12,4) NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, node_id)
);

-- 3) global_timeseries: one snapshot row per run/time
CREATE TABLE IF NOT EXISTS global_timeseries (
    run_id BIGINT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    sim_time_s NUMERIC(12,3) NOT NULL CHECK (sim_time_s >= 0),

    raw_tx_cum BIGINT NOT NULL CHECK (raw_tx_cum >= 0),
    raw_rx_cum BIGINT NOT NULL CHECK (raw_rx_cum >= 0),
    agg_tx_cum BIGINT NOT NULL CHECK (agg_tx_cum >= 0),
    agg_rx_cum BIGINT NOT NULL CHECK (agg_rx_cum >= 0),
    direct_agg_rx_cum BIGINT NOT NULL CHECK (direct_agg_rx_cum >= 0),
    relayed_agg_rx_cum BIGINT NOT NULL CHECK (relayed_agg_rx_cum >= 0),
    relay_fwd_cum BIGINT NOT NULL CHECK (relay_fwd_cum >= 0),

    avg_res_j NUMERIC(12,6) NOT NULL CHECK (avg_res_j >= 0),
    min_res_j NUMERIC(12,6) NOT NULL CHECK (min_res_j >= 0),
    consumed_j NUMERIC(14,6) NOT NULL CHECK (consumed_j >= 0),
    low_nodes INTEGER NOT NULL CHECK (low_nodes >= 0),
    failed_chs INTEGER NOT NULL CHECK (failed_chs >= 0),
    recovered_clusters INTEGER NOT NULL CHECK (recovered_clusters >= 0),
    pending_raw_total BIGINT NOT NULL CHECK (pending_raw_total >= 0),

    PRIMARY KEY (run_id, sim_time_s)
);

-- 4) cluster_timeseries: one snapshot row per run/time/cluster
CREATE TABLE IF NOT EXISTS cluster_timeseries (
    run_id BIGINT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    sim_time_s NUMERIC(12,3) NOT NULL CHECK (sim_time_s >= 0),
    cluster_id INTEGER NOT NULL CHECK (cluster_id >= 0),

    original_ch_id INTEGER,
    current_ch_id INTEGER,
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    next_hop TEXT NOT NULL,

    members_count INTEGER NOT NULL CHECK (members_count >= 0),
    raw_rx_cum BIGINT NOT NULL CHECK (raw_rx_cum >= 0),
    pending_raw BIGINT NOT NULL CHECK (pending_raw >= 0),
    agg_tx_cum BIGINT NOT NULL CHECK (agg_tx_cum >= 0),
    relay_fwd_cum BIGINT NOT NULL CHECK (relay_fwd_cum >= 0),

    ch_res_j NUMERIC(12,6) NOT NULL CHECK (ch_res_j >= 0),
    avg_mem_res_j NUMERIC(12,6) NOT NULL CHECK (avg_mem_res_j >= 0),
    cluster_consumed_j NUMERIC(14,6) NOT NULL CHECK (cluster_consumed_j >= 0),

    PRIMARY KEY (run_id, sim_time_s, cluster_id)
);

-- 5) events: event log rows
CREATE TABLE IF NOT EXISTS events (
    event_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    sim_time_s NUMERIC(12,3) NOT NULL CHECK (sim_time_s >= 0),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    cluster_id INTEGER,
    node_id INTEGER,
    message TEXT NOT NULL,
    details JSONB
);

-- 6) run_summary: one final summary row per run
CREATE TABLE IF NOT EXISTS run_summary (
    run_id BIGINT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
    final_sim_time_s NUMERIC(12,3) NOT NULL CHECK (final_sim_time_s >= 0),

    raw_tx_cum BIGINT NOT NULL CHECK (raw_tx_cum >= 0),
    raw_rx_cum BIGINT NOT NULL CHECK (raw_rx_cum >= 0),
    agg_tx_cum BIGINT NOT NULL CHECK (agg_tx_cum >= 0),
    agg_rx_cum BIGINT NOT NULL CHECK (agg_rx_cum >= 0),
    direct_agg_rx_cum BIGINT NOT NULL CHECK (direct_agg_rx_cum >= 0),
    relayed_agg_rx_cum BIGINT NOT NULL CHECK (relayed_agg_rx_cum >= 0),
    relay_fwd_cum BIGINT NOT NULL CHECK (relay_fwd_cum >= 0),
    failed_chs INTEGER NOT NULL CHECK (failed_chs >= 0),
    recovered_clusters INTEGER NOT NULL CHECK (recovered_clusters >= 0),

    avg_res_j NUMERIC(12,6) NOT NULL CHECK (avg_res_j >= 0),
    min_res_j NUMERIC(12,6) NOT NULL CHECK (min_res_j >= 0),
    consumed_j NUMERIC(14,6) NOT NULL CHECK (consumed_j >= 0),
    low_nodes INTEGER NOT NULL CHECK (low_nodes >= 0),
    pending_raw_total BIGINT NOT NULL CHECK (pending_raw_total >= 0)
);

-- 7) node_final_summary: one final row per node per run
CREATE TABLE IF NOT EXISTS node_final_summary (
    run_id BIGINT NOT NULL,
    node_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('member', 'ch', 'bs')),
    cluster_id INTEGER,
    residual_j NUMERIC(12,6) NOT NULL CHECK (residual_j >= 0),
    consumed_j NUMERIC(14,6) NOT NULL CHECK (consumed_j >= 0),
    final_status TEXT NOT NULL,
    PRIMARY KEY (run_id, node_id),
    CONSTRAINT fk_node_final_summary_run FOREIGN KEY (run_id)
        REFERENCES runs(run_id) ON DELETE CASCADE,
    CONSTRAINT fk_node_final_summary_node FOREIGN KEY (run_id, node_id)
        REFERENCES nodes_static(run_id, node_id) ON DELETE CASCADE
);

-- Indexes (PKs already index run_id and other PK keys; add query-oriented indexes)
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_scenario ON runs(scenario_name, scenario_type);

CREATE INDEX IF NOT EXISTS idx_global_timeseries_run_time
    ON global_timeseries(run_id, sim_time_s);

CREATE INDEX IF NOT EXISTS idx_cluster_timeseries_run_time_cluster
    ON cluster_timeseries(run_id, sim_time_s, cluster_id);

CREATE INDEX IF NOT EXISTS idx_events_run_time
    ON events(run_id, sim_time_s);

CREATE INDEX IF NOT EXISTS idx_events_run_type
    ON events(run_id, event_type);

CREATE INDEX IF NOT EXISTS idx_node_final_summary_run_node
    ON node_final_summary(run_id, node_id);

CREATE INDEX IF NOT EXISTS idx_nodes_static_run_role
    ON nodes_static(run_id, role);

COMMIT;
