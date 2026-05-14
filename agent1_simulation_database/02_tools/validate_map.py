#!/usr/bin/env python3
"""Validator for M2 deterministic map packages."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

from generate_map import SCALE_RULES, generate_map_data


def _read_csv_dict(path: Path) -> List[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fail(msg: str, errors: List[str]) -> None:
    errors.append(msg)


def _parse_int(v: str, field: str, errors: List[str]) -> int | None:
    try:
        return int(v)
    except Exception:
        _fail(f"Invalid integer for {field}: {v}", errors)
        return None


def _parse_float(v: str, field: str, errors: List[str]) -> float | None:
    try:
        return float(v)
    except Exception:
        _fail(f"Invalid float for {field}: {v}", errors)
        return None


def validate_package(pkg_dir: Path) -> int:
    errors: List[str] = []

    manifest_path = pkg_dir / "manifest.json"
    nodes_path = pkg_dir / "nodes.csv"
    chbs_path = pkg_dir / "ch_bs.csv"
    map_path = pkg_dir / "node_cluster_map.csv"

    for p in [manifest_path, nodes_path, chbs_path, map_path]:
        if not p.exists():
            _fail(f"Missing required file: {p.name}", errors)

    if errors:
        print(f"FAIL: {pkg_dir}")
        for e in errors:
            print(f"  - {e}")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scale_id = manifest.get("scale_id")
    seed = manifest.get("seed")

    if scale_id not in SCALE_RULES:
        _fail(f"Invalid scale_id in manifest: {scale_id}", errors)
    if not isinstance(seed, int):
        _fail("Manifest seed must be integer", errors)

    if errors:
        print(f"FAIL: {pkg_dir}")
        for e in errors:
            print(f"  - {e}")
        return 1

    rule = SCALE_RULES[scale_id]

    nodes_raw = _read_csv_dict(nodes_path)
    chbs_raw = _read_csv_dict(chbs_path)
    mapping_raw = _read_csv_dict(map_path)

    # Validate nodes
    node_ids = set()
    node_xy: Dict[int, Tuple[float, float]] = {}
    for r in nodes_raw:
        node_id = _parse_int(r.get("node_id", ""), "nodes.node_id", errors)
        x = _parse_float(r.get("x_m", ""), "nodes.x_m", errors)
        y = _parse_float(r.get("y_m", ""), "nodes.y_m", errors)
        if node_id is None or x is None or y is None:
            continue

        if node_id in node_ids:
            _fail(f"Duplicate node_id: {node_id}", errors)
        node_ids.add(node_id)
        node_xy[node_id] = (x, y)

        if x < 0.0 or x > rule.width_m or y < 0.0 or y > rule.height_m:
            _fail(f"Node {node_id} outside bounds: ({x},{y})", errors)

    if len(node_ids) != rule.node_count:
        _fail(f"Node count mismatch: expected {rule.node_count}, got {len(node_ids)}", errors)

    expected_node_ids = set(range(rule.node_count))
    if node_ids != expected_node_ids:
        _fail("Node IDs must be contiguous 0..N-1 with no missing IDs", errors)

    # Validate CH/BS rows
    ch_ids = set()
    bs_ids = set()
    ch_node_ids = set()

    for r in chbs_raw:
        entity_type = r.get("entity_type", "")
        entity_id = _parse_int(r.get("entity_id", ""), "ch_bs.entity_id", errors)
        x = _parse_float(r.get("x_m", ""), "ch_bs.x_m", errors)
        y = _parse_float(r.get("y_m", ""), "ch_bs.y_m", errors)
        node_id_raw = r.get("node_id", "")

        if entity_id is None or x is None or y is None:
            continue

        if x < 0.0 or x > rule.width_m or y < 0.0 or y > rule.height_m:
            _fail(f"{entity_type} {entity_id} outside bounds: ({x},{y})", errors)

        if entity_type == "CH":
            if entity_id in ch_ids:
                _fail(f"Duplicate CH entity_id: {entity_id}", errors)
            ch_ids.add(entity_id)

            node_id = _parse_int(node_id_raw, "ch_bs.node_id(CH)", errors)
            if node_id is not None:
                if node_id not in node_ids:
                    _fail(f"CH node_id not found in nodes.csv: {node_id}", errors)
                if node_id in ch_node_ids:
                    _fail(f"Duplicate CH node_id assignment: {node_id}", errors)
                ch_node_ids.add(node_id)

        elif entity_type == "BS":
            if entity_id in bs_ids:
                _fail(f"Duplicate BS entity_id: {entity_id}", errors)
            bs_ids.add(entity_id)
            if node_id_raw not in {"", "None", "null", "NULL"}:
                _fail("BS row must have empty node_id", errors)

        else:
            _fail(f"Invalid entity_type: {entity_type}", errors)

    if len(ch_ids) != rule.ch_count:
        _fail(f"CH count mismatch: expected {rule.ch_count}, got {len(ch_ids)}", errors)
    if ch_ids != set(range(rule.ch_count)):
        _fail("CH IDs must be contiguous 0..CH-1", errors)

    if len(bs_ids) != rule.bs_count:
        _fail(f"BS count mismatch: expected {rule.bs_count}, got {len(bs_ids)}", errors)
    if bs_ids != set(range(rule.bs_count)):
        _fail("BS IDs must be contiguous 0..BS-1", errors)

    # Validate mapping
    map_node_ids = set()
    for r in mapping_raw:
        node_id = _parse_int(r.get("node_id", ""), "map.node_id", errors)
        cluster_id = _parse_int(r.get("cluster_id", ""), "map.cluster_id", errors)
        is_ch = _parse_int(r.get("is_ch", ""), "map.is_ch", errors)
        if node_id is None or cluster_id is None or is_ch is None:
            continue

        if node_id in map_node_ids:
            _fail(f"Duplicate mapping node_id: {node_id}", errors)
        map_node_ids.add(node_id)

        if node_id not in node_ids:
            _fail(f"Mapping node_id not found in nodes.csv: {node_id}", errors)
        if cluster_id not in ch_ids:
            _fail(f"Mapping cluster_id invalid: {cluster_id}", errors)
        if is_ch not in {0, 1}:
            _fail(f"is_ch must be 0 or 1 for node {node_id}", errors)

        if is_ch == 1:
            # CH row should map to cluster with same CH node.
            for c in chbs_raw:
                if c.get("entity_type") == "CH" and int(c.get("entity_id")) == cluster_id:
                    ch_node_id = int(c.get("node_id"))
                    if ch_node_id != node_id:
                        _fail(
                            f"CH node {node_id} incorrectly mapped to cluster {cluster_id}; expected {ch_node_id}",
                            errors,
                        )
                    break

    if map_node_ids != node_ids:
        _fail("Mapping must contain exactly one row for every node", errors)

    # Deterministic reproducibility check.
    expected = generate_map_data(scale_id, seed, manifest.get("map_id"))
    expected_sig = expected["manifest"]["deterministic_signature_sha256"]
    actual_sig = manifest.get("deterministic_signature_sha256")
    if actual_sig != expected_sig:
        _fail(
            "Deterministic signature mismatch; package content does not match generated deterministic output",
            errors,
        )

    if errors:
        print(f"FAIL: {pkg_dir}")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"PASS: {pkg_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic map package(s)")
    parser.add_argument("package", nargs="+", help="Path(s) to map package directories")
    args = parser.parse_args()

    code = 0
    for p in args.package:
        rc = validate_package(Path(p))
        if rc != 0:
            code = rc
    return code


if __name__ == "__main__":
    raise SystemExit(main())
