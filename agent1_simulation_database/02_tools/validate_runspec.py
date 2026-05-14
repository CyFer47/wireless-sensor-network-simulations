#!/usr/bin/env python3
"""Lightweight run-spec validator for M1."""

import argparse
import json
import re
import sys
from pathlib import Path

RUNSPEC_ID_RE = re.compile(r"^(F0|F1|F2|F3|F4)_H[0-4]_[AB]_S(?:[1-9]|10|11)_L[1-2]_seed[0-9]{2}$")

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

REQUIRED_PATHS = [
    "schema_version",
    "run_spec_id",
    "description",
    "phase",
    "architecture",
    "runnable",
    "variant",
    "failure_family",
    "healing_id",
    "load",
    "scale",
    "seed",
    "topology.node_count",
    "topology.cluster_count",
    "timing.sim_time_s",
    "timing.traffic_interval_s",
    "timing.aggregation_interval_s",
    "timing.dashboard_interval_s",
    "failure_injection.enabled",
    "recovery.enabled",
    "execution.sim_source",
    "execution.enable_run_export",
    "execution.export_root_dir",
]


def get_path(data, path):
    cur = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def add_error(errors, msg):
    errors.append(msg)


def validate_required(data, errors):
    for path in REQUIRED_PATHS:
        value = get_path(data, path)
        if value is None:
            add_error(errors, f"Missing required field: {path}")


def validate_enums(data, errors):
    if data.get("schema_version") != "runspec_v1":
        add_error(errors, "schema_version must be runspec_v1")

    if data.get("phase") != "phase1":
        add_error(errors, "phase must be phase1")

    if data.get("architecture") not in {"A", "B"}:
        add_error(errors, "architecture must be A or B")

    if data.get("variant") not in {"V1", "V2", "V3"}:
        add_error(errors, "variant must be V1, V2, or V3")

    if data.get("failure_family") not in {"F0", "F1", "F2", "F3", "F4"}:
        add_error(errors, "failure_family must be F0..F4")

    if data.get("healing_id") not in {"H0", "H1", "H2", "H3", "H4"}:
        add_error(errors, "healing_id must be H0..H4")

    if data.get("load") not in {"L1", "L2"}:
        add_error(errors, "load must be L1 or L2")

    if data.get("scale") not in SCALE_NODE_MAP:
        add_error(errors, "scale must be S1..S11")


def validate_name_and_identity(spec_path, data, errors):
    run_spec_id = data.get("run_spec_id", "")
    if not RUNSPEC_ID_RE.match(run_spec_id):
        add_error(errors, "run_spec_id does not match canonical pattern")
        return

    if spec_path.stem != run_spec_id:
        add_error(errors, f"file name stem must match run_spec_id ({run_spec_id})")

    parts = run_spec_id.split("_")
    failure_tok, heal_tok, arch_tok, scale_tok, load_tok, seed_tok = parts

    if failure_tok != data.get("failure_family"):
        add_error(errors, "run_spec_id failure token does not match failure_family")
    if heal_tok != data.get("healing_id"):
        add_error(errors, "run_spec_id healing token does not match healing_id")
    if arch_tok != data.get("architecture"):
        add_error(errors, "run_spec_id architecture token does not match architecture")
    if scale_tok != data.get("scale"):
        add_error(errors, "run_spec_id scale token does not match scale")
    if load_tok != data.get("load"):
        add_error(errors, "run_spec_id load token does not match load")

    seed_val = data.get("seed")
    if isinstance(seed_val, int):
        seed_from_id = int(seed_tok.replace("seed", ""))
        if seed_from_id != seed_val:
            add_error(errors, "run_spec_id seed token does not match seed")


def validate_scale_node_count(data, errors):
    scale = data.get("scale")
    node_count = get_path(data, "topology.node_count")
    expected = SCALE_NODE_MAP.get(scale)
    if isinstance(expected, int) and node_count != expected:
        add_error(errors, f"topology.node_count must be {expected} for {scale}")


def validate_numeric_fields(data, errors):
    seed = data.get("seed")
    if not isinstance(seed, int) or seed < 1 or seed > 99:
        add_error(errors, "seed must be integer in range 1..99")

    cluster_count = get_path(data, "topology.cluster_count")
    if not isinstance(cluster_count, int) or cluster_count <= 0:
        add_error(errors, "topology.cluster_count must be integer > 0")

    for fld in [
        "timing.sim_time_s",
        "timing.traffic_interval_s",
        "timing.aggregation_interval_s",
        "timing.dashboard_interval_s",
    ]:
        value = get_path(data, fld)
        if not isinstance(value, (int, float)) or value <= 0:
            add_error(errors, f"{fld} must be numeric > 0")


def validate_variant_consistency(data, errors):
    variant = data.get("variant")
    failure = data.get("failure_family")
    healing = data.get("healing_id")
    fail_enabled = get_path(data, "failure_injection.enabled")
    rec_enabled = get_path(data, "recovery.enabled")
    failure_time = get_path(data, "timing.failure_time_s")
    recovery_delay = get_path(data, "timing.recovery_delay_s")

    if variant == "V1":
        if failure != "F0":
            add_error(errors, "V1 requires failure_family=F0")
        if healing != "H0":
            add_error(errors, "V1 requires healing_id=H0")
        if fail_enabled is not False:
            add_error(errors, "V1 requires failure_injection.enabled=false")
        if rec_enabled is not False:
            add_error(errors, "V1 requires recovery.enabled=false")
        if failure_time is not None:
            add_error(errors, "V1 requires timing.failure_time_s=null")
        if recovery_delay is not None:
            add_error(errors, "V1 requires timing.recovery_delay_s=null")

    elif variant == "V2":
        if failure not in {"F1", "F2", "F3", "F4"}:
            add_error(errors, "V2 requires failure_family in F1..F4")
        if healing != "H0":
            add_error(errors, "V2 requires healing_id=H0")
        if fail_enabled is not True:
            add_error(errors, "V2 requires failure_injection.enabled=true")
        if rec_enabled is not False:
            add_error(errors, "V2 requires recovery.enabled=false")
        if not isinstance(failure_time, (int, float)):
            add_error(errors, "V2 requires numeric timing.failure_time_s")
        if recovery_delay is not None:
            add_error(errors, "V2 requires timing.recovery_delay_s=null")

    elif variant == "V3":
        if failure not in {"F1", "F2", "F3", "F4"}:
            add_error(errors, "V3 requires failure_family in F1..F4")
        if healing not in {"H1", "H2", "H3", "H4"}:
            add_error(errors, "V3 requires healing_id in H1..H4")
        if fail_enabled is not True:
            add_error(errors, "V3 requires failure_injection.enabled=true")
        if rec_enabled is not True:
            add_error(errors, "V3 requires recovery.enabled=true")
        if not isinstance(failure_time, (int, float)):
            add_error(errors, "V3 requires numeric timing.failure_time_s")
        if not isinstance(recovery_delay, (int, float)) or recovery_delay <= 0:
            add_error(errors, "V3 requires numeric timing.recovery_delay_s > 0")


def validate_architecture_b(data, allow_planned_b, errors):
    architecture = data.get("architecture")
    runnable = data.get("runnable")

    if architecture != "B":
        return

    # M4 enables runnable Architecture B. Keep a narrow check only for specs that
    # explicitly mark B as planned/non-runnable.
    if runnable is True:
        return

    if not allow_planned_b:
        add_error(
            errors,
            "Non-runnable Architecture B specs require --allow-planned-b",
        )
        return

    reserved = data.get("reserved_architecture_b")
    if not isinstance(reserved, dict):
        add_error(errors, "Non-runnable Architecture B spec requires reserved_architecture_b object")
        return

    planned_status = reserved.get("planned_status")
    if planned_status not in {"planned", "inactive"}:
        add_error(errors, "reserved_architecture_b.planned_status must be planned or inactive")


def validate_file(spec_path: Path, allow_planned_b: bool) -> int:
    errors = []

    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: unable to parse JSON: {exc}")
        return 2

    if not isinstance(data, dict):
        print("FAIL: top-level JSON must be an object")
        return 2

    validate_required(data, errors)
    validate_enums(data, errors)
    validate_name_and_identity(spec_path, data, errors)
    validate_scale_node_count(data, errors)
    validate_numeric_fields(data, errors)
    validate_variant_consistency(data, errors)
    validate_architecture_b(data, allow_planned_b, errors)

    if errors:
        print(f"FAIL: {spec_path}")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"PASS: {spec_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate M1 run-spec JSON files")
    parser.add_argument("spec", nargs="+", help="Path(s) to run-spec JSON file(s)")
    parser.add_argument(
        "--allow-planned-b",
        action="store_true",
        help="Allow planned/non-runnable Architecture B specs",
    )
    args = parser.parse_args()

    exit_code = 0
    for spec in args.spec:
        code = validate_file(Path(spec), args.allow_planned_b)
        if code != 0:
            exit_code = code
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
