#!/usr/bin/env python3
"""Run M7 production batch with resumable progress and import tracking."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
NS3_DEFAULT = Path("<VM_HOME_PATH>/ns-allinone-3.42/ns-3.42")

ARCHS = ("A", "B")
SCALES = ("S1", "S2", "S3", "S4", "S5", "S6")
LOADS = ("L1", "L2")
SEEDS = (1, 2, 3, 4)
FAILURES = ("F1", "F2", "F3", "F4")

SCALE_CONFIG = {
    "S1": {"node_count": 50, "cluster_count": 5, "sim_time_s": 30.0, "traffic_interval_s": 3.0, "aggregation_interval_s": 6.0, "dashboard_interval_s": 1.0, "failure_time_s": 13.0, "recovery_delay_s": 1.0},
    "S2": {"node_count": 100, "cluster_count": 6, "sim_time_s": 60.0, "traffic_interval_s": 3.0, "aggregation_interval_s": 5.0, "dashboard_interval_s": 1.0, "failure_time_s": 18.0, "recovery_delay_s": 2.0},
    "S3": {"node_count": 200, "cluster_count": 10, "sim_time_s": 90.0, "traffic_interval_s": 3.0, "aggregation_interval_s": 5.0, "dashboard_interval_s": 1.0, "failure_time_s": 24.0, "recovery_delay_s": 2.0},
    "S4": {"node_count": 400, "cluster_count": 20, "sim_time_s": 120.0, "traffic_interval_s": 3.0, "aggregation_interval_s": 4.0, "dashboard_interval_s": 1.0, "failure_time_s": 30.0, "recovery_delay_s": 3.0},
    "S5": {"node_count": 800, "cluster_count": 32, "sim_time_s": 150.0, "traffic_interval_s": 3.0, "aggregation_interval_s": 4.0, "dashboard_interval_s": 1.0, "failure_time_s": 36.0, "recovery_delay_s": 3.0},
    "S6": {"node_count": 1600, "cluster_count": 64, "sim_time_s": 180.0, "traffic_interval_s": 3.0, "aggregation_interval_s": 4.0, "dashboard_interval_s": 1.0, "failure_time_s": 42.0, "recovery_delay_s": 4.0},
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_rows() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    # V1 controls: F0/H0 only (validator/runtime invariant).
    for scale in SCALES:
        cfg = SCALE_CONFIG[scale]
        for seed in SEEDS:
            for arch in ARCHS:
                for load in LOADS:
                    rows.append({
                        "run_spec_id": f"F0_H0_{arch}_{scale}_{load}_seed{seed:02d}",
                        "architecture": arch,
                        "failure_family": "F0",
                        "healing_id": "H0",
                        "variant": "V1",
                        "scale": scale,
                        "load": load,
                        "seed": seed,
                        "cfg": cfg,
                    })

    # V2 and V3 rows across F1..F4.
    for scale in SCALES:
        cfg = SCALE_CONFIG[scale]
        for seed in SEEDS:
            for arch in ARCHS:
                for load in LOADS:
                    for failure in FAILURES:
                        # V2: failure + no healing
                        rows.append({
                            "run_spec_id": f"{failure}_H0_{arch}_{scale}_{load}_seed{seed:02d}",
                            "architecture": arch,
                            "failure_family": failure,
                            "healing_id": "H0",
                            "variant": "V2",
                            "scale": scale,
                            "load": load,
                            "seed": seed,
                            "cfg": cfg,
                        })

                        # V3: failure + matched healing.
                        h = "H" + failure[1:]
                        rows.append({
                            "run_spec_id": f"{failure}_{h}_{arch}_{scale}_{load}_seed{seed:02d}",
                            "architecture": arch,
                            "failure_family": failure,
                            "healing_id": h,
                            "variant": "V3",
                            "scale": scale,
                            "load": load,
                            "seed": seed,
                            "cfg": cfg,
                        })
    return rows


def ensure_map(scale: str, seed: int, maps_root: Path, logf) -> Path:
    map_dir = maps_root / f"map_{scale}_seed{seed:02d}"
    if (map_dir / "manifest.json").exists():
        return map_dir

    gen_cmd = [
        "python3",
        str(REPO_ROOT / "tools" / "generate_map.py"),
        "--scale-id",
        scale,
        "--seed",
        str(seed),
        "--output-root",
        str(maps_root),
        "--map-id",
        f"map_{scale}_seed{seed:02d}",
    ]
    rc = subprocess.run(gen_cmd, cwd=str(REPO_ROOT), stdout=logf, stderr=logf).returncode
    if rc != 0:
        raise RuntimeError(f"map generation failed for {scale}/seed{seed:02d}")

    val_cmd = ["python3", str(REPO_ROOT / "tools" / "validate_map.py"), str(map_dir)]
    rc = subprocess.run(val_cmd, cwd=str(REPO_ROOT), stdout=logf, stderr=logf).returncode
    if rc != 0:
        raise RuntimeError(f"map validation failed for {scale}/seed{seed:02d}")

    return map_dir


def write_spec(row: Dict[str, object], spec_dir: Path) -> Path:
    cfg = row["cfg"]
    variant = row["variant"]
    failure_time = None if variant == "V1" else cfg["failure_time_s"]
    recovery_delay = cfg["recovery_delay_s"] if variant == "V3" else None

    spec = {
        "schema_version": "runspec_v1",
        "run_spec_id": row["run_spec_id"],
        "description": f"M7 production {variant} {row['failure_family']}/{row['healing_id']} {row['architecture']} {row['scale']}/{row['load']}",
        "phase": "phase1",
        "owner": "vmware-sim",
        "notes": "M7 production batch",
        "architecture": row["architecture"],
        "runnable": True,
        "variant": variant,
        "failure_family": row["failure_family"],
        "healing_id": row["healing_id"],
        "load": row["load"],
        "scale": row["scale"],
        "seed": row["seed"],
        "topology": {"node_count": cfg["node_count"], "cluster_count": cfg["cluster_count"]},
        "timing": {
            "sim_time_s": cfg["sim_time_s"],
            "traffic_interval_s": cfg["traffic_interval_s"],
            "aggregation_interval_s": cfg["aggregation_interval_s"],
            "dashboard_interval_s": cfg["dashboard_interval_s"],
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

    spec_path = spec_dir / f"{row['run_spec_id']}.json"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return spec_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run M7 production batch")
    parser.add_argument("--ns3-root", default=str(NS3_DEFAULT))
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--maps-root", default="maps/generated")
    parser.add_argument("--spec-root", default="runspecs/generated/m7")
    parser.add_argument("--state-file", default="outputs/m7_state.json")
    parser.add_argument("--log-file", default="outputs/m7_batch.log")
    parser.add_argument("--quarantine-file", default="outputs/m7_quarantine.json")
    parser.add_argument("--max-runs", type=int, default=0, help="0 means no cap")
    parser.add_argument("--start-index", type=int, default=1)
    args = parser.parse_args()

    ns3_root = Path(args.ns3_root).resolve()
    output_root = Path(args.output_root).resolve()
    maps_root = Path(args.maps_root).resolve()
    spec_root = Path(args.spec_root).resolve()
    state_file = Path(args.state_file).resolve()
    log_file = Path(args.log_file).resolve()
    quarantine_file = Path(args.quarantine_file).resolve()

    output_root.mkdir(parents=True, exist_ok=True)
    maps_root.mkdir(parents=True, exist_ok=True)
    spec_root.mkdir(parents=True, exist_ok=True)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    rows = build_rows()

    state: Dict[str, Dict[str, object]] = {}
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))

    quarantine: List[Dict[str, object]] = []
    if quarantine_file.exists():
        quarantine = json.loads(quarantine_file.read_text(encoding="utf-8"))

    processed = 0
    with log_file.open("a", encoding="utf-8") as logf:
        logf.write(f"\n[M7] batch_start {now_utc()} total_rows={len(rows)}\n")
        for idx, row in enumerate(rows, start=1):
            if idx < args.start_index:
                continue
            run_id = str(row["run_spec_id"])
            if run_id in state and state[run_id].get("status") == "ok":
                continue
            if args.max_runs > 0 and processed >= args.max_runs:
                break

            processed += 1
            logf.write(f"[M7][{idx}/{len(rows)}] START {run_id}\n")
            logf.flush()

            try:
                map_dir = ensure_map(str(row["scale"]), int(row["seed"]), maps_root, logf)
                spec_path = write_spec(row, spec_root)
            except Exception as exc:
                state[run_id] = {
                    "status": "failed_preflight",
                    "reason": str(exc),
                    "at": now_utc(),
                    "index": idx,
                }
                quarantine.append({"run_spec_id": run_id, "stage": "preflight", "reason": str(exc), "index": idx})
                state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
                quarantine_file.write_text(json.dumps(quarantine, indent=2) + "\n", encoding="utf-8")
                continue

            run_cmd = [
                "python3",
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
                run_id,
            ]
            rc = subprocess.run(run_cmd, cwd=str(REPO_ROOT), stdout=logf, stderr=logf).returncode
            if rc != 0:
                state[run_id] = {"status": "failed_launch", "run_rc": rc, "at": now_utc(), "index": idx}
                quarantine.append({"run_spec_id": run_id, "stage": "launch", "rc": rc, "index": idx})
                state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
                quarantine_file.write_text(json.dumps(quarantine, indent=2) + "\n", encoding="utf-8")
                continue

            imp_cmd = [
                "python3",
                str(REPO_ROOT / "importer" / "import_run_to_postgres.py"),
                "--run-dir",
                str(output_root / run_id),
                "--env-file",
                str(REPO_ROOT / "config" / ".env"),
                "--schema",
                "wsn",
                "--mode",
                "replace",
            ]
            imp_rc = subprocess.run(imp_cmd, cwd=str(REPO_ROOT), stdout=logf, stderr=logf).returncode
            if imp_rc != 0:
                state[run_id] = {"status": "failed_import", "run_rc": rc, "import_rc": imp_rc, "at": now_utc(), "index": idx}
                quarantine.append({"run_spec_id": run_id, "stage": "import", "rc": imp_rc, "index": idx})
                state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
                quarantine_file.write_text(json.dumps(quarantine, indent=2) + "\n", encoding="utf-8")
                continue

            state[run_id] = {"status": "ok", "run_rc": rc, "import_rc": imp_rc, "at": now_utc(), "index": idx}
            state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            quarantine_file.write_text(json.dumps(quarantine, indent=2) + "\n", encoding="utf-8")

        logf.write(f"[M7] batch_end {now_utc()} processed={processed}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
