#!/usr/bin/env python3
"""
export_run_for_matlab.py

Purpose:
  Export one complete WSN Dashboard run from PostgreSQL into MATLAB-friendly
  flat CSV files for analysis and visualization.

Usage:
  python3 export_run_for_matlab.py --env-file config/.env --latest
  python3 export_run_for_matlab.py --env-file config/.env --run-id 2

Output:
  Created folder with CSVs suitable for MATLAB readtable() or csvread()

Files Generated:
  - global_timeseries.csv      (energy and cluster metrics over time)
  - cluster_timeseries.csv     (per-cluster snapshots)
  - events.csv                 (failures, recoveries, role changes)
  - node_final_summary.csv     (residual energy per node at end)
  - run_summary.csv            (run-level metadata)
  - nodes_static.csv           (static node info and positions)

Author: WSN Dashboard Milestone 3
"""

import argparse
import os
import sys
from datetime import datetime
import csv

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
    """
    Get the run_id to export.
    If run_id is None, return the latest run_id.
    """
    cur = conn.cursor()
    schema = config['PGSCHEMA']
    
    try:
        if run_id is None:
            # Get latest run
            cur.execute(f"SET search_path TO {schema}; SELECT MAX(run_id) FROM runs;")
            result = cur.fetchone()
            if result[0] is None:
                print("ERROR: No runs found in database")
                sys.exit(1)
            run_id = result[0]
        else:
            # Verify run_id exists
            cur.execute(f"SET search_path TO {schema}; SELECT run_id FROM runs WHERE run_id = %s;", (run_id,))
            result = cur.fetchone()
            if result is None:
                print(f"ERROR: Run ID {run_id} not found in database")
                sys.exit(1)
        
        return run_id
    finally:
        cur.close()


def export_table_to_csv(conn, config, run_id, table_name, csv_file):
    """
    Export a table (filtered by run_id) to CSV.
    
    Args:
        conn: psycopg2 connection
        config: database config dict
        run_id: the run_id to filter on
        table_name: name of table (no schema prefix)
        csv_file: output file path
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    schema = config['PGSCHEMA']
    
    try:
        # Fetch all rows for this run from this table
        query = f"SET search_path TO {schema}; SELECT * FROM {table_name} WHERE run_id = %s ORDER BY ";
        
        # Add ordering based on table
        if table_name == 'nodes_static':
            query += "node_id;"
        elif table_name == 'global_timeseries':
            query += "sim_time_s;"
        elif table_name == 'cluster_timeseries':
            query += "sim_time_s, cluster_id;"
        elif table_name == 'events':
            query += "sim_time_s, event_id;"
        elif table_name == 'run_summary':
            query += "run_id;"
        elif table_name == 'node_final_summary':
            query += "node_id;"
        else:
            query += "1;"  # Default ordering
        
        cur.execute(query, (run_id,))
        rows = cur.fetchall()
        
        if not rows:
            print(f"  WARNING: No rows found for table {table_name} in run_id {run_id}. Creating empty CSV.")
            rows = []
        
        # Write CSV header and rows
        with open(csv_file, 'w', newline='') as f:
            if rows:
                fieldnames = rows[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
        
        row_count = len(rows)
        print(f"  {table_name:25s} -> {os.path.basename(csv_file):30s} ({row_count:6d} rows)")
        
    finally:
        cur.close()


def export_run_summary(conn, config, run_id, csv_file):
    """
    Export run_summary as a single row CSV.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    schema = config['PGSCHEMA']
    
    try:
        query = f"SET search_path TO {schema}; SELECT * FROM run_summary WHERE run_id = %s;"
        cur.execute(query, (run_id,))
        rows = cur.fetchall()
        
        if not rows:
            print(f"  WARNING: No run_summary found for run_id {run_id}. Creating minimal CSV.")
            rows = []
        
        with open(csv_file, 'w', newline='') as f:
            if rows:
                fieldnames = rows[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
        
        row_count = len(rows)
        print(f"  {'run_summary':25s} -> {os.path.basename(csv_file):30s} ({row_count:6d} rows)")
        
    finally:
        cur.close()


def export_run_metadata(conn, config, run_id, csv_file):
    """
    Export run metadata (runs table) as a single row CSV.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    schema = config['PGSCHEMA']
    
    try:
        query = f"SET search_path TO {schema}; SELECT * FROM runs WHERE run_id = %s;"
        cur.execute(query, (run_id,))
        rows = cur.fetchall()
        
        if not rows:
            print(f"  WARNING: No run metadata found for run_id {run_id}.")
            return
        
        with open(csv_file, 'w', newline='') as f:
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        row_count = len(rows)
        print(f"  {'run_metadata':25s} -> {os.path.basename(csv_file):30s} ({row_count:6d} rows)")
        
    finally:
        cur.close()


def main():
    parser = argparse.ArgumentParser(
        description='Export a WSN Dashboard run from PostgreSQL as MATLAB-friendly CSVs'
    )
    parser.add_argument(
        '--env-file',
        default='config/.env',
        help='Path to .env file with database credentials (default: config/.env)'
    )
    parser.add_argument(
        '--run-id',
        type=int,
        default=None,
        help='Specific run_id to export (default: latest)'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='Export latest run (same as not specifying --run-id)'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Output folder for CSVs (default: run_export_YYYYMMDD_HHMMSS)'
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_env(args.env_file)
    
    # Connect to DB
    conn = connect_db(config)
    
    try:
        # Determine run_id
        run_id = get_run_id(conn, config, args.run_id)
        
        # Create output directory
        if args.output_dir is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            args.output_dir = f'run_export_{timestamp}'
        
        os.makedirs(args.output_dir, exist_ok=True)
        
        print(f"\n[MATLAB Export] Exporting run_id={run_id} to: {os.path.abspath(args.output_dir)}")
        print("-" * 80)
        
        # Export tables
        tables_to_export = [
            ('nodes_static', 'nodes_static.csv'),
            ('global_timeseries', 'global_timeseries.csv'),
            ('cluster_timeseries', 'cluster_timeseries.csv'),
            ('events', 'events.csv'),
            ('node_final_summary', 'node_final_summary.csv'),
        ]
        
        for table_name, csv_name in tables_to_export:
            csv_file = os.path.join(args.output_dir, csv_name)
            export_table_to_csv(conn, config, run_id, table_name, csv_file)
        
        # Export run_summary and run metadata
        export_run_summary(conn, config, run_id, os.path.join(args.output_dir, 'run_summary.csv'))
        export_run_metadata(conn, config, run_id, os.path.join(args.output_dir, 'run_metadata.csv'))
        
        print("-" * 80)
        print(f"[MATLAB Export] SUCCESS")
        print(f"\nAll CSVs ready for MATLAB analysis:")
        print(f"  Location: {os.path.abspath(args.output_dir)}")
        print(f"\nIn MATLAB, load CSVs with:")
        print(f"  T = readtable('nodes_static.csv');")
        print(f"  T = readtable('global_timeseries.csv');")
        print(f"  T = readtable('cluster_timeseries.csv');")
        print(f"  % etc...")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: Export failed: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
