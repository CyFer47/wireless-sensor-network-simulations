#!/usr/bin/env python3
"""Connectivity + schema verification for local PostgreSQL."""

from __future__ import annotations

import argparse
import os
import re
import socket
import sys
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f".env file not found: {path}")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Test local PostgreSQL connectivity and schema")
    parser.add_argument("--env-file", default="config/.env", help="Path to .env")
    args = parser.parse_args()

    env_file = Path(args.env_file)
    if env_file.exists():
        load_dotenv(env_file)
    else:
        print(f"WARN: .env file not found at {env_file}, falling back to process env")

    host = get_required("PGHOST")
    port = int(get_required("PGPORT"))
    dbname = get_required("PGDATABASE")
    user = get_required("PGUSER")
    password = get_required("PGPASSWORD")
    schema = os.environ.get("PGSCHEMA", "wsn").strip()

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", schema):
        print(f"ERROR: invalid PGSCHEMA: {schema}", file=sys.stderr)
        return 2

    print(f"[1/3] TCP reachability: {host}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((host, port))
        print("  OK: TCP port reachable")
    except Exception as exc:
        print(f"  FAIL: cannot reach {host}:{port} -> {exc}", file=sys.stderr)
        return 1
    finally:
        sock.close()

    print("[2/3] PostgreSQL authentication")
    try:
        import psycopg2
    except Exception:
        print("  FAIL: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        return 2

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=8,
        )
    except Exception as exc:
        print(f"  FAIL: DB login failed -> {exc}", file=sys.stderr)
        return 1

    print("  OK: DB authentication succeeded")

    print(f"[3/3] Schema/table checks in schema '{schema}'")
    expected = {
        "runs",
        "nodes_static",
        "global_timeseries",
        "cluster_timeseries",
        "events",
        "run_summary",
        "node_final_summary",
    }
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    """,
                    (schema,),
                )
                present = {r[0] for r in cur.fetchall()}
                missing = sorted(expected - present)
                if missing:
                    print(f"  FAIL: missing tables: {', '.join(missing)}", file=sys.stderr)
                    return 1
                print("  OK: all required Milestone 1 tables exist")
    finally:
        conn.close()

    print("Connectivity test PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
