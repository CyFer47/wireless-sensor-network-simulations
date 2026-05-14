#!/usr/bin/env python3
"""
inspect_latest_run.py

Purpose:
  Operator-friendly CLI tool to quickly inspect the latest (or specific) run
  without needing SQL knowledge.

Usage:
  python3 tools/inspect_latest_run.py --env-file config/.env
  python3 tools/inspect_latest_run.py --run-id 2 --env-file config/.env

Output:
  Formatted summary of run metadata, node counts, row counts, recent events,
  and energy distribution.

Author: WSN Dashboard Milestone 3
"""

import argparse
import os
import sys
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2-binary not found. Install with:")
    print("  pip install psycopg2-binary")
    sys.exit(2)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not found. Install with:")
    print("  pip install python-dotenv")
    sys.exit(2)


def load_env(env_file):
    """Load PostgreSQL config from .env file."""
    if not os.path.exists(env_file):
        print(f"ERROR: .env file not found: {env_file}")
        sys.exit(1)
    
    load_dotenv(env_file)
    
    required = ['PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGSCHEMA']
    config = {}
    for key in required:
        val = os.getenv(key)
        if not val:
            print(f"ERROR: Missing required env var: {key}")
            sys.exit(1)
        config[key] = val
    
    return config


def connect_db(config):
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=config['PGHOST'],
            port=int(config['PGPORT']),
            database=config['PGDATABASE'],
            user=config['PGUSER'],
            password=config['PGPASSWORD']
        )
        return conn
    except psycopg2.Error as e:
        print(f"ERROR: Failed to connect to PostgreSQL: {e}")
        sys.exit(1)


def get_run_id(conn, config, run_id=None):
    """Get the run_id, default to latest if not specified."""
    cur = conn.cursor()
    schema = config['PGSCHEMA']
    
    try:
        if run_id is None:
            cur.execute(f"SET search_path TO {schema}; SELECT MAX(run_id) FROM runs;")
            result = cur.fetchone()
            if result[0] is None:
                print("ERROR: No runs found in database")
                sys.exit(1)
            run_id = result[0]
        else:
            cur.execute(f"SET search_path TO {schema}; SELECT run_id FROM runs WHERE run_id = %s;", (run_id,))
            if cur.fetchone() is None:
                print(f"ERROR: Run ID {run_id} not found")
                sys.exit(1)
        
        return run_id
    finally:
        cur.close()


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{title}")
    print(f"{'-' * 80}")


def format_timestamp(ts):
    """Format a timestamp nicely."""
    if ts:
        return ts.strftime("%Y-%m-%d %H:%M:%S UTC")
    return "N/A"


def main():
    parser = argparse.ArgumentParser(
        description='Inspect a WSN Dashboard run (latest by default)'
    )
    parser.add_argument(
        '--env-file',
        default='config/.env',
        help='Path to .env file (default: config/.env)'
    )
    parser.add_argument(
        '--run-id',
        type=int,
        default=None,
        help='Specific run_id to inspect (default: latest)'
    )
    
    args = parser.parse_args()
    
    # Load config and connect
    config = load_env(args.env_file)
    conn = connect_db(config)
    schema = config['PGSCHEMA']
    
    try:
        # Get run_id
        run_id = get_run_id(conn, config, args.run_id)
        
        cur = conn.cursor()
        
        # === RUN METADATA ===
        cur.execute(
            f"SET search_path TO {schema}; "
            f"SELECT run_id, experiment_version, started_at FROM runs WHERE run_id = %s;",
            (run_id,)
        )
        run_row = cur.fetchone()
        if not run_row:
            print(f"ERROR: Run {run_id} not found")
            return 1
        
        run_id, exp_version, started_at = run_row
        
        print_header(f"RUN INSPECTION — run_id={run_id}")
        
        print_section("Run Metadata")
        print(f"  run_id:             {run_id}")
        print(f"  experiment_version: {exp_version}")
        print(f"  started_at:         {format_timestamp(started_at)}")
        
        # === ROW COUNTS ===
        print_section("Per-Table Row Counts (for this run)")
        
        tables = [
            'nodes_static',
            'global_timeseries',
            'cluster_timeseries',
            'events',
            'run_summary',
            'node_final_summary'
        ]
        
        counts = {}
        for table_name in tables:
            cur.execute(
                f"SET search_path TO {schema}; "
                f"SELECT COUNT(*) FROM {table_name} WHERE run_id = %s;",
                (run_id,)
            )
            count = cur.fetchone()[0]
            counts[table_name] = count
            print(f"  {table_name:25s}: {count:6d} rows")
        
        total_rows = sum(counts.values())
        print(f"  {'TOTAL':25s}: {total_rows:6d} rows")
        
        # === NODE SUMMARY ===
        print_section("Node Summary")
        
        cur.execute(
            f"SET search_path TO {schema}; "
            f"SELECT "
            f"  COUNT(*) AS total, "
            f"  COUNT(CASE WHEN role = 'ch' THEN 1 END) AS ch_count, "
            f"  COUNT(CASE WHEN role = 'member' THEN 1 END) AS member_count, "
            f"  COUNT(CASE WHEN final_status = 'normal' THEN 1 END) AS alive_count, "
            f"  COUNT(CASE WHEN final_status != 'normal' THEN 1 END) AS dead_count "
            f"FROM node_final_summary WHERE run_id = %s;",
            (run_id,)
        )
        node_stats = cur.fetchone()
        if node_stats:
            total, ch, member, alive, dead = node_stats
            print(f"  Total nodes:        {total}")
            print(f"  Cluster Heads (ch): {ch}")
            print(f"  Members:            {member}")
            print(f"  Normal status:      {alive}")
            print(f"  Other status:       {dead}")
        
        # === ENERGY SUMMARY ===
        print_section("Energy Summary (At End of Run)")
        
        cur.execute(
            f"SET search_path TO {schema}; "
            f"SELECT "
            f"  COUNT(*) AS node_count, "
            f"  MIN(residual_j)::NUMERIC(10,3) AS min_residual, "
            f"  MAX(residual_j)::NUMERIC(10,3) AS max_residual, "
            f"  AVG(residual_j)::NUMERIC(10,3) AS avg_residual, "
            f"  AVG(consumed_j)::NUMERIC(10,3) AS avg_consumed "
            f"FROM node_final_summary WHERE run_id = %s;",
            (run_id,)
        )
        energy_stats = cur.fetchone()
        if energy_stats:
            node_count, min_r, max_r, avg_r, avg_c = energy_stats
            print(f"  Nodes measured:     {node_count}")
            print(f"  Min residual energy: {min_r} J")
            print(f"  Max residual energy: {max_r} J")
            print(f"  Avg residual energy: {avg_r} J")
            print(f"  Avg consumed energy: {avg_c} J")
        
        # === RECENT EVENTS (TOP 10) ===
        print_section("Recent Events (Latest 10)")
        
        cur.execute(
            f"SET search_path TO {schema}; "
            f"SELECT event_id, sim_time_s, event_type, node_id, cluster_id, severity, message, details "
            f"FROM events WHERE run_id = %s "
            f"ORDER BY sim_time_s DESC LIMIT 10;",
            (run_id,)
        )
        
        events = cur.fetchall()
        if events:
            for i, event in enumerate(events, 1):
                eid, sim_time, etype, nid, cid, severity, message, details = event
                print(f"\n  [{i}] t={sim_time:.2f}s — {etype} (severity: {severity})")
                print(f"       node_id={nid}, cluster_id={cid}")
                print(f"       message: {message}")
                if details:
                    print(f"       details: {details}")
        else:
            print("  (No events recorded)")
        
        # === CLUSTER STATUS (FROM RUN SUMMARY) ===
        print_section("Cluster Status (From Run Summary)")
        
        cur.execute(
            f"SET search_path TO {schema}; "
            f"SELECT final_sim_time_s, raw_tx_cum, agg_tx_cum, agg_rx_cum, "
            f"        failed_chs, recovered_clusters, consumed_j, avg_res_j "
            f"FROM run_summary WHERE run_id = %s;",
            (run_id,)
        )
        
        summary = cur.fetchone()
        if summary:
            final_time, raw_tx, agg_tx, agg_rx, failed_chs, recovered, consumed, avg_res = summary
            print(f"  Final simulation time:      {final_time:.3f} seconds")
            print(f"  Raw packets transmitted:    {raw_tx}")
            print(f"  Aggregated packets TX:      {agg_tx}")
            print(f"  Aggregated packets RX:      {agg_rx}")
            print(f"  CH Failures:                {failed_chs}")
            print(f"  Recoveries:                 {recovered}")
            print(f"  Total energy consumed (J):  {consumed}")
            if avg_res:
                print(f"  Avg residual energy (J):    {avg_res:.3f}")
        
        print_section("End of Inspection")
        print()
        
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
