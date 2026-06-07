#!/usr/bin/env python3
"""Run S9/S10 production chunks with export, verification, cleanup, and merge."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
ML_EXPORTS_DIR = ROOT / "ml_exports"

SCALE_TO_DIR = {
    "S9": "S9_4500",
    "S10": "S10_5000",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", required=True, choices=sorted(SCALE_TO_DIR))
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-end", type=int, default=50)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--min-free-gb", type=float, default=10.0)
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.scale not in SCALE_TO_DIR:
        parser.error("Only S9 and S10 are supported.")
    if args.chunk_size != 5:
        parser.error("This orchestrator supports only 5-seed chunks.")
    if args.seed_start < 1 or args.seed_end > 50 or args.seed_start > args.seed_end:
        parser.error("Seeds must satisfy 1 <= seed-start <= seed-end <= 50.")
    return args


def scale_folder(scale: str) -> str:
    return SCALE_TO_DIR[scale]


def chunk_ranges(seed_start: int, seed_end: int, chunk_size: int) -> list[tuple[int, int]]:
    chunks: list[tuple[int, int]] = []
    current = seed_start
    while current <= seed_end:
        end = min(current + chunk_size - 1, seed_end)
        chunks.append((current, end))
        current = end + 1
    return chunks


def chunk_tag(start: int, end: int) -> str:
    return f"part{start:02d}_{end:02d}"


def output_subdir(start: int, end: int) -> str:
    return f"outputs_production_50seed_{chunk_tag(start, end)}"


def chunk_csv_path(scale: str, start: int, end: int) -> Path:
    return ML_EXPORTS_DIR / f"production_v3_{scale_folder(scale)}_{chunk_tag(start, end)}.csv"


def final_csv_path(scale: str) -> Path:
    return ML_EXPORTS_DIR / f"production_v3_{scale_folder(scale)}.csv"


def raw_output_dir(scale: str, start: int, end: int) -> Path:
    return ROOT / "runs" / scale_folder(scale) / output_subdir(start, end)


def print_disk_status() -> float:
    free_gb = shutil.disk_usage(ROOT).free / (1024 ** 3)
    print(subprocess.run(["df", "-h", "/"], check=True, text=True, capture_output=True).stdout.strip())
    print(
        subprocess.run(["df", "-h", "/home/cyfer/FYP"], check=True, text=True, capture_output=True).stdout.strip()
    )
    print(f"free_gb_exact={free_gb:.2f}")
    return free_gb


def ensure_disk(min_free_gb: float) -> None:
    free_gb = print_disk_status()
    if free_gb < min_free_gb:
        raise RuntimeError(f"Free space {free_gb:.2f} GB is below threshold {min_free_gb:.2f} GB.")


def run_command(cmd: list[str], dry_run: bool = False) -> None:
    print("$ " + " ".join(str(part) for part in cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True, cwd=ROOT)


def count_run_dirs(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.iterdir() if p.is_dir() and p.name.startswith("run_campaign_v3_"))


def verify_chunk_csv(path: Path, expected_rows: int, seeds: Iterable[int]) -> tuple[int, int, Counter[str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    run_ids = [row.get("run_id", "") for row in rows]
    seed_counts = Counter(row.get("seed", "") for row in rows)
    dup_count = len(run_ids) - len(set(run_ids))

    if len(rows) != expected_rows:
        raise RuntimeError(f"{path.name}: expected {expected_rows} rows, found {len(rows)}")
    if dup_count != 0:
        raise RuntimeError(f"{path.name}: duplicate_run_id={dup_count}")
    for seed in seeds:
        count = seed_counts.get(str(seed), 0)
        if count != 204:
            raise RuntimeError(f"{path.name}: seed {seed} expected 204 rows, found {count}")
    return len(rows), dup_count, seed_counts


def merge_scale_csv(scale: str, chunk_paths: list[Path]) -> Path:
    output = final_csv_path(scale)
    fieldnames = None
    rows: list[dict[str, str]] = []

    for path in chunk_paths:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if fieldnames is None:
                fieldnames = reader.fieldnames
            rows.extend(reader)

    assert fieldnames is not None
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            clean = {}
            for key in fieldnames:
                value = row.get(key, "")
                clean[key] = value.replace("\r", " ").replace("\n", " ") if isinstance(value, str) else value
            writer.writerow(clean)
    return output


def verify_merged_csv(path: Path, expected_rows: int, seeds: Iterable[int]) -> tuple[int, int]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    run_ids = [row.get("run_id", "") for row in rows]
    dup_count = len(run_ids) - len(set(run_ids))
    seed_counts = Counter(row.get("seed", "") for row in rows)

    if len(rows) != expected_rows:
        raise RuntimeError(f"{path.name}: expected {expected_rows} rows, found {len(rows)}")
    if dup_count != 0:
        raise RuntimeError(f"{path.name}: duplicate_run_id={dup_count}")
    for seed in seeds:
        count = seed_counts.get(str(seed), 0)
        if count != 204:
            raise RuntimeError(f"{path.name}: seed {seed} expected 204 rows, found {count}")
    return len(rows), dup_count


def main() -> int:
    args = parse_args()
    chunks = chunk_ranges(args.seed_start, args.seed_end, args.chunk_size)
    expected_chunk_rows = 1020
    requested_chunk_csvs: list[Path] = []

    print(f"Scale: {args.scale}")
    print(f"Scale folder: {scale_folder(args.scale)}")
    print(f"Requested chunks: {len(chunks)}")

    for index, (start, end) in enumerate(chunks, start=1):
        tag = chunk_tag(start, end)
        out_subdir = output_subdir(start, end)
        raw_dir = raw_output_dir(args.scale, start, end)
        csv_path = chunk_csv_path(args.scale, start, end)

        print()
        print(f"Scale: {args.scale}")
        print(f"Current chunk: {tag}")
        print(f"Completed chunks: {index - 1} / {len(chunks)}")
        print(f"Pending chunks: {len(chunks) - (index - 1)}")
        print(f"Expected chunk rows: {expected_chunk_rows}")
        ensure_disk(args.min_free_gb)

        if args.dry_run:
            print(f"Dry run: would execute chunk {tag}")
            print(
                " ".join(
                    [
                        "tools/run_chunk_with_progress.sh",
                        f"--scale {args.scale}",
                        f"--seed-start {start}",
                        f"--seed-end {end}",
                        f"--output-subdir {out_subdir}",
                        "--target-runs 1020",
                        f"--min-free-gb {args.min_free_gb}",
                        f"--poll-seconds {args.poll_seconds}",
                    ]
                )
            )
            continue

        run_command(
            [
                str(TOOLS_DIR / "run_chunk_with_progress.sh"),
                "--scale",
                args.scale,
                "--seed-start",
                str(start),
                "--seed-end",
                str(end),
                "--output-subdir",
                out_subdir,
                "--target-runs",
                "1020",
                "--min-free-gb",
                str(args.min_free_gb),
                "--poll-seconds",
                str(args.poll_seconds),
            ]
        )

        raw_count = count_run_dirs(raw_dir)
        if raw_count != expected_chunk_rows:
            raise RuntimeError(f"{tag}: expected {expected_chunk_rows} raw folders, found {raw_count}")

        run_command(
            [
                sys.executable,
                str(TOOLS_DIR / "export_production_dataset_v3.py"),
                "--scale",
                args.scale,
                "--output-subdir",
                out_subdir,
            ]
        )

        exported_scale_csv = final_csv_path(args.scale)
        exported_scale_csv.rename(csv_path)

        rows, dup_count, seed_counts = verify_chunk_csv(csv_path, expected_chunk_rows, range(start, end + 1))
        print("Chunk complete")
        print(f"CSV verified: rows={rows} duplicate_run_id={dup_count}")
        for seed in range(start, end + 1):
            print(f"seed_{seed}={seed_counts[str(seed)]}")

        requested_chunk_csvs.append(csv_path)

        if not args.keep_raw:
            shutil.rmtree(raw_dir)
            print("Raw folder deleted")
        else:
            print("Raw folder kept (--keep-raw set)")

        ensure_disk(args.min_free_gb)
        print("Next chunk starting")

    if args.dry_run:
        print()
        print("Dry run complete")
        return 0

    merged = merge_scale_csv(args.scale, requested_chunk_csvs)
    expected_total_rows = 1020 * len(requested_chunk_csvs)
    rows, dup_count = verify_merged_csv(merged, expected_total_rows, range(args.seed_start, args.seed_end + 1))
    print()
    print(f"Merged CSV: {merged}")
    print(f"Merged rows: {rows}")
    print(f"Merged duplicate_run_id: {dup_count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
