#!/usr/bin/env python3
"""Run Final Scale5000 S8 Stage B (32-run healing-family validation batch) with resumable progress."""

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
NS3_DEFAULT = Path("/home/cyfer/ns-allinone-3.42/ns-3.42")
DB_ENV_FILE = Path("/home/cyfer/FYP/WSN Dashboard Milestone V2/web-monitor/backend/config/.env")

STATE_DEFAULT = REPO_ROOT / "outputs" / "s8_stageb_state.json"
QUARANTINE_DEFAULT = REPO_ROOT / "outputs" / "s8_stageb_quarantine.json"
LOG_DEFAULT = REPO_ROOT / "outputs" / "s8_stageb_batch.log"
SPEC_ROOT_DEFAULT = REPO_ROOT / "runspecs" / "generated" / "s8_stageb"
OUTPUT_ROOT_DEFAULT = REPO_ROOT / "outputs"


@dataclass(frozen=True)
class ScaleRule:
    node_count: int
    cluster_count: int
    sim_time_s: float
    traffic_interval_s: float
    aggregation_interval_s: float
    dashboard_interval_s: float
    failure_time_s: float
    recovery_delay_s: float


S8_RULE = ScaleRule(
    node_count=3500,
    cluster_count=140,
    sim_time_s=230.0,
    traffic_interval_s=3.0,
    aggregation_interval_s=4.0,
    dashboard_interval_s=1.0,
    failure_time_s=46.0,
    recovery_delay_s=4.0,
)

# Stage B matrix: 4 families × 2 architectures × 2 loads × 2 seeds = 32 rows
S8_STAGEB_MATRIX: List[Dict[str, str | int]] = []

def build_stageb_matrix():
    """Build 32-row Stage B matrix: F1–F4, A/B, L1/L2, seed01/seed02."""
    families = [("F1", "H1"), ("F2", "H2"), ("F3", "H3"), ("F4", "H4")]
    architectures = ["A", "B"]
    loads = ["L1", "L2"]
    seeds = [1, 2]
    
    for family, healing in families:
        for arch in architectures:
            for load in loads:
                for seed in seeds:
                    seed_suffix = f"seed{seed:02d}"
                    run_spec_id = f"{family}_{healing}_{arch}_S8_{load}_{seed_suffix}"
                    S8_STAGEB_MATRIX.append({
                        "run_spec_id": run_spec_id,
                        "architecture": arch,
                        "failure_family": family,
                        "healing_id": healing,
                        "variant": "V3",
                        "load": load,
                        "seed": seed,
                    })

build_stageb_matrix()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


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


def get_s8_map_dir(seed: int) -> Path:
    """Return the S8 map directory for the given seed."""
    map_dir = REPO_ROOT / "maps" / "examples" / f"map_S8_seed{seed:02d}"
    if not (map_dir / "manifest.json").exists():
        raise FileNotFoundError(f"Missing S8 map package: {map_dir}")
    return map_dir


def get_s8_map_signature(seed: int) -> str:
    """Return the expected deterministic signature for S8 at given seed."""
    sigs = {
        1: "fb969a468352b224ac76c1dce90944cf5f7dd6acc148c153e89692e2ef04ceb5",
        2: "9d9cbda6449d002e75fc6dc97c8cf523044b156c6e3ec5d2656fa19f49a9c21f",
    }
    return sigs.get(seed, "unknown")


def spec_for_row(row: Dict[str, str | int]) -> dict:
    variant = row["variant"]
    seed = row["seed"]
    failure_time = None if variant == "V1" else S8_RULE.failure_time_s
    recovery_delay = None if variant == "V1" else S8_RULE.recovery_delay_s
    
    return {
        "schema_version": "runspec_v1",
        "run_spec_id": row["run_spec_id"],
        "description": f"Final Scale5000 Stage B {row['architecture']} {row['failure_family']}/{row['healing_id']} {row['load']} seed{seed:02d}",
        "phase": "phase1",
        "owner": "vmware-sim",
        "notes": "Final Scale5000 S8 Stage B healing-family validation",
        "architecture": row["architecture"],
        "runnable": True,
        "variant": variant,
        "failure_family": row["failure_family"],
        "healing_id": row["healing_id"],
        "load": row["load"],
        "scale": "S8",
        "seed": seed,
        "topology": {"node_count": S8_RULE.node_count, "cluster_count": S8_RULE.cluster_count},
        "timing": {
            "sim_time_s": S8_RULE.sim_time_s,
            "traffic_interval_s": S8_RULE.traffic_interval_s,
            "aggregation_interval_s": S8_RULE.aggregation_interval_s,
            "dashboard_interval_s": S8_RULE.dashboard_interval_s,
            "failure_time_s": failure_time,
            "recovery_delay_s": recovery_delay,
        },
        "failure_injection": {"enabled": variant != "V1", "target": "cluster_ch"},
        "recovery": {"enabled": variant == "V3", "profile": "m7_profile"},
        "execution": {
            "sim_source": "test-ns3/m3-scenario-library.cc",
            "ns3_binary_hint": str(NS3_DEFAULT),
            "enable_run_export": True,
            "export_root_dir": "outputs",
        },
        "provenance_tags": {"mix_alias": row["run_spec_id"]},
        "reserved_architecture_b": {
            "controller_family": "BSBSSP",
            "controller_profile": "bsbssp_phase1" if row["architecture"] == "B" else "reserved",
            "planned_status": "active" if row["architecture"] == "B" else "planned",
        },
    }


def ensure_spec(row: Dict[str, str | int], spec_root: Path) -> Path:
    spec_root.mkdir(parents=True, exist_ok=True)
    spec_path = spec_root / f"{row['run_spec_id']}.json"
    spec = spec_for_row(row)
    write_json(spec_path, spec)
    return spec_path


def latest_run_id_for_external_id(cur, external_run_id: str) -> int | None:
    cur.execute("SELECT run_id FROM wsn.runs WHERE experiment_version = %s ORDER BY run_id DESC LIMIT 1", (external_run_id,))
    row = cur.fetchone()
    return int(row["run_id"]) if row else None


def verify_import(cur, external_run_id: str) -> dict:
    cur.execute(
        """
        SELECT run_id, scale, architecture, failure_family, healing_id, load, seed, run_status, map_id, map_signature
        FROM wsn.runs
        WHERE experiment_version = %s
        ORDER BY run_id DESC
        LIMIT 1
        """,
        (external_run_id,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Imported run not found in DB")
    return {
        "run_id": int(row["run_id"]),
        "scale": row["scale"],
        "architecture": row["architecture"],
        "failure_family": row["failure_family"],
        "healing_id": row["healing_id"],
        "load": row["load"],
        "seed": row["seed"],
        "run_status": row["run_status"],
        "map_id": row["map_id"],
        "map_signature": row["map_signature"],
    }


def find_existing_complete(cur, external_run_id: str) -> dict | None:
    """Return latest complete DB row for external_run_id, or None if missing."""
    cur.execute(
        """
        SELECT run_id, scale, architecture, failure_family, healing_id, load, seed, run_status, map_id, map_signature
        FROM wsn.runs
        WHERE experiment_version = %s
          AND run_status = 'complete'
        ORDER BY run_id DESC
        LIMIT 1
        """,
        (external_run_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "run_id": int(row["run_id"]),
        "scale": row["scale"],
        "architecture": row["architecture"],
        "failure_family": row["failure_family"],
        "healing_id": row["healing_id"],
        "load": row["load"],
        "seed": row["seed"],
        "run_status": row["run_status"],
        "map_id": row["map_id"],
        "map_signature": row["map_signature"],
    }


def db_connect(cfg_file: Path):
    env = {}
    for line in cfg_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    import psycopg2
    conn = psycopg2.connect(
        host=env["PGHOST"],
        port=int(env["PGPORT"]),
        database=env["PGDATABASE"],
        user=env["PGUSER"],
        password=env["PGPASSWORD"],
        connect_timeout=int(env.get("PGCONNECT_TIMEOUT", "5")),
        sslmode=env.get("PGSSLMODE", "disable"),
    )
    conn.autocommit = False
    return conn


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Final Scale5000 S8 Stage B healing-family validation batch")
    parser.add_argument("--ns3-root", default=str(NS3_DEFAULT))
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT_DEFAULT))
    parser.add_argument("--spec-root", default=str(SPEC_ROOT_DEFAULT))
    parser.add_argument("--state-file", default=str(STATE_DEFAULT))
    parser.add_argument("--quarantine-file", default=str(QUARANTINE_DEFAULT))
    parser.add_argument("--log-file", default=str(LOG_DEFAULT))
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--max-runs", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ns3_root = Path(args.ns3_root)
    output_root = Path(args.output_root)
    spec_root = Path(args.spec_root)
    state_file = Path(args.state_file)
    quarantine_file = Path(args.quarantine_file)
    log_file = Path(args.log_file)

    output_root.mkdir(parents=True, exist_ok=True)
    spec_root.mkdir(parents=True, exist_ok=True)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    quarantine_file.parent.mkdir(parents=True, exist_ok=True)

    # Ensure both seed01 and seed02 maps exist
    for seed in [1, 2]:
        get_s8_map_dir(seed)

    if not DB_ENV_FILE.exists():
        raise FileNotFoundError(f"DB env file not found: {DB_ENV_FILE}")

    import psycopg2  # type: ignore
    from psycopg2.extras import RealDictCursor  # type: ignore

    state = load_json(state_file) if state_file.exists() else {}
    quarantine = load_json(quarantine_file) if quarantine_file.exists() else []
    if not isinstance(state, dict):
        state = {}
    if not isinstance(quarantine, list):
        quarantine = []

    append_log(log_file, f"[S8B] batch_start {now_utc()} total_runs={len(S8_STAGEB_MATRIX)}")
    if args.dry_run:
        append_log(log_file, "[S8B] dry-run only; no simulations will be launched")
        return 0

    conn = db_connect(DB_ENV_FILE)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET search_path TO wsn, public")
            # Reuse already-complete rows from DB so Stage B can resume safely without duplicates.
            for idx, row in enumerate(S8_STAGEB_MATRIX, start=1):
                run_spec_id = row["run_spec_id"]
                existing = find_existing_complete(cur, run_spec_id)
                if existing:
                    state[run_spec_id] = {
                        "status": "ok",
                        "run_id": existing["run_id"],
                        "run_label": run_spec_id,
                        "scale": "S8",
                        "architecture": row["architecture"],
                        "failure_family": row["failure_family"],
                        "healing_id": row["healing_id"],
                        "load": row["load"],
                        "seed": int(row["seed"]),
                        "run_status": existing["run_status"],
                        "map_id": existing["map_id"],
                        "map_signature": existing["map_signature"],
                        "at": now_utc(),
                        "index": idx,
                        "source": "reused_existing_complete",
                    }

            write_json(state_file, state)
            write_json(quarantine_file, quarantine)

            processed = 0
            skipped = 0
            for idx, row in enumerate(S8_STAGEB_MATRIX, start=1):
                if idx < args.start_index:
                    continue
                run_spec_id = row["run_spec_id"]
                if run_spec_id in state and state[run_spec_id].get("status") == "ok":
                    skipped += 1
                    append_log(log_file, f"[S8B][{idx}/{len(S8_STAGEB_MATRIX)}] SKIP {run_spec_id} (already complete)")
                    continue
                if args.max_runs > 0 and processed >= args.max_runs:
                    break
                processed += 1
                append_log(log_file, f"[S8B][{idx}/{len(S8_STAGEB_MATRIX)}] START {run_spec_id} ({processed} of active batch)")

                try:
                    # Re-check DB immediately before launch in case another process imported this row.
                    existing = find_existing_complete(cur, run_spec_id)
                    if existing:
                        state[run_spec_id] = {
                            "status": "ok",
                            "run_id": existing["run_id"],
                            "run_label": run_spec_id,
                            "scale": "S8",
                            "architecture": row["architecture"],
                            "failure_family": row["failure_family"],
                            "healing_id": row["healing_id"],
                            "load": row["load"],
                            "seed": int(row["seed"]),
                            "run_status": existing["run_status"],
                            "map_id": existing["map_id"],
                            "map_signature": existing["map_signature"],
                            "at": now_utc(),
                            "index": idx,
                            "source": "reused_existing_complete_prelaunch",
                        }
                        write_json(state_file, state)
                        append_log(log_file, f"[S8B][{idx}/{len(S8_STAGEB_MATRIX)}] SKIP {run_spec_id} (complete in DB)")
                        continue

                    spec_path = ensure_spec(row, spec_root)
                    validate_rc = run_checked([
                        sys.executable,
                        str(REPO_ROOT / "tools" / "validate_runspec.py"),
                        str(spec_path),
                    ], cwd=REPO_ROOT, log_file=log_file)
                    if validate_rc != 0:
                        raise RuntimeError(f"run-spec validation failed (rc={validate_rc})")

                    seed = int(row["seed"])
                    map_dir = get_s8_map_dir(seed)
                    manifest = load_json(map_dir / "manifest.json")
                    if manifest.get("scale_id") != "S8" or manifest.get("seed") != seed:
                        raise RuntimeError(f"map linkage mismatch for seed {seed}")
                    expected_sig = get_s8_map_signature(seed)
                    if manifest.get("deterministic_signature_sha256") != expected_sig:
                        raise RuntimeError(f"map signature mismatch for seed {seed}")

                    run_rc = run_checked([
                        sys.executable,
                        str(REPO_ROOT / "tools" / "run_from_spec.py"),
                        "--spec",
                        str(spec_path),
                        "--map",
                        str(map_dir),
                        "--ns3-root",
                        str(ns3_root),
                        "--output-root",
                        str(output_root),
                        "--run-label",
                        run_spec_id,
                    ], cwd=REPO_ROOT, log_file=log_file)
                    if run_rc != 0:
                        raise RuntimeError(f"simulation failed with rc={run_rc}")

                    export_dir = output_root / run_spec_id
                    if not export_dir.exists():
                        raise RuntimeError(f"missing export directory: {export_dir}")

                    imp_rc = run_checked([
                        sys.executable,
                        str(REPO_ROOT / "importer" / "import_run_to_postgres.py"),
                        "--run-dir",
                        str(export_dir),
                        "--env-file",
                        str(DB_ENV_FILE),
                        "--schema",
                        "wsn",
                        "--mode",
                        "replace",
                    ], cwd=REPO_ROOT, log_file=log_file)
                    if imp_rc != 0:
                        raise RuntimeError(f"import failed with rc={imp_rc}")

                    cur.execute("SELECT 1")
                    db_info = verify_import(cur, run_spec_id)
                    cur.execute("SELECT COUNT(*) AS c FROM wsn.runs WHERE scale = 'S8'")
                    s8_count = int(cur.fetchone()["c"])
                    cur.execute("SELECT COUNT(*) AS c FROM wsn.runs WHERE scale = 'S8' AND architecture = %s", (row["architecture"],))
                    arch_count = int(cur.fetchone()["c"])
                    cur.execute("SELECT COUNT(*) AS c FROM wsn.runs WHERE scale = 'S8' AND load = %s", (row["load"],))
                    load_count = int(cur.fetchone()["c"])
                    cur.execute("SELECT COUNT(*) AS c FROM wsn.runs WHERE scale = 'S8' AND failure_family = %s", (row["failure_family"],))
                    fam_count = int(cur.fetchone()["c"])
                    cur.execute("SELECT COUNT(*) AS c FROM wsn.runs WHERE scale = 'S8' AND healing_id = %s", (row["healing_id"],))
                    heal_count = int(cur.fetchone()["c"])
                    cur.execute("SELECT MAX(run_id) AS max_run_id FROM wsn.runs")
                    newest_run_id = int(cur.fetchone()["max_run_id"])
                    
                    state[run_spec_id] = {
                        "status": "ok",
                        "run_id": db_info["run_id"],
                        "run_label": run_spec_id,
                        "scale": "S8",
                        "architecture": row["architecture"],
                        "failure_family": row["failure_family"],
                        "healing_id": row["healing_id"],
                        "load": row["load"],
                        "seed": seed,
                        "run_status": db_info["run_status"],
                        "map_id": db_info["map_id"],
                        "map_signature": db_info["map_signature"],
                        "s8_count": s8_count,
                        "arch_count": arch_count,
                        "load_count": load_count,
                        "family_count": fam_count,
                        "healing_count": heal_count,
                        "newest_run_id": newest_run_id,
                        "at": now_utc(),
                        "index": idx,
                    }
                    write_json(state_file, state)
                    write_json(quarantine_file, quarantine)
                    append_log(log_file, f"[S8B][{idx}/{len(S8_STAGEB_MATRIX)}] OK {run_spec_id} run_id={db_info['run_id']} newest_run_id={newest_run_id} s8_count={s8_count}")
                except Exception as exc:
                    state[run_spec_id] = {"status": "failed", "reason": str(exc), "at": now_utc(), "index": idx}
                    quarantine.append({"run_spec_id": run_spec_id, "reason": str(exc), "index": idx, "at": now_utc()})
                    write_json(state_file, state)
                    write_json(quarantine_file, quarantine)
                    append_log(log_file, f"[S8B][{idx}/{len(S8_STAGEB_MATRIX)}] FAIL {run_spec_id}: {exc}")
                    return 1

        append_log(log_file, f"[S8B] batch_end {now_utc()} processed={processed} skipped={skipped}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
