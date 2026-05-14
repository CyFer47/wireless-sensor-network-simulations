#!/usr/bin/env python3
"""Run Final Scale5000 S11 combined (5000 nodes: Stages A+B+C with internal gates)
DB-aware: pre-scan DB for existing complete rows and reuse them.
Gate 0: preflight checks
Gate A: Stage A must pass before proceeding to Stage B
Gate B: Stage B must pass before proceeding to Stage C
Gate C: Stage C must pass for overall completion
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
STATE_DEFAULT = REPO_ROOT /"outputs" / "s11_combined_state.json"
QUARANTINE_DEFAULT = REPO_ROOT / "outputs" / "s11_combined_quarantine.json"
LOG_DEFAULT = REPO_ROOT / "outputs" / "s11_combined_batch.log"
SPEC_ROOT_DEFAULT = REPO_ROOT / "runspecs" / "generated" / "s11_combined"
OUTPUT_ROOT_DEFAULT = REPO_ROOT / "outputs"

@dataclass(frozen=True)
class S11Rule:
    node_count: int
    cluster_count: int
    bs: int
    area_x: int
    area_y: int
    sim_time_s: float

S11_RULE = S11Rule(node_count=5000, cluster_count=200, bs=6, area_x=1150, area_y=1150, sim_time_s=300.0)

S11_STAGE_A: List[Dict[str, object]] = []
S11_STAGE_B: List[Dict[str, object]] = []
S11_STAGE_C: List[Dict[str, object]] = []

def build_matrix():
    global S11_STAGE_A, S11_STAGE_B, S11_STAGE_C
    
    # Stage A: 12 rows (F0/H0, F1/H1, F4/H4 with seed01 only)
    for family, healing, variant in [("F0", "H0", "V1"), ("F1", "H1", "V3"), ("F4", "H4", "V3")]:
        for arch in ['A', 'B']:
            for load in ['L1', 'L2']:
                S11_STAGE_A.append({
                    "run_spec_id": f"{family}_{healing}_{arch}_S11_{load}_seed01",
                    "architecture": arch,
                    "failure_family": family,
                    "healing_id": healing,
                    "variant": variant,
                    "load": load,
                    "seed": 1,
                })
    
    # Stage B: 32 rows (F1-F4 H1-H4, A/B, L1/L2, seed01/seed02)
    for family, healing, variant in [("F1", "H1", "V3"), ("F2", "H2", "V3"), ("F3", "H3", "V3"), ("F4", "H4", "V3")]:
        for arch in ['A', 'B']:
            for load in ['L1', 'L2']:
                for seed in [1, 2]:
                    S11_STAGE_B.append({
                        "run_spec_id": f"{family}_{healing}_{arch}_S11_{load}_seed{seed:02d}",
                        "architecture": arch,
                        "failure_family": family,
                        "healing_id": healing,
                        "variant": variant,
                        "load": load,
                        "seed": seed,
                    })
    
    # Stage C: 64 rows (32 H0 controls + 32 active healing)
    # H0 controls (F1-F4)
    for family in ["F1", "F2", "F3", "F4"]:
        for arch in ['A', 'B']:
            for load in ['L1', 'L2']:
                for seed in [1, 2]:
                    S11_STAGE_C.append({
                        "run_spec_id": f"{family}_H0_{arch}_S11_{load}_seed{seed:02d}",
                        "architecture": arch,
                        "failure_family": family,
                        "healing_id": "H0",
                        "variant": "V2",
                        "load": load,
                        "seed": seed,
                    })
    # Active healing (reused from Stage B)
    for family, healing_id in [("F1", "H1"), ("F2", "H2"), ("F3", "H3"), ("F4", "H4")]:
        for arch in ['A', 'B']:
            for load in ['L1', 'L2']:
                for seed in [1, 2]:
                    S11_STAGE_C.append({
                        "run_spec_id": f"{family}_{healing_id}_{arch}_S11_{load}_seed{seed:02d}",
                        "architecture": arch,
                        "failure_family": family,
                        "healing_id": healing_id,
                        "variant": "V3",
                        "load": load,
                        "seed": seed,
                    })

build_matrix()

def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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
    healing = row.get('healing_id') or row.get('healing')
    variant = row.get('variant')
    failure_family = row.get('failure_family')
    
    # V1 baseline: no failure injection
    is_baseline = (variant == 'V1' and failure_family == 'F0' and healing == 'H0')
    failure_enabled = not is_baseline
    
    recovery_enabled = healing != 'H0'
    recovery_profile = 'm7_profile' if recovery_enabled and row.get('architecture') == 'B' else 'none'
    recovery_delay = None if (healing == 'H0' or (variant == 'V2' and healing == 'H0')) else 12.0
    failure_time = None if is_baseline else 10.0
    
    timing = {
        "sim_time_s": S11_RULE.sim_time_s,
        "traffic_interval_s": 1.0,
        "aggregation_interval_s": 30.0,
        "dashboard_interval_s": 10.0,
        "failure_time_s": failure_time,
        "recovery_delay_s": recovery_delay,
    }

    exec_cfg = {
        "sim_source": "ns3",
        "enable_run_export": True,
        "export_root_dir": str(OUTPUT_ROOT_DEFAULT),
        "ns3_root_hint": str(Path('/home/cyfer/ns-allinone-3.42/ns-3.42')),
    }

    return {
        "schema_version": "runspec_v1",
        "run_spec_id": row['run_spec_id'],
        "description": f"Final Scale5000 Combined S11 {row['architecture']} {failure_family}/{healing} {row['load']} seed{seed:02d}",
        "phase": "phase1",
        "architecture": row['architecture'],
        "runnable": True,
        "variant": variant or row.get('variant'),
        "failure_family": failure_family,
        "healing_id": healing,
        "load": row['load'],
        "scale": "S11",
        "seed": seed,
        "topology": {"node_count": S11_RULE.node_count, "cluster_count": S11_RULE.cluster_count, "bs": S11_RULE.bs, "area": [S11_RULE.area_x, S11_RULE.area_y]},
        "timing": timing,
        "failure_injection": {"enabled": failure_enabled},
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
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    import psycopg2
    conn = psycopg2.connect(host=env['PGHOST'], port=int(env['PGPORT']), database=env['PGDATABASE'], user=env['PGUSER'], password=env['PGPASSWORD'])
    conn.autocommit = False
    return conn

def find_existing_complete(cur, external_run_id: str):
    cur.execute(
        "SELECT run_id, run_status, map_id, map_signature FROM wsn.runs WHERE experiment_version LIKE %s AND run_status='complete' ORDER BY run_id DESC LIMIT 1",
        (f"{external_run_id}_%",)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {"run_id": int(row['run_id']), 'run_status': row['run_status'], 'map_id': row['map_id'], 'map_signature': row['map_signature']}

def get_s11_map_dir(seed: int) -> Path:
    p = REPO_ROOT / 'maps' / 'examples' / f'map_S11_seed{seed:02d}'
    if not p.exists():
        raise FileNotFoundError(f"Map package missing: {p}")
    return p

def run_stage(matrix: List[Dict[str, object]], stage_name: str, state: dict, quarantine: list, conn, state_file: Path, quarantine_file: Path, log_file: Path, spec_root: Path, output_root: Path, ns3_root: str) -> tuple:
    """Execute a single stage and return (success: bool, new_ok_count: int, new_failed_count: int)"""
    append_log(log_file, f"\n[S11] === GATE: Entering {stage_name} (target {len(matrix)} rows) ===\n")
    
    from psycopg2.extras import RealDictCursor
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET search_path TO wsn, public")
        
        reused_count = 0
        for idx, row in enumerate(matrix, start=1):
            spec_id = row['run_spec_id']
            existing = find_existing_complete(cur, spec_id)
            if existing:
                state[spec_id] = {"status": "ok", "run_id": existing['run_id'], "map_id": existing['map_id'], "map_signature": existing['map_signature'], "source": "reused_existing_complete", "at": now_utc(), 'index': idx, 'stage': stage_name}
                reused_count += 1
        
        write_json(state_file, state)
        append_log(log_file, f"[{stage_name}] pre-scan: reused {reused_count}/{len(matrix)} existing complete rows\n")
        
        new_ok = 0
        new_failed = 0
        for idx, row in enumerate(matrix, start=1):
            spec_id = row['run_spec_id']
            if state.get(spec_id, {}).get('status') == 'ok':
                append_log(log_file, f"[{stage_name}][{idx}/{len(matrix)}] SKIP {spec_id} (already complete)\n")
                continue
            
            append_log(log_file, f"[{stage_name}][{idx}/{len(matrix)}] START {spec_id}\n")
            existing = find_existing_complete(cur, spec_id)
            if existing:
                state[spec_id] = {"status": "ok", "run_id": existing['run_id'], "map_id": existing['map_id'], "map_signature": existing['map_signature'], "source": "reused_existing_complete_prelaunch", "at": now_utc(), 'index': idx, 'stage': stage_name}
                write_json(state_file, state)
                append_log(log_file, f"[{stage_name}][{idx}/{len(matrix)}] SKIP {spec_id} (complete in DB)\n")
                continue
            
            try:
                spec_path = ensure_spec(row, spec_root)
                rc = run_checked([sys.executable, str(REPO_ROOT / 'tools' / 'validate_runspec.py'), str(spec_path)], cwd=REPO_ROOT, log_file=log_file)
                if rc != 0:
                    raise RuntimeError('spec validation failed')
                
                seed = row['seed']
                map_dir = get_s11_map_dir(seed)
                manifest = json.loads((map_dir / 'manifest.json').read_text())
                expected_nodes = S11_RULE.node_count
                manifest_node_count = None
                if isinstance(manifest.get('counts'), dict):
                    manifest_node_count = manifest['counts'].get('node_count')
                if manifest_node_count is None:
                    manifest_node_count = manifest.get('nodes')
                if manifest_node_count != expected_nodes:
                    raise RuntimeError(f'map node count mismatch (manifest={manifest_node_count} expected={expected_nodes})')
                
                rc = run_checked([sys.executable, str(REPO_ROOT / 'tools' / 'run_from_spec.py'), '--spec', str(spec_path), '--map', str(map_dir), '--ns3-root', ns3_root, '--output-root', str(output_root)], cwd=REPO_ROOT, log_file=log_file)
                if rc != 0:
                    raise RuntimeError(f'simulation failed rc={rc}')
                
                import glob
                matching_dirs = sorted(glob.glob(str(output_root / f"run_{spec_id}_*")), reverse=True)
                if not matching_dirs:
                    raise RuntimeError(f'missing export dir: no match for run_{spec_id}_*')
                export_dir = Path(matching_dirs[0])
                
                rc = run_checked([sys.executable, str(REPO_ROOT / 'importer' / 'import_run_to_postgres.py'), '--run-dir', str(export_dir), '--env-file', str(DB_ENV_FILE), '--schema', 'wsn', '--mode', 'replace'], cwd=REPO_ROOT, log_file=log_file)
                if rc != 0:
                    raise RuntimeError(f'import failed rc={rc}')
                
                cur.execute('SELECT run_id, map_id, map_signature FROM wsn.runs WHERE experiment_version LIKE %s AND run_status = %s ORDER BY run_id DESC LIMIT 1', (f'{spec_id}_%', 'complete'))
                row_db = cur.fetchone()
                if not row_db:
                    raise RuntimeError('db verification failed after import')
                
                state[spec_id] = {"status": "ok", "run_id": int(row_db['run_id']), "map_id": row_db['map_id'], "map_signature": row_db['map_signature'], "at": now_utc(), 'index': idx, 'stage': stage_name}
                write_json(state_file, state)
                new_ok += 1
                append_log(log_file, f"[{stage_name}][{idx}/{len(matrix)}] OK {spec_id} run_id={row_db['run_id']}\n")
            
            except Exception as exc:
                state[spec_id] = {"status": "failed", "reason": str(exc), 'index': idx, 'at': now_utc(), 'stage': stage_name}
                quarantine.append({"run_spec_id": spec_id, "reason": str(exc), 'index': idx, 'at': now_utc()})
                write_json(state_file, state)
                write_json(quarantine_file, quarantine)
                append_log(log_file, f"[{stage_name}][{idx}/{len(matrix)}] FAIL {spec_id}: {exc}\n")
                new_failed += 1
                # Stop immediately on failure
                return (False, new_ok, new_failed)
        
        append_log(log_file, f"[{stage_name}] completed: {new_ok} new OK, {new_failed} new FAILED\n")
        return (True, new_ok, new_failed)

def main():
    parser = argparse.ArgumentParser(description="Run S11 combined simulation (Stages A+B+C)")
    parser.add_argument('--state', type=Path, default=STATE_DEFAULT, help="State file")
    parser.add_argument('--quarantine', type=Path, default=QUARANTINE_DEFAULT, help="Quarantine file")
    parser.add_argument('--log', type=Path, default=LOG_DEFAULT, help="Log file")
    parser.add_argument('--spec-root', type=Path, default=SPEC_ROOT_DEFAULT, help="Runspec directory")
    parser.add_argument('--output-root', type=Path, default=OUTPUT_ROOT_DEFAULT, help="Output directory")
    parser.add_argument('--ns3-root', type=str, default='/home/cyfer/ns-allinone-3.42/ns-3.42', help="ns-3 root path")
    
    args = parser.parse_args()
    
    append_log(args.log, f"[S11] batch_start {now_utc()}\n")
    append_log(args.log, f"[S11] === PREFLIGHT ===\n")
    append_log(args.log, f"[S11] Scale rule: node_count={S11_RULE.node_count}, CH={S11_RULE.cluster_count}, BS={S11_RULE.bs}, area={S11_RULE.area_x}x{S11_RULE.area_y}, sim_time={S11_RULE.sim_time_s}s\n")
    append_log(args.log, f"[S11] Stage A target: {len(S11_STAGE_A)} rows\n")
    append_log(args.log, f"[S11] Stage B target: {len(S11_STAGE_B)} rows\n")
    append_log(args.log, f"[S11] Stage C target: {len(S11_STAGE_C)} rows\n")
    
    # Load existing state if it exists
    state = {}
    quarantine = []
    if args.state.exists():
        state = json.loads(args.state.read_text())
        append_log(args.log, f"[S11] Resuming: found {len(state)} prior entries in state\n")
    if args.quarantine.exists():
        quarantine = json.loads(args.quarantine.read_text())
        append_log(args.log, f"[S11] Found {len(quarantine)} prior quarantined entries\n")
    
    # Connect to DB
    try:
        conn = db_connect(DB_ENV_FILE)
        append_log(args.log, "[S11] DB connection OK\n")
    except Exception as exc:
        append_log(args.log, f"[S11] ERROR: DB connection failed: {exc}\n")
        sys.exit(1)
    
    # Execute stages sequentially
    gate_a_pass = False
    gate_b_pass = False
    gate_c_pass = False
    
    try:
        # Stage A
        append_log(args.log, "\n[S11] === GATE_A: Stage A (Smoke Test) ===\n")
        success, new_ok, new_failed = run_stage(S11_STAGE_A, "STAGE_A", state, quarantine, conn, args.state, args.quarantine, args.log, args.spec_root, args.output_root, args.ns3_root)
        if not success or new_failed > 0:
            append_log(args.log, f"[S11] ❌ GATE_A FAILED: new_ok={new_ok} new_failed={new_failed}\n")
            sys.exit(1)
        append_log(args.log, f"[S11] ✅ GATE_A PASSED: {new_ok} new rows\n")
        gate_a_pass = True
        
        # Stage B
        append_log(args.log, "\n[S11] === GATE_B: Stage B (Healing Validation) ===\n")
        success, new_ok, new_failed = run_stage(S11_STAGE_B, "STAGE_B", state, quarantine, conn, args.state, args.quarantine, args.log, args.spec_root, args.output_root, args.ns3_root)
        if not success or new_failed > 0:
            append_log(args.log, f"[S11] ❌ GATE_B FAILED: new_ok={new_ok} new_failed={new_failed}\n")
            sys.exit(1)
        append_log(args.log, f"[S11] ✅ GATE_B PASSED: {new_ok} new rows\n")
        gate_b_pass = True
        
        # Stage C
        append_log(args.log, "\n[S11] === GATE_C: Stage C (H0 vs Healing Control) ===\n")
        success, new_ok, new_failed = run_stage(S11_STAGE_C, "STAGE_C", state, quarantine, conn, args.state, args.quarantine, args.log, args.spec_root, args.output_root, args.ns3_root)
        if not success or new_failed > 0:
            append_log(args.log, f"[S11] ❌ GATE_C FAILED: new_ok={new_ok} new_failed={new_failed}\n")
            sys.exit(1)
        append_log(args.log, f"[S11] ✅ GATE_C PASSED: {new_ok} new rows\n")
        gate_c_pass = True
        
        # All gates passed
        append_log(args.log, f"\n[S11] ✅ ALL GATES PASSED: S11 combined execution complete\n")
        append_log(args.log, f"[S11] batch_end {now_utc()}\n")
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
