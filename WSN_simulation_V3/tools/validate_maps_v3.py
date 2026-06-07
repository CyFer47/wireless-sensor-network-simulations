#!/usr/bin/env python3
import csv, json, sys
from pathlib import Path

errors = 0

for manifest_path in Path(sys.argv[1]).rglob("manifest.json"):
    map_dir = manifest_path.parent
    m = json.loads(manifest_path.read_text())

    required = ["nodes.csv", "ch_bs.csv", "node_cluster_map.csv"]
    for f in required:
        if not (map_dir / f).exists():
            errors += 1
            print("missing", f, map_dir)

    nodes = list(csv.DictReader((map_dir / "nodes.csv").open()))
    chbs = list(csv.DictReader((map_dir / "ch_bs.csv").open()))
    mapping = list(csv.DictReader((map_dir / "node_cluster_map.csv").open()))

    if len(nodes) != m["counts"]["node_count"]:
        errors += 1
        print("bad node count", map_dir, len(nodes), m["counts"]["node_count"])

    ch_count = sum(1 for r in chbs if r["entity_type"] == "CH")
    bs_count = sum(1 for r in chbs if r["entity_type"] == "BS")

    if ch_count != m["counts"]["ch_count"]:
        errors += 1
        print("bad CH count", map_dir, ch_count, m["counts"]["ch_count"])

    if bs_count != m["counts"]["bs_count"]:
        errors += 1
        print("bad BS count", map_dir, bs_count, m["counts"]["bs_count"])

    if len(mapping) != len(nodes):
        errors += 1
        print("bad mapping count", map_dir, len(mapping), len(nodes))

    ch_flags = sum(1 for r in mapping if r["is_ch"] == "1")
    if ch_flags != ch_count:
        errors += 1
        print("bad is_ch count", map_dir, ch_flags, ch_count)

    node_ids = {r["node_id"] for r in nodes}
    map_node_ids = {r["node_id"] for r in mapping}
    if node_ids != map_node_ids:
        errors += 1
        print("node id mismatch", map_dir)

print(f"Checked maps. Errors = {errors}")
sys.exit(1 if errors else 0)
