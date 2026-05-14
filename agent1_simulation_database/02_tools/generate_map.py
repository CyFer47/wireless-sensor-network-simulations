#!/usr/bin/env python3
"""Deterministic topology/mapping generator for M2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

MAP_SCHEMA_VERSION = "m2_map_v1"
BOUNDARY_MARGIN_M = 2.0


@dataclass(frozen=True)
class ScaleRule:
    node_count: int
    ch_count: int
    bs_count: int
    width_m: float
    height_m: float
    min_spacing_m: float


SCALE_RULES: Dict[str, ScaleRule] = {
    "S1": ScaleRule(50, 3, 1, 100.0, 100.0, 5.0),
    "S2": ScaleRule(100, 6, 1, 150.0, 150.0, 4.0),
    "S3": ScaleRule(200, 10, 1, 220.0, 220.0, 3.5),
    "S4": ScaleRule(400, 20, 1, 320.0, 320.0, 3.0),
    "S5": ScaleRule(800, 32, 2, 450.0, 450.0, 2.5),
    "S6": ScaleRule(1600, 64, 3, 640.0, 640.0, 2.0),
    "S7": ScaleRule(3000, 120, 4, 880.0, 880.0, 2.0),
    "S8": ScaleRule(3500, 140, 5, 950.0, 950.0, 2.0),
    "S9": ScaleRule(4000, 160, 5, 1020.0, 1020.0, 2.0),
    "S10": ScaleRule(4500, 180, 6, 1080.0, 1080.0, 2.0),
    "S11": ScaleRule(5000, 200, 6, 1150.0, 1150.0, 2.0),
}


def _fmt_float(v: float) -> str:
    return f"{v:.3f}"


def _distance_sq(ax: float, ay: float, bx: float, by: float) -> float:
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def _generate_sensor_nodes(scale_rule: ScaleRule, seed: int) -> List[dict]:
    rng = random.Random(seed)
    nodes: List[dict] = []

    min_x = BOUNDARY_MARGIN_M
    min_y = BOUNDARY_MARGIN_M
    max_x = scale_rule.width_m - BOUNDARY_MARGIN_M
    max_y = scale_rule.height_m - BOUNDARY_MARGIN_M
    min_dist_sq = scale_rule.min_spacing_m * scale_rule.min_spacing_m

    max_trials_per_node = 20000

    for node_id in range(scale_rule.node_count):
        placed = False
        for _ in range(max_trials_per_node):
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)

            ok = True
            for other in nodes:
                if _distance_sq(x, y, other["x_m"], other["y_m"]) < min_dist_sq:
                    ok = False
                    break

            if ok:
                nodes.append({"node_id": node_id, "x_m": x, "y_m": y})
                placed = True
                break

        if not placed:
            raise RuntimeError(
                f"Unable to place node {node_id} for scale with min spacing {scale_rule.min_spacing_m}."
            )

    return nodes


def _choose_ch_nodes(nodes: List[dict], ch_count: int, seed: int) -> List[int]:
    # Deterministic farthest-point sampling on sensor node coordinates.
    pick_rng = random.Random(seed * 10007 + 97)
    first = pick_rng.randrange(len(nodes))
    chosen = [first]
    chosen_set = {first}

    while len(chosen) < ch_count:
        best_idx = None
        best_score = -1.0

        for idx, node in enumerate(nodes):
            if idx in chosen_set:
                continue
            min_d = float("inf")
            for cidx in chosen:
                c = nodes[cidx]
                d = _distance_sq(node["x_m"], node["y_m"], c["x_m"], c["y_m"])
                if d < min_d:
                    min_d = d

            if min_d > best_score:
                best_score = min_d
                best_idx = idx
            elif math.isclose(min_d, best_score, rel_tol=0.0, abs_tol=1e-12):
                if best_idx is None or idx < best_idx:
                    best_idx = idx

        if best_idx is None:
            raise RuntimeError("Failed to select CH nodes deterministically")

        chosen.append(best_idx)
        chosen_set.add(best_idx)

    # Cluster IDs follow deterministic order of selected node IDs.
    ch_node_ids = sorted(nodes[idx]["node_id"] for idx in chosen)
    return ch_node_ids


def _bs_positions(scale_rule: ScaleRule) -> List[Tuple[float, float]]:
    w = scale_rule.width_m
    h = scale_rule.height_m
    if scale_rule.bs_count == 1:
        return [(w * 0.5, h * 0.5)]
    if scale_rule.bs_count == 2:
        return [(w * 0.25, h * 0.5), (w * 0.75, h * 0.5)]
    if scale_rule.bs_count == 3:
        return [(w * 0.20, h * 0.50), (w * 0.80, h * 0.50), (w * 0.50, h * 0.82)]
    if scale_rule.bs_count == 4:
        return [
            (w * 0.20, h * 0.25),
            (w * 0.80, h * 0.25),
            (w * 0.20, h * 0.75),
            (w * 0.80, h * 0.75),
        ]
    if scale_rule.bs_count == 5:
        return [
            (w * 0.20, h * 0.20),
            (w * 0.80, h * 0.20),
            (w * 0.20, h * 0.80),
            (w * 0.80, h * 0.80),
            (w * 0.50, h * 0.50),
        ]
    if scale_rule.bs_count == 6:
        return [
            (w * 0.20, h * 0.25),
            (w * 0.50, h * 0.25),
            (w * 0.80, h * 0.25),
            (w * 0.20, h * 0.75),
            (w * 0.50, h * 0.75),
            (w * 0.80, h * 0.75),
        ]
    raise RuntimeError(f"Unsupported BS count: {scale_rule.bs_count}")


def _node_cluster_map(nodes: List[dict], cluster_ch: Dict[int, int]) -> List[dict]:
    # Build lookup: node_id -> (x, y)
    node_lookup = {n["node_id"]: (n["x_m"], n["y_m"]) for n in nodes}

    mapping = []
    for n in nodes:
        node_id = n["node_id"]
        if node_id in cluster_ch.values():
            # CH maps to own cluster.
            cluster_id = next(cid for cid, ch in cluster_ch.items() if ch == node_id)
            mapping.append({"node_id": node_id, "cluster_id": cluster_id, "is_ch": 1})
            continue

        best_cluster = None
        best_dist = float("inf")
        nx, ny = node_lookup[node_id]

        for cid in sorted(cluster_ch.keys()):
            ch_node_id = cluster_ch[cid]
            cx, cy = node_lookup[ch_node_id]
            d = _distance_sq(nx, ny, cx, cy)
            if d < best_dist:
                best_dist = d
                best_cluster = cid
            elif math.isclose(d, best_dist, rel_tol=0.0, abs_tol=1e-12) and best_cluster is not None and cid < best_cluster:
                best_cluster = cid

        mapping.append({"node_id": node_id, "cluster_id": int(best_cluster), "is_ch": 0})

    mapping.sort(key=lambda r: r["node_id"])
    return mapping


def _deterministic_signature(nodes: List[dict], ch_bs: List[dict], mapping: List[dict]) -> str:
    payload = {
        "nodes": [
            {"node_id": r["node_id"], "x_m": _fmt_float(r["x_m"]), "y_m": _fmt_float(r["y_m"])} for r in nodes
        ],
        "ch_bs": [
            {
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "node_id": r["node_id"],
                "x_m": _fmt_float(r["x_m"]),
                "y_m": _fmt_float(r["y_m"]),
            }
            for r in ch_bs
        ],
        "node_cluster_map": mapping,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_map_data(scale_id: str, seed: int, map_id: str | None = None) -> dict:
    if scale_id not in SCALE_RULES:
        raise ValueError(f"Unsupported scale_id: {scale_id}")
    if seed < 1 or seed > 99:
        raise ValueError("seed must be in range 1..99")

    rule = SCALE_RULES[scale_id]
    if map_id is None:
        map_id = f"map_{scale_id}_seed{seed:02d}"

    nodes = _generate_sensor_nodes(rule, seed)
    ch_node_ids = _choose_ch_nodes(nodes, rule.ch_count, seed)
    cluster_ch = {cid: ch_node_ids[cid] for cid in range(rule.ch_count)}

    ch_rows = []
    node_lookup = {n["node_id"]: n for n in nodes}
    for cid in sorted(cluster_ch.keys()):
        ch_node_id = cluster_ch[cid]
        n = node_lookup[ch_node_id]
        ch_rows.append(
            {
                "entity_type": "CH",
                "entity_id": cid,
                "node_id": ch_node_id,
                "x_m": n["x_m"],
                "y_m": n["y_m"],
            }
        )

    bs_rows = []
    for bs_id, (x, y) in enumerate(_bs_positions(rule)):
        bs_rows.append(
            {
                "entity_type": "BS",
                "entity_id": bs_id,
                "node_id": None,
                "x_m": x,
                "y_m": y,
            }
        )

    ch_bs_rows = ch_rows + bs_rows
    mapping_rows = _node_cluster_map(nodes, cluster_ch)
    signature = _deterministic_signature(nodes, ch_bs_rows, mapping_rows)

    manifest = {
        "map_schema_version": MAP_SCHEMA_VERSION,
        "map_id": map_id,
        "scale_id": scale_id,
        "seed": seed,
        "generator": "tools/generate_map.py",
        "deterministic_signature_sha256": signature,
        "area": {"width_m": rule.width_m, "height_m": rule.height_m},
        "counts": {
            "node_count": rule.node_count,
            "ch_count": rule.ch_count,
            "bs_count": rule.bs_count,
        },
        "rules": {
            "boundary_margin_m": BOUNDARY_MARGIN_M,
            "min_spacing_m": rule.min_spacing_m,
            "ch_selection": "deterministic_farthest_point_sampling",
            "node_cluster_assignment": "nearest_ch_tie_lowest_cluster_id",
            "bs_placement": "deterministic_geometry_anchors",
        },
        "files": {
            "nodes": "nodes.csv",
            "ch_bs": "ch_bs.csv",
            "node_cluster_map": "node_cluster_map.csv",
        },
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }

    return {
        "manifest": manifest,
        "nodes": nodes,
        "ch_bs": ch_bs_rows,
        "node_cluster_map": mapping_rows,
    }


def write_map_package(map_data: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "manifest.json"
    nodes_path = output_dir / "nodes.csv"
    ch_bs_path = output_dir / "ch_bs.csv"
    mapping_path = output_dir / "node_cluster_map.csv"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(map_data["manifest"], f, indent=2, sort_keys=True)
        f.write("\n")

    with nodes_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["node_id", "x_m", "y_m"])
        for row in sorted(map_data["nodes"], key=lambda r: r["node_id"]):
            writer.writerow([row["node_id"], _fmt_float(row["x_m"]), _fmt_float(row["y_m"])])

    with ch_bs_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["entity_type", "entity_id", "node_id", "x_m", "y_m"])

        def _sort_key(r):
            kind_rank = 0 if r["entity_type"] == "CH" else 1
            return (kind_rank, r["entity_id"])

        for row in sorted(map_data["ch_bs"], key=_sort_key):
            node_id = "" if row["node_id"] is None else row["node_id"]
            writer.writerow([row["entity_type"], row["entity_id"], node_id, _fmt_float(row["x_m"]), _fmt_float(row["y_m"])])

    with mapping_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["node_id", "cluster_id", "is_ch"])
        for row in sorted(map_data["node_cluster_map"], key=lambda r: r["node_id"]):
            writer.writerow([row["node_id"], row["cluster_id"], row["is_ch"]])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic topology map package")
    parser.add_argument("--scale-id", required=True, choices=sorted(SCALE_RULES.keys()))
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-root", default="maps/generated")
    parser.add_argument("--map-id", default=None)
    args = parser.parse_args()

    map_data = generate_map_data(args.scale_id, args.seed, args.map_id)
    out_root = Path(args.output_root)
    out_dir = out_root / map_data["manifest"]["map_id"]
    write_map_package(map_data, out_dir)

    print(f"Generated map package: {out_dir}")
    print(f"  scale_id: {args.scale_id}")
    print(f"  seed: {args.seed}")
    print(f"  signature: {map_data['manifest']['deterministic_signature_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
