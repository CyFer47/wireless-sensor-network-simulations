#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
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
CSV_COLUMNS = [
    "run_id",
    "external_run_id",
    "scale",
    "node_count",
    "cluster_count",
    "bs_count",
    "map_profile",
    "seed",
    "architecture",
    "load",
    "failure_family",
    "healing_id",
    "variant",
    "map_id",
    "map_signature",
    "mean_node_to_ch_distance",
    "max_node_to_ch_distance",
    "mean_ch_to_bs_distance",
    "max_ch_to_bs_distance",
    "cluster_size_mean",
    "cluster_size_max",
    "cluster_size_cv",
    "long_link_ratio",
    "failure_time_s",
    "recovery_applied_delay_s",
    "recovery_applied_s",
    "recovery_event_time_s",
    "first_recovered_aggregate_s",
    "traffic_recovery_delay_s",
    "recovery_stress_score",
    "recovery_map_profile_penalty_s",
    "recovery_queue_norm",
    "recovery_cluster_norm",
    "recovery_energy_norm",
    "recovery_distance_norm",
    "consumed_j",
    "avg_res_j",
    "min_res_j",
    "low_nodes",
    "raw_tx",
    "raw_rx",
    "raw_delivery_ratio",
    "agg_tx",
    "agg_rx",
    "agg_delivery_ratio",
    "pending_raw_total",
    "failed_chs",
    "recovered_clusters",
    "candidate_group_key",
    "is_healing_case",
    "is_baseline",
    "is_failure_no_healing",
    "source_output_dir",
]


def scale_list(scale: str) -> list[str]:
    return list(SCALE_FOLDERS.keys()) if scale == "all" else [scale]


def load_json(path: Path) -> dict | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def to_blank(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def resolve_map_manifest(scale_folder: str, meta: dict) -> dict | None:
    map_id = meta.get("map_id")
    if not map_id:
        return None
    map_root = REPO_ROOT / "runs" / scale_folder / "maps"
    map_profile = meta.get("map_profile")
    if map_profile:
        manifest = load_json(map_root / str(map_profile) / str(map_id) / "manifest.json")
        if manifest is not None:
            return manifest
    for manifest_path in map_root.glob(f"*/{map_id}/manifest.json"):
        manifest = load_json(manifest_path)
        if manifest is not None:
            return manifest
    return None


def row_from_run(scale_folder: str, run_dir: Path) -> tuple[dict[str, object] | None, list[str]]:
    summary = load_json(run_dir / "run_summary.json")
    if summary is None:
        return None, [f"missing or invalid run_summary.json in {run_dir}"]
    meta = load_json(run_dir / "run_meta.json") or {}
    manifest = resolve_map_manifest(scale_folder, meta) or {}

    scale = meta.get("scale") or manifest.get("scale_id") or scale_folder.split("_")[0]
    map_profile = meta.get("map_profile") or manifest.get("map_profile") or ""
    seed = meta.get("seed")
    failure_family = meta.get("failure_family")
    healing_id = meta.get("healing_id")

    candidate_group_key = "|".join([to_blank(scale), to_blank(map_profile), to_blank(seed), to_blank(meta.get("architecture")), to_blank(meta.get("load")), to_blank(failure_family)])

    raw_tx = summary.get("raw_tx_cum")
    raw_rx = summary.get("raw_rx_cum")
    agg_tx = summary.get("agg_tx_cum")
    agg_rx = summary.get("agg_rx_cum")

    row = {
        "run_id": meta.get("run_spec_id") or "",
        "external_run_id": summary.get("external_run_id") or meta.get("external_run_id") or run_dir.name.replace("run_", "", 1),
        "scale": scale,
        "node_count": meta.get("node_count") or manifest.get("counts", {}).get("node_count"),
        "cluster_count": meta.get("cluster_count") or manifest.get("counts", {}).get("ch_count"),
        "bs_count": manifest.get("counts", {}).get("bs_count"),
        "map_profile": map_profile,
        "seed": seed,
        "architecture": meta.get("architecture"),
        "load": meta.get("load"),
        "failure_family": failure_family,
        "healing_id": healing_id,
        "variant": meta.get("variant"),
        "map_id": meta.get("map_id") or manifest.get("map_id"),
        "map_signature": meta.get("map_signature") or manifest.get("deterministic_signature_sha256"),
        "mean_node_to_ch_distance": manifest.get("metrics", {}).get("mean_node_to_ch_distance"),
        "max_node_to_ch_distance": manifest.get("metrics", {}).get("max_node_to_ch_distance"),
        "mean_ch_to_bs_distance": manifest.get("metrics", {}).get("mean_ch_to_bs_distance"),
        "max_ch_to_bs_distance": manifest.get("metrics", {}).get("max_ch_to_bs_distance"),
        "cluster_size_mean": manifest.get("metrics", {}).get("cluster_size_mean"),
        "cluster_size_max": manifest.get("metrics", {}).get("cluster_size_max"),
        "cluster_size_cv": manifest.get("metrics", {}).get("cluster_size_cv"),
        "long_link_ratio": manifest.get("metrics", {}).get("long_link_ratio"),
        "failure_time_s": meta.get("failure_time_s") or summary.get("failure_time_s"),
        "recovery_applied_delay_s": meta.get("recovery_applied_delay_s") or summary.get("recovery_applied_delay_s"),
        "recovery_applied_s": meta.get("recovery_applied_s") or summary.get("recovery_applied_s"),
        "recovery_event_time_s": meta.get("recovery_event_time_s") or summary.get("recovery_event_time_s"),
        "first_recovered_aggregate_s": summary.get("first_recovered_aggregate_s"),
        "traffic_recovery_delay_s": summary.get("traffic_recovery_delay_s"),
        "recovery_stress_score": meta.get("recovery_stress_score"),
        "recovery_map_profile_penalty_s": meta.get("recovery_map_profile_penalty_s") or summary.get("recovery_map_profile_penalty_s"),
        "recovery_queue_norm": meta.get("recovery_queue_norm"),
        "recovery_cluster_norm": meta.get("recovery_cluster_norm"),
        "recovery_energy_norm": meta.get("recovery_energy_norm"),
        "recovery_distance_norm": meta.get("recovery_distance_norm"),
        "consumed_j": summary.get("consumed_j"),
        "avg_res_j": summary.get("avg_res_j"),
        "min_res_j": summary.get("min_res_j"),
        "low_nodes": summary.get("low_nodes"),
        "raw_tx": raw_tx,
        "raw_rx": raw_rx,
        "raw_delivery_ratio": (float(raw_rx) / float(raw_tx)) if raw_tx not in {None, "", 0, "0"} else "",
        "agg_tx": agg_tx,
        "agg_rx": agg_rx,
        "agg_delivery_ratio": (float(agg_rx) / float(agg_tx)) if agg_tx not in {None, "", 0, "0"} else "",
        "pending_raw_total": summary.get("pending_raw_total"),
        "failed_chs": summary.get("failed_chs"),
        "recovered_clusters": summary.get("recovered_clusters"),
        "candidate_group_key": candidate_group_key,
        "is_healing_case": healing_id not in {None, "", "H0"},
        "is_baseline": failure_family == "F0" and healing_id == "H0",
        "is_failure_no_healing": failure_family != "F0" and healing_id == "H0",
        "source_output_dir": str(run_dir),
    }
    return row, []


def export_scale(scale: str, output_dir: Path, output_subdir: str) -> tuple[Path, list[dict[str, object]], list[str]]:
    scale_folder = SCALE_FOLDERS[scale]
    outputs = REPO_ROOT / "runs" / scale_folder / output_subdir
    rows: list[dict[str, object]] = []
    warnings: list[str] = []
    seen_run_ids: Counter[str] = Counter()
    seen_external_ids: Counter[str] = Counter()

    for run_dir in sorted(outputs.glob("run_campaign_v3_*")):
        if not run_dir.is_dir():
            continue
        row, row_warnings = row_from_run(scale_folder, run_dir)
        warnings.extend(row_warnings)
        if row is None:
            continue
        seen_run_ids[str(row["run_id"])] += 1
        seen_external_ids[str(row["external_run_id"])] += 1
        rows.append(row)

    duplicate_run_ids = [run_id for run_id, count in seen_run_ids.items() if count > 1]
    duplicate_external_ids = [run_id for run_id, count in seen_external_ids.items() if count > 1]
    if duplicate_run_ids:
        warnings.append(f"duplicate run_id values in {scale_folder}: {', '.join(sorted(duplicate_run_ids)[:10])}")
    if duplicate_external_ids:
        warnings.append(f"duplicate external_run_id values in {scale_folder}: {', '.join(sorted(duplicate_external_ids)[:10])}")

    out_path = output_dir / f"production_v3_{scale_folder}.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: to_blank(row.get(column)) for column in CSV_COLUMNS})

    return out_path, rows, warnings


def summarize_rows(scale: str, rows: list[dict[str, object]]) -> list[str]:
    missing = [column for column in CSV_COLUMNS if any(row.get(column) in {None, ""} for row in rows)]
    groups = Counter((row.get("map_profile"), row.get("architecture"), row.get("load"), row.get("failure_family"), row.get("healing_id")) for row in rows)
    lines = [
        f"[{scale}] rows={len(rows)}",
        f"[{scale}] missing_fields={', '.join(sorted(set(missing))[:12]) if missing else 'none'}",
        f"[{scale}] unique_groups={len(groups)}",
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Export completed V3 production runs to CSV")
    parser.add_argument("--scale", required=True, choices=[*SCALE_FOLDERS.keys(), "all"])
    parser.add_argument("--output-dir", default="ml_exports")
    parser.add_argument("--output-subdir", default="outputs_production_50seed")
    args = parser.parse_args()

    scales = scale_list(args.scale)
    output_dir = Path(args.output_dir).resolve()
    export_scale.output_subdir = args.output_subdir
    all_rows: list[dict[str, object]] = []
    all_warnings: list[str] = []

    for scale in scales:
        out_path, rows, warnings = export_scale(scale, output_dir, args.output_subdir)
        all_rows.extend(rows)
        all_warnings.extend(warnings)
        for line in summarize_rows(scale, rows):
            print(line)
        print(f"[{scale}] export={out_path}")

    if args.scale == "all":
        combined_path = output_dir / "production_v3_50seed_dataset.csv"
        with combined_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in all_rows:
                writer.writerow({column: to_blank(row.get(column)) for column in CSV_COLUMNS})
        print(f"[all] export={combined_path}")

    if all_warnings:
        for warning in sorted(set(all_warnings)):
            print(f"WARNING: {warning}")

    print(f"row_count={len(all_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())