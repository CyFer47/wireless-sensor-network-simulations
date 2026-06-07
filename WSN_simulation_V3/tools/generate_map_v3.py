#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, math, random
from pathlib import Path
from statistics import mean, pstdev

MARGIN = 2.0

def load_scales(path: Path) -> dict:
    return json.loads(path.read_text())

def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])

def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)

def gen_nodes(rule, seed, profile):
    rng = random.Random(seed)
    nodes = []
    n = rule["nodes"]
    w, h = rule["area_x"], rule["area_y"]

    for node_id in range(n):
        if profile == "M2_LONG_LINK" and node_id < n * 0.40:
            x = rng.uniform(w * 0.78, w - MARGIN)
            y = rng.uniform(h * 0.78, h - MARGIN)
        elif profile == "M3_IMBALANCED" and node_id < n * 0.75:
            x = rng.uniform(w * 0.05, w * 0.22)
            y = rng.uniform(h * 0.05, h * 0.22)
        else:
            x = rng.uniform(MARGIN, w - MARGIN)
            y = rng.uniform(MARGIN, h - MARGIN)

        nodes.append({"node_id": node_id, "x": round(x, 3), "y": round(y, 3)})

    return nodes

def choose_ch(nodes, ch_count, seed, profile):
    rng = random.Random(seed * 10007 + 97)

    if profile == "M3_IMBALANCED":
        # Intentionally place CHs away from the dense node group.
        # This creates uneven cluster membership and longer member-to-CH distances.
        max_x = max(n["x"] for n in nodes)
        max_y = max(n["y"] for n in nodes)
        dense_x = max_x * 0.45
        dense_y = max_y * 0.45

        candidate_indices = [
            idx for idx, n in enumerate(nodes)
            if not (n["x"] <= dense_x and n["y"] <= dense_y)
        ]
        if len(candidate_indices) < ch_count:
            candidate_indices = list(range(len(nodes)))

        first = rng.choice(candidate_indices)
        chosen = [first]
        chosen_set = {first}

        while len(chosen) < ch_count:
            best_idx, best_score = None, -1
            for idx in candidate_indices:
                if idx in chosen_set:
                    continue
                score = min(dist(nodes[idx], nodes[c]) for c in chosen)
                if score > best_score:
                    best_idx, best_score = idx, score
            chosen.append(best_idx)
            chosen_set.add(best_idx)

        return sorted(nodes[i]["node_id"] for i in chosen)

    if profile == "M2_LONG_LINK":
        max_x = max(n["x"] for n in nodes)
        max_y = max(n["y"] for n in nodes)
        corner_x = max_x * 0.70
        corner_y = max_y * 0.70
        candidate_indices = [
            idx for idx, n in enumerate(nodes)
            if not (n["x"] >= corner_x and n["y"] >= corner_y)
        ]
        if len(candidate_indices) < ch_count:
            candidate_indices = list(range(len(nodes)))

        first = rng.choice(candidate_indices)
        chosen = [first]
        chosen_set = {first}

        while len(chosen) < ch_count:
            best_idx, best_score = None, -1
            for idx in candidate_indices:
                if idx in chosen_set:
                    continue
                score = min(dist(nodes[idx], nodes[c]) for c in chosen)
                if score > best_score:
                    best_idx, best_score = idx, score
            chosen.append(best_idx)
            chosen_set.add(best_idx)

        return sorted(nodes[i]["node_id"] for i in chosen)

    first = rng.randrange(len(nodes))
    chosen = [first]
    chosen_set = {first}

    while len(chosen) < ch_count:
        best_idx, best_score = None, -1
        for idx, node in enumerate(nodes):
            if idx in chosen_set:
                continue
            score = min(dist(node, nodes[c]) for c in chosen)
            if score > best_score:
                best_idx, best_score = idx, score
        chosen.append(best_idx)
        chosen_set.add(best_idx)

    return sorted(nodes[i]["node_id"] for i in chosen)

def bs_positions(rule, profile):
    w, h, bs = rule["area_x"], rule["area_y"], rule["bs"]

    if profile == "M2_LONG_LINK":
        base = [(w * 0.08, h * 0.08)]
    else:
        base = [(w * 0.5, h * 0.5)]

    if bs == 1:
        return base

    anchors = [
        (w*0.20, h*0.20), (w*0.80, h*0.20),
        (w*0.20, h*0.80), (w*0.80, h*0.80),
        (w*0.50, h*0.50), (w*0.50, h*0.80)
    ]
    return anchors[:bs]

def build_map(scale_id, rule, seed, profile):
    nodes = gen_nodes(rule, seed, profile)
    node_lookup = {n["node_id"]: n for n in nodes}

    ch_ids = choose_ch(nodes, rule["clusters"], seed, profile)
    cluster_ch = {cid: ch_ids[cid] for cid in range(len(ch_ids))}

    ch_bs = []
    for cid, node_id in cluster_ch.items():
        n = node_lookup[node_id]
        ch_bs.append({"entity_type": "CH", "entity_id": cid, "node_id": node_id, "x_m": n["x"], "y_m": n["y"]})

    for bs_id, (x, y) in enumerate(bs_positions(rule, profile)):
        ch_bs.append({"entity_type": "BS", "entity_id": bs_id, "node_id": "", "x_m": round(x, 3), "y_m": round(y, 3)})

    mapping = []
    cluster_sizes = {cid: 0 for cid in cluster_ch}
    node_to_ch_d = []

    for n in nodes:
        if n["node_id"] in cluster_ch.values():
            cid = next(k for k, v in cluster_ch.items() if v == n["node_id"])
            is_ch = 1
        else:
            cid = min(cluster_ch, key=lambda c: dist(n, node_lookup[cluster_ch[c]]))
            is_ch = 0

        cluster_sizes[cid] += 1
        node_to_ch_d.append(dist(n, node_lookup[cluster_ch[cid]]))
        mapping.append({"node_id": n["node_id"], "cluster_id": cid, "is_ch": is_ch})

    ch_nodes = [node_lookup[v] for v in cluster_ch.values()]
    bs_nodes = [{"x": r["x_m"], "y": r["y_m"]} for r in ch_bs if r["entity_type"] == "BS"]
    ch_to_bs_d = [min(dist(ch, bs) for bs in bs_nodes) for ch in ch_nodes]
    sizes = list(cluster_sizes.values())

    metrics = {
        "mean_node_to_ch_distance": round(mean(node_to_ch_d), 3),
        "max_node_to_ch_distance": round(max(node_to_ch_d), 3),
        "mean_ch_to_bs_distance": round(mean(ch_to_bs_d), 3),
        "max_ch_to_bs_distance": round(max(ch_to_bs_d), 3),
        "cluster_size_mean": round(mean(sizes), 3),
        "cluster_size_max": max(sizes),
        "cluster_size_cv": round((pstdev(sizes) / mean(sizes)) if mean(sizes) else 0, 4),
        "long_link_ratio": round(sum(1 for d in node_to_ch_d if d > mean(node_to_ch_d) * 1.5) / len(node_to_ch_d), 4)
    }

    sig_payload = {"nodes": nodes, "ch_bs": ch_bs, "mapping": mapping, "metrics": metrics}
    signature = hashlib.sha256(json.dumps(sig_payload, sort_keys=True).encode()).hexdigest()

    manifest = {
        "map_schema_version": "v3_map",
        "map_id": f"map_{scale_id}_{profile}_seed{seed:03d}",
        "scale_id": scale_id,
        "seed": seed,
        "map_profile": profile,
        "deterministic_signature_sha256": signature,
        "area": {"width_m": rule["area_x"], "height_m": rule["area_y"]},
        "counts": {"node_count": rule["nodes"], "ch_count": rule["clusters"], "bs_count": rule["bs"]},
        "metrics": metrics,
        "files": {"nodes": "nodes.csv", "ch_bs": "ch_bs.csv", "node_cluster_map": "node_cluster_map.csv"}
    }

    return manifest, nodes, ch_bs, mapping

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scale-id", required=True)
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--profile", required=True, choices=["M1_BALANCED", "M2_LONG_LINK", "M3_IMBALANCED"])
    p.add_argument("--scales", default="campaign/config/scales.json")
    p.add_argument("--output-root", required=True)
    args = p.parse_args()

    scales = load_scales(Path(args.scales))
    rule = scales[args.scale_id]

    manifest, nodes, ch_bs, mapping = build_map(args.scale_id, rule, args.seed, args.profile)

    out = Path(args.output_root) / args.profile / manifest["map_id"]
    out.mkdir(parents=True, exist_ok=True)

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_csv(out / "nodes.csv", ["node_id", "x_m", "y_m"], [{"node_id": n["node_id"], "x_m": n["x"], "y_m": n["y"]} for n in nodes])
    write_csv(out / "ch_bs.csv", ["entity_type", "entity_id", "node_id", "x_m", "y_m"], ch_bs)
    write_csv(out / "node_cluster_map.csv", ["node_id", "cluster_id", "is_ch"], mapping)

    print(f"Generated: {out}")
    print(f"Signature: {manifest['deterministic_signature_sha256']}")
    print(json.dumps(manifest["metrics"], indent=2))

if __name__ == "__main__":
    main()