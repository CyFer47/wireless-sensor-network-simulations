#!/usr/bin/env python3
"""Milestone 2 importer: ns-3 exported files -> local PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def load_dotenv(dotenv_path: Optional[Path]) -> None:
    if dotenv_path is None:
        return
    if not dotenv_path.exists():
        raise FileNotFoundError(f".env file not found: {dotenv_path}")

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def pg_config(schema_override: Optional[str]) -> Dict[str, Any]:
    schema = (schema_override or os.environ.get("PGSCHEMA", "wsn")).strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", schema):
        raise ValueError(f"Invalid PGSCHEMA value: {schema}")

    return {
        "host": require_env("PGHOST"),
        "port": int(require_env("PGPORT")),
        "dbname": require_env("PGDATABASE"),
        "user": require_env("PGUSER"),
        "password": require_env("PGPASSWORD"),
        "schema": schema,
    }


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def f_int(v: Any, nullable: bool = False) -> Optional[int]:
    s = "" if v is None else str(v).strip()
    if s == "":
        return None if nullable else 0
    return int(s)


def f_float(v: Any, nullable: bool = False) -> Optional[float]:
    s = "" if v is None else str(v).strip()
    if s == "":
        return None if nullable else 0.0
    return float(s)


def f_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def required_files(run_dir: Path) -> Dict[str, Path]:
    files = {
        "run_meta": run_dir / "run_meta.json",
        "nodes_static": run_dir / "nodes_static.csv",
        "global_timeseries": run_dir / "global_timeseries.csv",
        "cluster_timeseries": run_dir / "cluster_timeseries.csv",
        "events": run_dir / "events.csv",
        "run_summary": run_dir / "run_summary.json",
        "node_final_summary": run_dir / "node_final_summary.csv",
    }
    missing = [k for k, p in files.items() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required files: {', '.join(missing)}")
    return files


def assert_external_id(rows: Iterable[Dict[str, str]], expected: str, table: str) -> None:
    for i, row in enumerate(rows, start=2):
        got = (row.get("external_run_id") or "").strip()
        if got != expected:
            raise ValueError(f"{table} external_run_id mismatch at line {i}: expected {expected}, got {got}")


def check_tables(cur, schema: str) -> None:
    expected = {
        "runs",
        "nodes_static",
        "global_timeseries",
        "cluster_timeseries",
        "events",
        "run_summary",
        "node_final_summary",
    }
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
        raise RuntimeError(f"Schema check failed. Missing tables in {schema}: {', '.join(missing)}")


def find_existing_run_id(cur, schema: str, external_run_id: str) -> Optional[int]:
    cur.execute(
        f"SELECT run_id FROM {schema}.runs WHERE experiment_version = %s ORDER BY run_id DESC LIMIT 1",
        (external_run_id,),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def insert_run(cur, schema: str, meta: Dict[str, Any]) -> int:
    """Insert run with M5 metadata support (architecture, scenario axes, topology lineage).
    
    Backward compatible: M3/M4 exports with architecture+scenario axes use new columns;
    older exports use defaults (architecture='A', all axes NULL).
    """
    cur.execute(
        f"""
        INSERT INTO {schema}.runs (
            scenario_name, scenario_type, sim_time_s,
            node_count, cluster_count,
            traffic_interval_s, aggregation_interval_s,
            failure_time_s, recovery_delay_s, recovery_enabled,
            schema_version, experiment_version, notes,
            architecture, routing_engine,
            failure_family, healing_id, variant, load, scale, seed,
            map_id, map_signature, run_status, external_run_id_new
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING run_id
        """,
        (
            meta.get("scenario_name", "cluster-dashboard-m1"),
            meta.get("scenario_type", "wsn-self-healing"),
            f_float(meta.get("sim_time_s")),
            f_int(meta.get("node_count")),
            f_int(meta.get("cluster_count")),
            f_float(meta.get("traffic_interval_s")),
            f_float(meta.get("aggregation_interval_s")),
            f_float(meta.get("failure_time_s"), nullable=True),
            f_float(meta.get("recovery_delay_s"), nullable=True),
            f_bool(meta.get("recovery_enabled", False)),
            meta.get("schema_version", "m1_v1"),
            meta.get("external_run_id"),
            f"imported_from={meta.get('source_file', 'export')}",
            # M5 columns: architecture and scenario axes (backward compatible, default to A)
            meta.get("architecture", "A"),  # new in M4: explicit A or B
            meta.get("routing_engine", "baseline"),  # new in M4: baseline or bsbssp_v1_approx
            # Scenario axes (optional fields from run_spec)
            meta.get("failure_family"),  # e.g., F0, F1, F2, F3, F4
            meta.get("healing_id"),      # e.g., H0, H1, H2, H3, H4
            meta.get("variant"),         # e.g., V1, V2, V3
            meta.get("load"),            # e.g., L1, L2, L3
            meta.get("scale"),           # e.g., S1, S2, S3, S4, S5, S6
            f_int(meta.get("seed"), nullable=True),  # new in M4: random seed
            # Topology lineage (optional fields from topology map)
            meta.get("map_id"),          # new in M4: topology map identifier
            meta.get("map_signature"),   # new in M4: SHA256 of topology package
            "complete",                  # default run_status; importer validates 7-file completeness
            meta.get("external_run_id"),  # optional: stable external ID anchor for future
        ),
    )
    return int(cur.fetchone()[0])


def do_import(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        print(f"ERROR: run-dir not found: {run_dir}", file=sys.stderr)
        return 2

    files = required_files(run_dir)
    run_meta = load_json(files["run_meta"])
    run_summary = load_json(files["run_summary"])
    nodes_static = load_csv(files["nodes_static"])
    global_ts = load_csv(files["global_timeseries"])
    cluster_ts = load_csv(files["cluster_timeseries"])
    events = load_csv(files["events"])
    node_final = load_csv(files["node_final_summary"])

    ext_run_id = run_meta.get("external_run_id")
    if not ext_run_id:
        print("ERROR: run_meta.json missing external_run_id", file=sys.stderr)
        return 2

    assert_external_id(nodes_static, ext_run_id, "nodes_static")
    assert_external_id(global_ts, ext_run_id, "global_timeseries")
    assert_external_id(cluster_ts, ext_run_id, "cluster_timeseries")
    assert_external_id(events, ext_run_id, "events")
    assert_external_id(node_final, ext_run_id, "node_final_summary")
    if run_summary.get("external_run_id") != ext_run_id:
        raise ValueError("run_summary external_run_id mismatch")

    cfg = pg_config(args.schema)

    if args.dry_run:
        print("DRY RUN: validation only, no DB writes")
        print(f"  run_dir={run_dir}")
        print(f"  external_run_id={ext_run_id}")
        print(f"  nodes_static={len(nodes_static)}")
        print(f"  global_timeseries={len(global_ts)}")
        print(f"  cluster_timeseries={len(cluster_ts)}")
        print(f"  events={len(events)}")
        print(f"  node_final_summary={len(node_final)}")
        return 0

    try:
        import psycopg2
        from psycopg2.extras import Json, execute_values
    except Exception:
        print("ERROR: Install dependency first: pip install psycopg2-binary", file=sys.stderr)
        return 2

    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        connect_timeout=8,
    )

    inserted = {}
    run_id = None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {cfg['schema']}, public")
                check_tables(cur, cfg["schema"])

                existing = find_existing_run_id(cur, cfg["schema"], ext_run_id)
                if existing is not None:
                    if args.mode == "skip":
                        print(f"SKIP: run already imported. run_id={existing}, external_run_id={ext_run_id}")
                        return 0
                    if args.mode == "fail":
                        raise RuntimeError(
                            f"Duplicate run external_run_id={ext_run_id} (run_id={existing}). Use --mode skip|replace"
                        )
                    cur.execute(f"DELETE FROM {cfg['schema']}.runs WHERE run_id=%s", (existing,))

                run_id = insert_run(cur, cfg["schema"], run_meta)
                inserted["runs"] = 1

                execute_values(
                    cur,
                    f"""
                    INSERT INTO {cfg['schema']}.nodes_static (
                        run_id,node_id,role,original_cluster_id,original_ch_id,initial_energy_j,x,y,z
                    ) VALUES %s
                    """,
                    [
                        (
                            run_id,
                            f_int(r["node_id"]),
                            r["role"],
                            f_int(r.get("original_cluster_id"), nullable=True),
                            f_int(r.get("original_ch_id"), nullable=True),
                            f_float(r["initial_energy_j"]),
                            f_float(r["x"]),
                            f_float(r["y"]),
                            f_float(r.get("z", 0)),
                        )
                        for r in nodes_static
                    ],
                    page_size=2000,
                )
                inserted["nodes_static"] = len(nodes_static)

                execute_values(
                    cur,
                    f"""
                    INSERT INTO {cfg['schema']}.global_timeseries (
                        run_id,sim_time_s,raw_tx_cum,raw_rx_cum,agg_tx_cum,agg_rx_cum,
                        direct_agg_rx_cum,relayed_agg_rx_cum,relay_fwd_cum,
                        avg_res_j,min_res_j,consumed_j,low_nodes,failed_chs,recovered_clusters,pending_raw_total
                    ) VALUES %s
                    """,
                    [
                        (
                            run_id,
                            f_float(r["sim_time"]),
                            f_int(r["raw_tx_cum"]),
                            f_int(r["raw_rx_cum"]),
                            f_int(r["agg_tx_cum"]),
                            f_int(r["agg_rx_cum"]),
                            f_int(r["direct_agg_rx_cum"]),
                            f_int(r["relayed_agg_rx_cum"]),
                            f_int(r["relay_fwd_cum"]),
                            f_float(r["avg_res_j"]),
                            f_float(r["min_res_j"]),
                            f_float(r["consumed_j"]),
                            f_int(r["low_nodes"]),
                            f_int(r["failed_chs"]),
                            f_int(r["recovered_clusters"]),
                            f_int(r["pending_raw_total"]),
                        )
                        for r in global_ts
                    ],
                    page_size=5000,
                )
                inserted["global_timeseries"] = len(global_ts)

                execute_values(
                    cur,
                    f"""
                    INSERT INTO {cfg['schema']}.cluster_timeseries (
                        run_id,sim_time_s,cluster_id,original_ch_id,current_ch_id,status,mode,next_hop,
                        members_count,raw_rx_cum,pending_raw,agg_tx_cum,relay_fwd_cum,
                        ch_res_j,avg_mem_res_j,cluster_consumed_j
                    ) VALUES %s
                    """,
                    [
                        (
                            run_id,
                            f_float(r["sim_time"]),
                            f_int(r["cluster_id"]),
                            f_int(r["original_ch_id"]),
                            f_int(r["current_ch_id"]),
                            r["status"],
                            r["mode"],
                            r["next_hop"],
                            f_int(r["members_count"]),
                            f_int(r["raw_rx_cum"]),
                            f_int(r["pending_raw"]),
                            f_int(r["agg_tx_cum"]),
                            f_int(r["relay_fwd_cum"]),
                            f_float(r["ch_res_j"]),
                            f_float(r["avg_mem_res_j"]),
                            f_float(r["cluster_consumed_j"]),
                        )
                        for r in cluster_ts
                    ],
                    page_size=5000,
                )
                inserted["cluster_timeseries"] = len(cluster_ts)

                execute_values(
                    cur,
                    f"""
                    INSERT INTO {cfg['schema']}.events (
                        run_id,sim_time_s,event_type,severity,cluster_id,node_id,message,details
                    ) VALUES %s
                    """,
                    [
                        (
                            run_id,
                            f_float(r["sim_time"]),
                            r["event_type"],
                            r["severity"],
                            f_int(r.get("cluster_id"), nullable=True),
                            f_int(r.get("node_id"), nullable=True),
                            r["message"],
                            Json(json.loads(r["details_json"])) if (r.get("details_json") or "").strip() else Json({}),
                        )
                        for r in events
                    ],
                    page_size=5000,
                )
                inserted["events"] = len(events)

                cur.execute(
                    f"""
                    INSERT INTO {cfg['schema']}.run_summary (
                        run_id,final_sim_time_s,raw_tx_cum,raw_rx_cum,agg_tx_cum,agg_rx_cum,
                        direct_agg_rx_cum,relayed_agg_rx_cum,relay_fwd_cum,
                        failed_chs,recovered_clusters,avg_res_j,min_res_j,consumed_j,low_nodes,pending_raw_total
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        run_id,
                        f_float(run_summary["final_sim_time"]),
                        f_int(run_summary["raw_tx_cum"]),
                        f_int(run_summary["raw_rx_cum"]),
                        f_int(run_summary["agg_tx_cum"]),
                        f_int(run_summary["agg_rx_cum"]),
                        f_int(run_summary["direct_agg_rx_cum"]),
                        f_int(run_summary["relayed_agg_rx_cum"]),
                        f_int(run_summary["relay_fwd_cum"]),
                        f_int(run_summary["failed_chs"]),
                        f_int(run_summary["recovered_clusters"]),
                        f_float(run_summary["avg_res_j"]),
                        f_float(run_summary["min_res_j"]),
                        f_float(run_summary["consumed_j"]),
                        f_int(run_summary["low_nodes"]),
                        f_int(run_summary["pending_raw_total"]),
                    ),
                )
                inserted["run_summary"] = 1

                execute_values(
                    cur,
                    f"""
                    INSERT INTO {cfg['schema']}.node_final_summary (
                        run_id,node_id,role,cluster_id,residual_j,consumed_j,final_status
                    ) VALUES %s
                    """,
                    [
                        (
                            run_id,
                            f_int(r["node_id"]),
                            r["role"],
                            f_int(r.get("cluster_id"), nullable=True),
                            f_float(r["residual_j"]),
                            f_float(r["consumed_j"]),
                            r["final_status"],
                        )
                        for r in node_final
                    ],
                    page_size=5000,
                )
                inserted["node_final_summary"] = len(node_final)

        print("Import successful")
        print(f"  external_run_id: {ext_run_id}")
        print(f"  run_id:          {run_id}")
        for key in [
            "runs",
            "nodes_static",
            "global_timeseries",
            "cluster_timeseries",
            "events",
            "run_summary",
            "node_final_summary",
        ]:
            print(f"  {key:20s} {inserted.get(key, 0)}")
        return 0

    except Exception as exc:
        conn.rollback()
        print(f"ERROR: import failed and rolled back: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import one exported run into remote PostgreSQL")
    parser.add_argument("--run-dir", required=True, help="Path to run folder")
    parser.add_argument("--env-file", default="config/.env", help="Path to .env file")
    parser.add_argument("--schema", help="Override PGSCHEMA")
    parser.add_argument("--mode", choices=["fail", "skip", "replace"], default="fail")
    parser.add_argument("--dry-run", action="store_true", help="Validate files and print counts only")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"WARN: .env file not found at {env_path}, using current environment", file=sys.stderr)

    return do_import(args)


if __name__ == "__main__":
    raise SystemExit(main())
