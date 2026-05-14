#!/usr/bin/env python3
"""Launch one deterministic Architecture A or B simulation from one run-spec + one map package."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
SCENARIO_SRC = REPO_ROOT / "ns3" / "test-ns3" / "m3-scenario-library.cc"

SCALE_NODE_MAP = {
    "S1": 50,
    "S2": 100,
    "S3": 200,
    "S4": 400,
    "S5": 800,
    "S6": 1600,
    "S7": 3000,
    "S8": 3500,
    "S9": 4000,
    "S10": 4500,
    "S11": 5000,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def die(msg: str, code: int = 2) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return code


def run_checked(cmd: list[str], cwd: Path | None = None) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return proc.returncode


def validate_spec(spec: dict) -> list[str]:
    errors: list[str] = []
    architecture = spec.get("architecture")
    if architecture not in {"A", "B"}:
        errors.append("architecture must be A or B")
    if not spec.get("runnable", False):
        errors.append("spec must be runnable")
    if spec.get("variant") not in {"V1", "V2", "V3"}:
        errors.append("invalid variant")
    if spec.get("failure_family") not in {"F0", "F1", "F2", "F3", "F4"}:
        errors.append("invalid failure_family")
    if spec.get("healing_id") not in {"H0", "H1", "H2", "H3", "H4"}:
        errors.append("invalid healing_id")
    if spec.get("load") not in {"L1", "L2"}:
        errors.append("invalid load")
    if spec.get("scale") not in SCALE_NODE_MAP:
        errors.append("invalid scale")
    if not isinstance(spec.get("seed"), int):
        errors.append("seed must be integer")
    if spec.get("variant") == "V1":
        if spec.get("failure_family") != "F0" or spec.get("healing_id") != "H0":
            errors.append("V1 requires F0/H0")
    if spec.get("variant") == "V2":
        if spec.get("healing_id") != "H0" or spec.get("failure_family") == "F0":
            errors.append("V2 requires failure family F1..F4 and H0")
    if spec.get("variant") == "V3":
        if spec.get("failure_family") == "F0" or spec.get("healing_id") == "H0":
            errors.append("V3 requires failure family F1..F4 and H1..H4")
    return errors


def validate_map_pair(spec: dict, map_dir: Path) -> dict:
    manifest = load_json(map_dir / "manifest.json")
    map_nodes = manifest.get("counts", {}).get("node_count")
    map_ch = manifest.get("counts", {}).get("ch_count")
    map_bs = manifest.get("counts", {}).get("bs_count")

    if manifest.get("scale_id") != spec.get("scale"):
        raise ValueError("map scale does not match spec scale")
    if manifest.get("seed") != spec.get("seed"):
        raise ValueError("map seed does not match spec seed")
    if map_nodes != SCALE_NODE_MAP.get(spec.get("scale")):
        raise ValueError("map node count does not match frozen scale rule")

    # Validate using the standalone validator as well.
    validate_cmd = [sys.executable, str(TOOLS_DIR / "validate_map.py"), str(map_dir)]
    if subprocess.run(validate_cmd).returncode != 0:
        raise ValueError("map validation failed")

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch one M4 Architecture A/B run from one spec and one map")
    parser.add_argument("--spec", required=True, help="Path to M1 run-spec JSON")
    parser.add_argument("--map", required=True, help="Path to M2 map package directory")
    parser.add_argument("--ns3-root", required=True, help="Path to ns-3.42 root")
    parser.add_argument("--output-root", default="outputs", help="Run export root directory")
    parser.add_argument("--run-label", default=None, help="Optional explicit export folder label")
    args = parser.parse_args()

    spec_path = Path(args.spec).resolve()
    map_dir = Path(args.map).resolve()
    ns3_root = Path(args.ns3_root).resolve()
    output_root = Path(args.output_root).resolve()

    if not spec_path.exists():
        return die(f"spec not found: {spec_path}")
    if not map_dir.exists():
        return die(f"map package not found: {map_dir}")
    if not ns3_root.exists():
        return die(f"ns3 root not found: {ns3_root}")
    if not SCENARIO_SRC.exists():
        return die(f"scenario source not found: {SCENARIO_SRC}")

    # Reuse the M1 validator for strict spec checking.
    if subprocess.run([sys.executable, str(TOOLS_DIR / "validate_runspec.py"), str(spec_path)]).returncode != 0:
        return die("run-spec validation failed")

    spec = load_json(spec_path)
    errors = validate_spec(spec)
    if errors:
        return die("; ".join(errors))

    manifest = validate_map_pair(spec, map_dir)

    if spec.get("scale") != manifest.get("scale_id"):
        return die("spec scale does not match map scale")

    # Scenario settings.
    load_multiplier = 1.0 if spec.get("load") == "L1" else 1.6
    enable_failure = spec.get("variant") in {"V2", "V3"}
    enable_recovery = spec.get("variant") == "V3"
    failure_time = spec.get("timing", {}).get("failure_time_s")
    recovery_delay = spec.get("timing", {}).get("recovery_delay_s")
    if spec.get("variant") == "V1":
        failure_time = 0.0
        recovery_delay = 0.0
    if recovery_delay is None:
        recovery_delay = 0.0

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    default_label = f"run_{spec['run_spec_id']}_{spec['seed']:02d}_{ts}"
    run_label = args.run_label or default_label

    with tempfile.TemporaryDirectory(prefix="m3_run_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        runtime_map_dir = tmp_dir / "map"
        runtime_output_root = tmp_dir / "outputs"
        shutil.copytree(map_dir, runtime_map_dir)
        runtime_output_root.mkdir(parents=True, exist_ok=True)

        scratch_dir = ns3_root / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        dest_source = scratch_dir / "m3-scenario-library.cc"
        shutil.copy2(SCENARIO_SRC, dest_source)

        build_cmd = [str(ns3_root / "ns3"), "build", "scratch/m3-scenario-library"]
        print(f"[M3] building: {' '.join(build_cmd)}")
        if subprocess.run(build_cmd, cwd=str(ns3_root)).returncode != 0:
            return die("ns-3 build failed")

        run_cmd = [
            str(ns3_root / "ns3"),
            "run",
            (
                "scratch/m3-scenario-library "
                f"--runSpecId={spec['run_spec_id']} "
                f"--mapId={manifest.get('map_id', map_dir.name)} "
                f"--mapSignature={manifest.get('deterministic_signature_sha256', '')} "
                f"--mapDir={runtime_map_dir} "
                f"--architecture={spec['architecture']} "
                f"--variant={spec['variant']} "
                f"--failureFamily={spec['failure_family']} "
                f"--healingId={spec['healing_id']} "
                f"--load={spec['load']} "
                f"--scale={spec['scale']} "
                f"--seed={spec['seed']} "
                f"--simTime={spec['timing']['sim_time_s']} "
                f"--trafficInterval={spec['timing']['traffic_interval_s']} "
                f"--aggregationInterval={spec['timing']['aggregation_interval_s']} "
                f"--dashboardInterval={spec['timing']['dashboard_interval_s']} "
                f"--failureTime={failure_time} "
                f"--recoveryDelay={recovery_delay} "
                f"--enableFailure={'true' if enable_failure else 'false'} "
                f"--enableRecovery={'true' if enable_recovery else 'false'} "
                f"--enableRunExport=true "
                f"--exportRootDir={runtime_output_root} "
                f"--exportRunLabel={run_label} "
                f"--loadMultiplier={load_multiplier}"
            ),
        ]

        print(f"[M3] running: {run_label}")
        rc = subprocess.run(run_cmd, cwd=str(ns3_root)).returncode
        if rc != 0:
            return die(f"simulation failed with exit code {rc}", rc)

        runtime_export = runtime_output_root / run_label
        final_export = output_root / run_label
        final_export.parent.mkdir(parents=True, exist_ok=True)
        if final_export.exists():
            shutil.rmtree(final_export)
        shutil.copytree(runtime_export, final_export)

    print(f"[M3] export directory: {output_root / run_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
