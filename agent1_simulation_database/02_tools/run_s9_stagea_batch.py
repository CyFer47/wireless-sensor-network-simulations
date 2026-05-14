#!/usr/bin/env python3
"""Run Final Scale5000 S9 Stage A (12-run smoke test for S9=4000 nodes)
DB-aware: pre-scan DB for existing complete rows and reuse them.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_ENV_FILE = Path("/home/cyfer/FYP/WSN Dashboard Milestone V2/web-monitor/backend/config/.env")
STATE_DEFAULT = REPO_ROOT / "outputs" / "s9_stagea_state.json"
QUARANTINE_DEFAULT = REPO_ROOT / "outputs" / "s9_stagea_quarantine.json"
LOG_DEFAULT = REPO_ROOT / "outputs" / "s9_stagea_batch.log"
SPEC_ROOT_DEFAULT = REPO_ROOT / "runspecs" / "generated" / "s9_stagea"
OUTPUT_ROOT_DEFAULT = REPO_ROOT / "outputs"

@dataclass(frozen=True)
class S9Rule:
    node_count: int
    cluster_count: int
    bs: int
    area_x: int
    area_y: int
    sim_time_s: float

S9_RULE = S9Rule(node_count=4000, cluster_count=160, bs=5, area_x=1020, area_y=1020, sim_time_s=250.0)

S9_MATRIX: List[Dict[str, object]] = []

def build_matrix():
    # Group 1 Baseline controls
    rows = [
        ("F0", "H0", "A", "L1", 1),
        ("F0", "H0", "A", "L2", 1),
        ("F0", "H0", "B", "L1", 1),
        ("F0", "H0", "B", "L2", 1),
        # Group 2 Common healing pair
        ("F1", "H1", "A", "L1", 1),
        ("F1", "H1", "A", "L2", 1),
        ("F1", "H1", "B", "L1", 1),
        ("F1", "H1", "B", "L2", 1),
        # Group 3 Post-healing stress pair
        ("F4", "H4", "A", "L1", 1),
        ("F4", "H4", "A", "L2", 1),
        ("F4", "H4", "B", "L1", 1),
        ("F4", "H4", "B", "L2", 1),
    ]
    for family, healing, arch, load, seed in rows:
        run_spec_id = f"{family}_{healing}_{arch}_S9_{load}_seed{seed:02d}"
        variant = "V1" if family == "F0" and healing == "H0" else "V3"
        S9_MATRIX.append({
            "run_spec_id": run_spec_id,
            "architecture": arch,
            "failure_family": family,
            "healing_id": healing,
            "variant": variant,
            "load": load,
            "seed": seed,
        })

build_matrix()

def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True)+"\n", encoding="utf-8")

def append_log(log_file: Path, text: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")

def run_checked(cmd: List[str], cwd: Path | None = None, log_file: Path | None = None) -> int:
    if log_file is not None:
        with log_file.open("a", encoding="utf-8") as f:
            proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=f, stderr=f)
            return proc.returncode
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None).returncode

def spec_for_row(row: Dict[str, object]) -> dict:
    seed = int(row['seed'])
    healing = row['healing_id']
    recovery_enabled = healing != 'H0'
    recovery_profile = 'm7_profile' if recovery_enabled and row['architecture']=='B' else 'none'
    # standard timing values for Stage A smoke tests
    timing = {
        "sim_time_s": S9_RULE.sim_time_s,
        "traffic_interval_s": 1.0,
        "aggregation_interval_s": 30.0,
        "dashboard_interval_s": 10.0,
    }

    # failure / recovery timing
    if row['variant'] == 'V1':
        timing.update({"failure_time_s": None, "recovery_delay_s": None})
    else:
        timing.update({"failure_time_s": 10.0, "recovery_delay_s": 12.0})

    exec_cfg = {
        "sim_source": "ns3",
        "enable_run_export": True,
        "export_root_dir": str(OUTPUT_ROOT_DEFAULT),
        "ns3_root_hint": str(Path('/home/cyfer/ns-allinone-3.42/ns-3.42')),
    }

    return {
        "schema_version": "runspec_v1",
        "run_spec_id": row['run_spec_id'],
        "description": f"Final Scale5000 Stage A S9 {row['architecture']} {row['failure_family']}/{healing} {row['load']} seed{seed:02d}",
        "phase": "phase1",
        "architecture": row['architecture'],
        "runnable": True,
        "variant": row['variant'],
        "failure_family": row['failure_family'],
        "healing_id": healing,
        "load": row['load'],
        "scale": "S9",
        "seed": seed,
        "topology": {"node_count": S9_RULE.node_count, "cluster_count": S9_RULE.cluster_count, "bs": S9_RULE.bs, "area": [S9_RULE.area_x, S9_RULE.area_y]},
        "timing": timing,
        "failure_injection": {"enabled": True if row['failure_family'] != 'F0' else False},
        "recovery": {"enabled": recovery_enabled, "profile": recovery_profile},
        "execution": exec_cfg,
    }

def ensure_spec(row: Dict[str, object], spec_root: Path) -> Path:
    spec_root.mkdir(parents=True, exist_ok=True)
    spec_path = spec_root / f"{row['run_spec_id']}.json"
    spec = spec_for_row(row)
    write_json(spec_path, spec)
    return spec_path

def db_connect(cfg_file: Path):
    env = {}
    for line in cfg_file.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v = line.split('=',1)
        env[k.strip()]=v.strip().strip('"').strip("'")
    import psycopg2
    conn = psycopg2.connect(host=env['PGHOST'],port=int(env['PGPORT']),database=env['PGDATABASE'],user=env['PGUSER'],password=env['PGPASSWORD'])
    conn.autocommit=False
    return conn

def find_existing_complete(cur, external_run_id: str):
    cur.execute(
        "SELECT run_id, run_status, map_id, map_signature FROM wsn.runs WHERE experiment_version=%s AND run_status='complete' ORDER BY run_id DESC LIMIT 1",
        (external_run_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {"run_id": int(row['run_id']), 'run_status': row['run_status'], 'map_id': row['map_id'], 'map_signature': row['map_signature']}

def get_s9_map_dir(seed:int)->Path:
    p = REPO_ROOT / 'maps' / 'examples' / f'map_S9_seed{seed:02d}'
    if not p.exists():
        raise FileNotFoundError(f"Map package missing: {p}")
    return p

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--ns3-root', default='/home/cyfer/ns-allinone-3.42/ns-3.42', help='Path to ns-3 root')
    args = parser.parse_args()

    state_file = STATE_DEFAULT
    quarantine_file = QUARANTINE_DEFAULT
    log_file = LOG_DEFAULT
    spec_root = SPEC_ROOT_DEFAULT
    output_root = OUTPUT_ROOT_DEFAULT

    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    quarantine = json.loads(quarantine_file.read_text()) if quarantine_file.exists() else []

    append_log(log_file, f"[S9A] batch_start {now_utc()} total_runs={len(S9_MATRIX)}")
    if args.dry_run:
        append_log(log_file, "[S9A] dry-run; no simulations launched")

    conn = db_connect(DB_ENV_FILE)
    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET search_path TO wsn, public")
            # pre-scan
            for idx,row in enumerate(S9_MATRIX, start=1):
                spec_id = row['run_spec_id']
                existing = find_existing_complete(cur, spec_id)
                if existing:
                    state[spec_id] = {"status":"ok","run_id":existing['run_id'],"map_id":existing['map_id'],"map_signature":existing['map_signature'],"source":"reused_existing_complete","at":now_utc(),'index':idx}
            write_json(state_file, state)

            if args.dry_run:
                append_log(log_file, "[S9A] dry-run complete")
                return 0

            for idx,row in enumerate(S9_MATRIX, start=1):
                spec_id = row['run_spec_id']
                if state.get(spec_id,{}).get('status')=='ok':
                    append_log(log_file, f"[S9A][{idx}/{len(S9_MATRIX)}] SKIP {spec_id} (already complete)")
                    continue
                append_log(log_file, f"[S9A][{idx}/{len(S9_MATRIX)}] START {spec_id}")
                existing = find_existing_complete(cur, spec_id)
                if existing:
                    state[spec_id] = {"status":"ok","run_id":existing['run_id'],"map_id":existing['map_id'],"map_signature":existing['map_signature'],"source":"reused_existing_complete_prelaunch","at":now_utc(),'index':idx}
                    write_json(state_file, state)
                    append_log(log_file, f"[S9A][{idx}/{len(S9_MATRIX)}] SKIP {spec_id} (complete in DB)")
                    continue
                try:
                    spec_path = ensure_spec(row, spec_root)
                    rc = run_checked([sys.executable, str(REPO_ROOT/'tools'/'validate_runspec.py'), str(spec_path)], cwd=REPO_ROOT, log_file=log_file)
                    if rc!=0:
                        raise RuntimeError('spec validation failed')
                    seed = row['seed']
                    map_dir = get_s9_map_dir(seed)
                    manifest = json.loads((map_dir/'manifest.json').read_text())
                    expected_nodes = S9_RULE.node_count
                    # manifest schema v2 stores counts.node_count
                    manifest_node_count = None
                    if isinstance(manifest.get('counts'), dict):
                        manifest_node_count = manifest['counts'].get('node_count')
                    if manifest_node_count is None:
                        manifest_node_count = manifest.get('nodes')
                    if manifest_node_count != expected_nodes:
                        raise RuntimeError(f'map node count mismatch (manifest={manifest_node_count} expected={expected_nodes})')
                    # run simulation
                    rc = run_checked([sys.executable, str(REPO_ROOT/'tools'/'run_from_spec.py'), '--spec', str(spec_path), '--map', str(map_dir), '--ns3-root', args.ns3_root, '--output-root', str(output_root)], cwd=REPO_ROOT, log_file=log_file)
                    if rc!=0:
                        raise RuntimeError(f'simulation failed rc={rc}')
                    # Find the export directory (run_from_spec.py adds timestamp)
                    import glob
                    matching_dirs = sorted(glob.glob(str(output_root / f"run_{spec_id}_*")), reverse=True)
                    if not matching_dirs:
                        raise RuntimeError(f'missing export dir: no match for run_{spec_id}_*')
                    export_dir = Path(matching_dirs[0])
                    # import
                    rc = run_checked([sys.executable, str(REPO_ROOT/'importer'/'import_run_to_postgres.py'), '--run-dir', str(export_dir), '--env-file', str(DB_ENV_FILE), '--schema', 'wsn', '--mode', 'replace'], cwd=REPO_ROOT, log_file=log_file)
                    if rc!=0:
                        raise RuntimeError(f'import failed rc={rc}')
                    # Query for the newly imported run (uses LIKE since importer adds timestamp to experiment_version)
                    cur.execute('SELECT run_id, map_id, map_signature FROM wsn.runs WHERE experiment_version LIKE %s AND run_status = %s ORDER BY run_id DESC LIMIT 1', (f'{spec_id}_%','complete'))
                    row_db = cur.fetchone()
                    if not row_db:
                        raise RuntimeError('db verification failed after import')
                    state[spec_id] = {"status":"ok","run_id":int(row_db['run_id']),"map_id":row_db['map_id'],"map_signature":row_db['map_signature'],"at":now_utc(),'index':idx}
                    write_json(state_file, state)
                    append_log(log_file, f"[S9A][{idx}/{len(S9_MATRIX)}] OK {spec_id} run_id={row_db['run_id']}")
                except Exception as exc:
                    state[spec_id] = {"status":"failed","reason":str(exc),'index':idx,'at':now_utc()}
                    quarantine.append({"run_spec_id":spec_id,"reason":str(exc),'index':idx,'at':now_utc()})
                    write_json(state_file, state)
                    write_json(quarantine_file, quarantine)
                    append_log(log_file, f"[S9A][{idx}/{len(S9_MATRIX)}] FAIL {spec_id}: {exc}")
                    return 1
            append_log(log_file, f"[S9A] batch_end {now_utc()} processed={len(S9_MATRIX)}")
    finally:
        conn.close()
    return 0

if __name__=='__main__':
    raise SystemExit(main())
