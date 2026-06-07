#!/usr/bin/env python3
"""Launch one deterministic Architecture A or B simulation from one run-spec + one map package."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import re
from datetime import datetime, timezone
from pathlib import Path
import os

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
# SCENARIO_SRC will be resolved at runtime from the provided --ns3-root
LOCAL_DB_ENV = REPO_ROOT / "03_database" / "config_local" / ".env"
REQUIRED_DB_ENV_KEYS = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSCHEMA")
PLACEHOLDER_DB_VALUES = {"", "CHANGE_ME_LOCAL_ONLY", "CHANGE_ME", "YOUR_DB_PASSWORD"}

SCALE_NODE_MAP = {
    "S1": 50,
    "S2": 100,
    "S3": 200,
    "S4": 400,
    "S5": 800,
    "S6": 1600,
    "S7": 3200,
    "S8": 4000,
    "S9": 4500,
    "S10": 5000,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def local_db_config_error() -> int:
    print("ERROR: local DB config missing or incomplete.", file=sys.stderr)
    print("Edit WSN_simulation/03_database/config_local/.env before using --import-db.", file=sys.stderr)
    return 2


def load_local_db_env() -> dict[str, str] | None:
    if not LOCAL_DB_ENV.exists():
        return None
    values = load_key_values(LOCAL_DB_ENV)
    missing = [k for k in REQUIRED_DB_ENV_KEYS if k not in values or values[k] in PLACEHOLDER_DB_VALUES]
    if missing:
        return None
    return values


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

    # Validate using the standalone V3 validator as well.
    validate_cmd = [sys.executable, str(TOOLS_DIR / "validate_maps_v3.py"), str(map_dir)]
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
    import_group = parser.add_mutually_exclusive_group()
    import_group.add_argument("--import-db", action="store_true", help="Import the exported run into PostgreSQL after a successful run")
    import_group.add_argument("--no-import", action="store_true", help="Explicitly disable PostgreSQL import")
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

    if args.import_db and not args.no_import:
        if load_local_db_env() is None:
            return local_db_config_error()

    # Locate scenario source relative to the provided ns3 root with sensible fallbacks.
    candidates = [
        REPO_ROOT / "source" / "m3-scenario-library-v3.cc",
        ns3_root / "test-ns3" / "m3-scenario-library.cc",
        ns3_root / "ns3" / "test-ns3" / "m3-scenario-library.cc",
        REPO_ROOT / "ns3" / "test-ns3" / "m3-scenario-library.cc",
    ]
    scenario_src = None
    for c in candidates:
        if c.exists():
            scenario_src = c
            break
    if scenario_src is None:
        return die(f"scenario source not found, tried: {', '.join(str(p) for p in candidates)}")

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

        # Resolve an executable ns-3 launcher (prefer `ns3`, then `waf`).
        candidate_launchers = [
            ns3_root / "ns3_runtime" / "ns3",
            ns3_root / "ns3_runtime" / "waf",
            ns3_root / "ns3",
            ns3_root / "waf",
        ]
        # Also consider a common alternate location used in this workspace.
        alt_launcher = Path("/home/cyfer/FYP/test-ns3/ns3")
        launcher = None
        for cand in candidate_launchers:
            if cand.exists() and cand.is_file() and os.access(str(cand), os.X_OK):
                launcher = cand
                break
        if launcher is None and alt_launcher.exists() and alt_launcher.is_file() and os.access(str(alt_launcher), os.X_OK):
            launcher = alt_launcher
        if launcher is None:
            checked = candidate_launchers + [alt_launcher]
            return die(f"ns-3 launcher not found or not executable; checked: {', '.join(str(p) for p in checked)}")

        runtime_root = launcher.parent
        scratch_dir = runtime_root / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        dest_source = scratch_dir / "m3-scenario-library.cc"
        shutil.copy2(scenario_src, dest_source)

        build_cwd = runtime_root

        build_cmd = [str(launcher), "build", "scratch/m3-scenario-library"]
        print(f"[M3] building: {' '.join(build_cmd)}")
        if subprocess.run(build_cmd, cwd=str(build_cwd)).returncode != 0:
            return die("ns-3 build failed")

        run_cmd = [
            str(launcher),
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

        if args.import_db and not args.no_import:
            local_db_env = load_local_db_env()
            if local_db_env is None:
                return local_db_config_error()

            importer = REPO_ROOT / "03_database" / "import_export" / "import_run_to_postgres.py"
            if not importer.exists():
                return die(f"importer not found: {importer}")

            importer_cmd = [sys.executable, str(importer), "--run-dir", str(final_export)]
            importer_cmd += ["--env-file", str(LOCAL_DB_ENV)]

            print(f"[M3] importing: {final_export}")
            importer_env = os.environ.copy()
            importer_env.update(local_db_env)
            proc = subprocess.run(importer_cmd, capture_output=True, text=True, env=importer_env)
            if proc.stdout:
                print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
            if proc.returncode != 0:
                if proc.stderr:
                    print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")
                return die(f"database import failed with exit code {proc.returncode}", proc.returncode)

            m = re.search(r"^\s*run_id:\s*(\d+)\s*$", proc.stdout, re.MULTILINE)
            if m:
                print(f"[M3] imported run_id: {m.group(1)}")
            else:
                print("[M3] imported run_id: unavailable")
            print("[M3] verification suggestion: python3 /home/cyfer/FYP/WSN_simulation/03_database/verification_queries/show_latest_run.sql (or your preferred query)")

    print(f"[M3] export directory: {output_root / run_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
