#!/usr/bin/env python3
"""
Milestone 2 importer: file export -> PostgreSQL (remote/local).

Usage example:
  python3 tools/import_run_to_postgres.py \
      --run-dir outputs/run_20260324_123456_123 \
      --env-file tools/db_config_example.env \
      --mode fail
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


psycopg2 = None


def parse_env_file(path: Optional[Path]) -> Dict[str, str]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {path}")

    result: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def build_db_config(args: argparse.Namespace) -> Dict[str, Any]:
    env_file_data = parse_env_file(Path(args.env_file) if args.env_file else None)

    def pick(name: str, default: Optional[str] = None) -> Optional[str]:
        cli = getattr(args, name.lower())
        if cli is not None:
            return cli
        env_name = f"WSN_DB_{name.upper()}"
        if env_name in os.environ:
            return os.environ[env_name]
        if env_name in env_file_data:
            return env_file_data[env_name]
        return default

    cfg = {
        "host": pick("host", "localhost"),
        "port": int(pick("port", "5432")),
        "dbname": pick("dbname", "wsn_sim"),
        "user": pick("user", "postgres"),
        "password": pick("password", ""),
        "schema": pick("schema", "wsn"),
    }

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", cfg["schema"]):
        raise ValueError(f"Invalid schema name: {cfg['schema']}")
    return cfg


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def parse_int(v: Any, nullable: bool = False) -> Optional[int]:
    if v is None:
        return None if nullable else 0
    s = str(v).strip()
    if s == "":
        return None if nullable else 0
    return int(s)


def parse_float(v: Any, nullable: bool = False) -> Optional[float]:
    if v is None:
        return None if nullable else 0.0
    s = str(v).strip()
    if s == "":
        return None if nullable else 0.0
    return float(s)


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
    missing = [name for name, p in files.items() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing export files in {run_dir}: {', '.join(missing)}")
    return files


def assert_external_id(rows: Iterable[Dict[str, str]], key: str, expected: str, table: str) -> None:
    for idx, row in enumerate(rows, start=2):
        actual = (row.get(key) or "").strip()
        if actual != expected:
            raise ValueError(
                f"{table}: external_run_id mismatch at CSV line {idx}. expected={expected}, got={actual}"
            )


def find_existing_run(cur, schema: str, external_run_id: str) -> Optional[int]:
    cur.execute(
        f"SELECT run_id FROM {schema}.runs WHERE experiment_version = %s ORDER BY run_id DESC LIMIT 1",
        (external_run_id,),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def delete_run(cur, schema: str, run_id: int) -> None:
    cur.execute(f"DELETE FROM {schema}.runs WHERE run_id = %s", (run_id,))


def insert_run(cur, schema: str, run_meta: Dict[str, Any]) -> int:
    cur.execute(
        f"""
        INSERT INTO {schema}.runs (
            scenario_name,
            scenario_type,
            sim_time_s,
            node_count,
            cluster_count,
            traffic_interval_s,
            aggregation_interval_s,
            failure_time_s,
            recovery_delay_s,
            recovery_enabled,
            schema_version,
            experiment_version,
            notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING run_id
        """,
        (
            run_meta.get("scenario_name", "cluster-dashboard-m1"),
            run_meta.get("scenario_type", "wsn-self-healing"),
            parse_float(run_meta.get("sim_time_s")),
            parse_int(run_meta.get("node_count")),
            parse_int(run_meta.get("cluster_count")),
            parse_float(run_meta.get("traffic_interval_s")),
            parse_float(run_meta.get("aggregation_interval_s")),
            parse_float(run_meta.get("failure_time_s"), nullable=True),
            parse_float(run_meta.get("recovery_delay_s"), nullable=True),
            parse_bool(run_meta.get("recovery_enabled", False)),
            run_meta.get("schema_version", "m1_v1"),
            run_meta.get("external_run_id"),
            f"Imported from file export. source_file={run_meta.get('source_file', 'unknown')}",
        ),
    )
    return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Import one exported ns-3 run into PostgreSQL")
    parser.add_argument("--run-dir", required=True, help="Path to outputs/run_<id> directory")
    parser.add_argument("--mode", choices=["fail", "skip", "replace"], default="fail")
    parser.add_argument("--env-file", help="Optional .env style file for DB connection")

    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--dbname")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--schema")

    args = parser.parse_args()

    global psycopg2
    try:
        import psycopg2 as _psycopg2
        import psycopg2.extras as _psycopg2_extras
        _ = _psycopg2_extras
        psycopg2 = _psycopg2
    except Exception:
        print("ERROR: psycopg2 is required. Install with: pip install psycopg2-binary", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir)
    if not run_dir.exists() or not run_dir.is_dir():
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 2

    files = required_files(run_dir)

    run_meta = load_json(files["run_meta"])
    run_summary = load_json(files["run_summary"])
    nodes_static = load_csv(files["nodes_static"])
    global_timeseries = load_csv(files["global_timeseries"])
    cluster_timeseries = load_csv(files["cluster_timeseries"])
    events = load_csv(files["events"])
    node_final_summary = load_csv(files["node_final_summary"])

    external_run_id = run_meta.get("external_run_id")
    if not external_run_id:
        print("ERROR: run_meta.json missing external_run_id", file=sys.stderr)
        return 2

    assert_external_id(nodes_static, "external_run_id", external_run_id, "nodes_static")
    assert_external_id(global_timeseries, "external_run_id", external_run_id, "global_timeseries")
    assert_external_id(cluster_timeseries, "external_run_id", external_run_id, "cluster_timeseries")
    assert_external_id(events, "external_run_id", external_run_id, "events")
    assert_external_id(node_final_summary, "external_run_id", external_run_id, "node_final_summary")
    if run_summary.get("external_run_id") != external_run_id:
        raise ValueError("run_summary.json external_run_id mismatch")

    cfg = build_db_config(args)
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
    )

    inserted_counts: Dict[str, int] = {}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {cfg['schema']}, public")

                existing = find_existing_run(cur, cfg["schema"], external_run_id)
                if existing is not None:
                    if args.mode == "skip":
                        print(f"SKIP: run already imported (run_id={existing}, external_run_id={external_run_id})")
                        return 0
                    if args.mode == "fail":
                        raise RuntimeError(
                            f"Duplicate run detected. run_id={existing}, external_run_id={external_run_id}. "
                            f"Use --mode skip or --mode replace."
                        )
                    if args.mode == "replace":
                        delete_run(cur, cfg["schema"], existing)

                run_id = insert_run(cur, cfg["schema"], run_meta)
                inserted_counts["runs"] = 1

                cur.executemany(
                    f"""
                    INSERT INTO {cfg['schema']}.nodes_static (
                        run_id,node_id,role,original_cluster_id,original_ch_id,initial_energy_j,x,y,z
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            run_id,
                            parse_int(r["node_id"]),
                            r["role"],
                            parse_int(r.get("original_cluster_id"), nullable=True),
                            parse_int(r.get("original_ch_id"), nullable=True),
                            parse_float(r["initial_energy_j"]),
                            parse_float(r["x"]),
                            parse_float(r["y"]),
                            parse_float(r.get("z", 0.0)),
                        )
                        for r in nodes_static
                    ],
                )
                inserted_counts["nodes_static"] = len(nodes_static)

                cur.executemany(
                    f"""
                    INSERT INTO {cfg['schema']}.global_timeseries (
                        run_id,sim_time_s,raw_tx_cum,raw_rx_cum,agg_tx_cum,agg_rx_cum,
                        direct_agg_rx_cum,relayed_agg_rx_cum,relay_fwd_cum,
                        avg_res_j,min_res_j,consumed_j,low_nodes,failed_chs,recovered_clusters,pending_raw_total
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            run_id,
                            parse_float(r["sim_time"]),
                            parse_int(r["raw_tx_cum"]),
                            parse_int(r["raw_rx_cum"]),
                            parse_int(r["agg_tx_cum"]),
                            parse_int(r["agg_rx_cum"]),
                            parse_int(r["direct_agg_rx_cum"]),
                            parse_int(r["relayed_agg_rx_cum"]),
                            parse_int(r["relay_fwd_cum"]),
                            parse_float(r["avg_res_j"]),
                            parse_float(r["min_res_j"]),
                            parse_float(r["consumed_j"]),
                            parse_int(r["low_nodes"]),
                            parse_int(r["failed_chs"]),
                            parse_int(r["recovered_clusters"]),
                            parse_int(r["pending_raw_total"]),
                        )
                        for r in global_timeseries
                    ],
                )
                inserted_counts["global_timeseries"] = len(global_timeseries)

                cur.executemany(
                    f"""
                    INSERT INTO {cfg['schema']}.cluster_timeseries (
                        run_id,sim_time_s,cluster_id,original_ch_id,current_ch_id,status,mode,next_hop,
                        members_count,raw_rx_cum,pending_raw,agg_tx_cum,relay_fwd_cum,
                        ch_res_j,avg_mem_res_j,cluster_consumed_j
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            run_id,
                            parse_float(r["sim_time"]),
                            parse_int(r["cluster_id"]),
                            parse_int(r["original_ch_id"]),
                            parse_int(r["current_ch_id"]),
                            r["status"],
                            r["mode"],
                            r["next_hop"],
                            parse_int(r["members_count"]),
                            parse_int(r["raw_rx_cum"]),
                            parse_int(r["pending_raw"]),
                            parse_int(r["agg_tx_cum"]),
                            parse_int(r["relay_fwd_cum"]),
                            parse_float(r["ch_res_j"]),
                            parse_float(r["avg_mem_res_j"]),
                            parse_float(r["cluster_consumed_j"]),
                        )
                        for r in cluster_timeseries
                    ],
                )
                inserted_counts["cluster_timeseries"] = len(cluster_timeseries)

                cur.executemany(
                    f"""
                    INSERT INTO {cfg['schema']}.events (
                        run_id,sim_time_s,event_type,severity,cluster_id,node_id,message,details
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            run_id,
                            parse_float(r["sim_time"]),
                            r["event_type"],
                            r["severity"],
                            parse_int(r.get("cluster_id"), nullable=True),
                            parse_int(r.get("node_id"), nullable=True),
                            r["message"],
                            psycopg2.extras.Json(json.loads(r["details_json"])) if r.get("details_json") else None,
                        )
                        for r in events
                    ],
                )
                inserted_counts["events"] = len(events)

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
                        parse_float(run_summary["final_sim_time"]),
                        parse_int(run_summary["raw_tx_cum"]),
                        parse_int(run_summary["raw_rx_cum"]),
                        parse_int(run_summary["agg_tx_cum"]),
                        parse_int(run_summary["agg_rx_cum"]),
                        parse_int(run_summary["direct_agg_rx_cum"]),
                        parse_int(run_summary["relayed_agg_rx_cum"]),
                        parse_int(run_summary["relay_fwd_cum"]),
                        parse_int(run_summary["failed_chs"]),
                        parse_int(run_summary["recovered_clusters"]),
                        parse_float(run_summary["avg_res_j"]),
                        parse_float(run_summary["min_res_j"]),
                        parse_float(run_summary["consumed_j"]),
                        parse_int(run_summary["low_nodes"]),
                        parse_int(run_summary["pending_raw_total"]),
                    ),
                )
                inserted_counts["run_summary"] = 1

                cur.executemany(
                    f"""
                    INSERT INTO {cfg['schema']}.node_final_summary (
                        run_id,node_id,role,cluster_id,residual_j,consumed_j,final_status
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [
                        (
                            run_id,
                            parse_int(r["node_id"]),
                            r["role"],
                            parse_int(r.get("cluster_id"), nullable=True),
                            parse_float(r["residual_j"]),
                            parse_float(r["consumed_j"]),
                            r["final_status"],
                        )
                        for r in node_final_summary
                    ],
                )
                inserted_counts["node_final_summary"] = len(node_final_summary)

        print("Import successful")
        print(f"  external_run_id: {external_run_id}")
        print(f"  run_id:          {run_id}")
        for k in [
            "runs",
            "nodes_static",
            "global_timeseries",
            "cluster_timeseries",
            "events",
            "run_summary",
            "node_final_summary",
        ]:
            print(f"  {k:20s} {inserted_counts.get(k, 0)}")
        return 0

    except Exception as exc:
        conn.rollback()
        print(f"ERROR: import failed and rolled back: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
