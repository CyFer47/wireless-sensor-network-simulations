#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
PROGRESS_PATH = REPO_ROOT / "evidence" / "production_v3_50seed_progress.csv"
SCALE_FOLDERS = {
    "S1": "S1_50",
    "S2": "S2_100",
    "S3": "S3_200",
    "S4": "S4_400",
    "S5": "S5_800",
    "S6": "S6_1600",
    "S7": "S7_3200",
    "S8": "S8_4000",
    "S9": "S9_4500",
    "S10": "S10_5000",
}
PROFILES = ["M1_BALANCED", "M2_LONG_LINK", "M3_IMBALANCED"]
ARCHITECTURES = ["A", "B"]
LOADS = ["L1", "L2"]
SCENARIOS = [
    ("F0", "H0"),
    ("F1", "H0"),
    ("F2", "H0"),
    ("F3", "H0"),
    ("F4", "H0"),
    ("F1", "H1"),
    ("F1", "H3"),
    ("F1", "H4"),
    ("F2", "H1"),
    ("F2", "H3"),
    ("F2", "H4"),
    ("F3", "H1"),
    ("F3", "H3"),
    ("F3", "H4"),
    ("F4", "H1"),
    ("F4", "H3"),
    ("F4", "H4"),
]

PROGRESS_COLUMNS = [
    "timestamp",
    "scale",
    "scale_folder",
    "profile",
    "seed",
    "architecture",
    "load",
    "failure_family",
    "healing_id",
    "spec_path",
    "map_path",
    "status",
    "return_code",
    "message",
]


@dataclass(frozen=True)
class Task:
    scale: str
    scale_folder: str
    profile: str
    seed: int
    architecture: str
    load: str
    failure_family: str
    healing_id: str
    spec_path: Path
    map_path: Path


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_progress_header() -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PROGRESS_PATH.exists():
        with PROGRESS_PATH.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=PROGRESS_COLUMNS)
            writer.writeheader()


def append_progress(row: dict[str, object]) -> None:
    ensure_progress_header()
    with PROGRESS_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROGRESS_COLUMNS)
        writer.writerow({column: row.get(column, "") for column in PROGRESS_COLUMNS})


def scale_folder_for(scale: str) -> str:
    return SCALE_FOLDERS[scale]


def bytes_to_gb(value: int) -> float:
    return value / (1024 ** 3)


def free_disk_gb(path: Path) -> float:
    return bytes_to_gb(shutil.disk_usage(path).free)


def read_summary(path: Path) -> dict | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        data = load_json(path)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def run_completed(output_dir: Path) -> bool:
    for summary in output_dir.rglob("run_summary.json"):
        if read_summary(summary) is not None:
            return True
    return False


def build_tasks(scale: str, seed_start: int, seed_end: int) -> list[Task]:
    scale_folder = scale_folder_for(scale)
    root = REPO_ROOT / "runs" / scale_folder
    tasks: list[Task] = []
    for profile in PROFILES:
        for seed in range(seed_start, seed_end + 1):
            map_path = root / "maps" / profile / f"map_{scale}_{profile}_seed{seed:03d}"
            spec_root = root / "specs" / profile
            for architecture in ARCHITECTURES:
                for load in LOADS:
                    for failure_family, healing_id in SCENARIOS:
                        spec_path = spec_root / f"campaign_v3_{scale}_{profile}_{architecture}_{load}_{failure_family}_{healing_id}_seed{seed:03d}.json"
                        tasks.append(
                            Task(
                                scale=scale,
                                scale_folder=scale_folder,
                                profile=profile,
                                seed=seed,
                                architecture=architecture,
                                load=load,
                                failure_family=failure_family,
                                healing_id=healing_id,
                                spec_path=spec_path,
                                map_path=map_path,
                            )
                        )
    return tasks


def task_output_prefix(task: Task) -> str:
    return (
        f"run_campaign_v3_{task.scale}_{task.profile}_{task.architecture}_{task.load}"
        f"_{task.failure_family}_{task.healing_id}_seed{task.seed:03d}"
    )


def find_missing_reason(task: Task) -> str | None:
    if not task.spec_path.exists():
        return "missing_spec"
    if not task.map_path.exists():
        return "missing_map"
    return None


def should_skip_existing(task: Task, output_root: Path) -> bool:
    prefix = task_output_prefix(task)
    for candidate in sorted(output_root.glob(f"{prefix}_*")):
        summary = read_summary(candidate / "run_summary.json")
        if summary is not None:
            return True
    return False


def run_one(task: Task, ns3_root: Path, output_root: Path) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "run_from_spec_v3.py"),
        "--spec",
        str(task.spec_path),
        "--map",
        str(task.map_path),
        "--ns3-root",
        str(ns3_root),
        "--output-root",
        str(output_root),
    ]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if proc.returncode == 0:
        return 0, "submitted"
    return proc.returncode, f"run_failed_rc_{proc.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the resumable V3 50-seed production campaign")
    parser.add_argument("--scale", required=True, choices=[*SCALE_FOLDERS.keys(), "all"])
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-end", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--ns3-root", default="/home/cyfer/ns-allinone-3.42/ns-3.42")
    parser.add_argument("--output-subdir", default="outputs_production_50seed")
    parser.add_argument("--min-free-gb", type=float, default=20.0)
    args = parser.parse_args()

    scales = list(SCALE_FOLDERS.keys()) if args.scale == "all" else [args.scale]
    ns3_root = Path(args.ns3_root).resolve()
    if not ns3_root.exists():
        print(f"ERROR: ns3 root not found: {ns3_root}", file=sys.stderr)
        return 2

    ensure_progress_header()

    all_tasks: list[Task] = []
    for scale in scales:
        all_tasks.extend(build_tasks(scale, args.seed_start, args.seed_end))

    output_subdir = args.output_subdir

    expected = len(all_tasks)
    completed_existing = 0
    submitted = 0
    failed = 0
    missing_spec = 0
    missing_map = 0

    for task in all_tasks:
        output_root = REPO_ROOT / "runs" / task.scale_folder / output_subdir
        output_root.mkdir(parents=True, exist_ok=True)

        missing_reason = find_missing_reason(task)
        if missing_reason == "missing_spec":
            missing_spec += 1
            append_progress({
                "timestamp": timestamp(),
                "scale": task.scale,
                "scale_folder": task.scale_folder,
                "profile": task.profile,
                "seed": task.seed,
                "architecture": task.architecture,
                "load": task.load,
                "failure_family": task.failure_family,
                "healing_id": task.healing_id,
                "spec_path": str(task.spec_path),
                "map_path": str(task.map_path),
                "status": "missing_spec",
                "return_code": "",
                "message": "spec file missing",
            })
            continue
        if missing_reason == "missing_map":
            missing_map += 1
            append_progress({
                "timestamp": timestamp(),
                "scale": task.scale,
                "scale_folder": task.scale_folder,
                "profile": task.profile,
                "seed": task.seed,
                "architecture": task.architecture,
                "load": task.load,
                "failure_family": task.failure_family,
                "healing_id": task.healing_id,
                "spec_path": str(task.spec_path),
                "map_path": str(task.map_path),
                "status": "missing_map",
                "return_code": "",
                "message": "map package missing",
            })
            continue

        if args.skip_existing and should_skip_existing(task, output_root):
            completed_existing += 1
            append_progress({
                "timestamp": timestamp(),
                "scale": task.scale,
                "scale_folder": task.scale_folder,
                "profile": task.profile,
                "seed": task.seed,
                "architecture": task.architecture,
                "load": task.load,
                "failure_family": task.failure_family,
                "healing_id": task.healing_id,
                "spec_path": str(task.spec_path),
                "map_path": str(task.map_path),
                "status": "skipped_existing",
                "return_code": 0,
                "message": "valid output already exists",
            })
            continue

        free_gb = free_disk_gb(REPO_ROOT)
        if free_gb < args.min_free_gb:
            append_progress({
                "timestamp": timestamp(),
                "scale": task.scale,
                "scale_folder": task.scale_folder,
                "profile": task.profile,
                "seed": task.seed,
                "architecture": task.architecture,
                "load": task.load,
                "failure_family": task.failure_family,
                "healing_id": task.healing_id,
                "spec_path": str(task.spec_path),
                "map_path": str(task.map_path),
                "status": "stopped_low_disk",
                "return_code": "",
                "message": f"free disk {free_gb:.2f} GB below threshold {args.min_free_gb:.2f} GB",
            })
            break

        if args.max_runs is not None and submitted >= args.max_runs:
            append_progress({
                "timestamp": timestamp(),
                "scale": task.scale,
                "scale_folder": task.scale_folder,
                "profile": task.profile,
                "seed": task.seed,
                "architecture": task.architecture,
                "load": task.load,
                "failure_family": task.failure_family,
                "healing_id": task.healing_id,
                "spec_path": str(task.spec_path),
                "map_path": str(task.map_path),
                "status": "stopped_max_runs",
                "return_code": "",
                "message": f"max-runs limit reached at {args.max_runs}",
            })
            break

        if args.dry_run:
            submitted += 1
            append_progress({
                "timestamp": timestamp(),
                "scale": task.scale,
                "scale_folder": task.scale_folder,
                "profile": task.profile,
                "seed": task.seed,
                "architecture": task.architecture,
                "load": task.load,
                "failure_family": task.failure_family,
                "healing_id": task.healing_id,
                "spec_path": str(task.spec_path),
                "map_path": str(task.map_path),
                "status": "dry_run",
                "return_code": 0,
                "message": "dry run only",
            })
            continue

        rc, message = run_one(task, ns3_root, output_root)
        submitted += 1
        status = "submitted" if rc == 0 else "failed"
        if rc != 0:
            failed += 1
        append_progress({
            "timestamp": timestamp(),
            "scale": task.scale,
            "scale_folder": task.scale_folder,
            "profile": task.profile,
            "seed": task.seed,
            "architecture": task.architecture,
            "load": task.load,
            "failure_family": task.failure_family,
            "healing_id": task.healing_id,
            "spec_path": str(task.spec_path),
            "map_path": str(task.map_path),
            "status": status,
            "return_code": rc,
            "message": message,
        })

    remaining = expected - completed_existing - submitted - missing_spec - missing_map
    print(f"expected={expected}")
    print(f"completed_existing={completed_existing}")
    print(f"submitted={submitted}")
    print(f"failed={failed}")
    print(f"missing_spec={missing_spec}")
    print(f"missing_map={missing_map}")
    print(f"remaining={remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())