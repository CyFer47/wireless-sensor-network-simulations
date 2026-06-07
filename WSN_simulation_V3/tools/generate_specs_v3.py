#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path

SCENARIOS = [
    ("F0", "H0", "V1"),
    ("F1", "H0", "V2"), ("F2", "H0", "V2"), ("F3", "H0", "V2"), ("F4", "H0", "V2"),
    ("F1", "H1", "V3"), ("F1", "H3", "V3"), ("F1", "H4", "V3"),
    ("F2", "H1", "V3"), ("F2", "H3", "V3"), ("F2", "H4", "V3"),
    ("F3", "H1", "V3"), ("F3", "H3", "V3"), ("F3", "H4", "V3"),
    ("F4", "H1", "V3"), ("F4", "H3", "V3"), ("F4", "H4", "V3")
]

def load_json(path):
    return json.loads(Path(path).read_text())

def spec(scale_id, scale_rule, profile, arch, load, failure, healing, variant, seed):
    run_id = f"campaign_v3_{scale_id}_{profile}_{arch}_{load}_{failure}_{healing}_seed{seed:03d}"
    is_baseline = variant == "V1"

    return {
        "schema_version": "runspec_v3",
        "run_spec_id": run_id,
        "description": f"Campaign V3 {scale_id} {profile} {arch} {load} {failure}/{healing} seed{seed:03d}",
        "campaign": "campaign_v3",
        "architecture": arch,
        "runnable": True,
        "variant": variant,
        "failure_family": failure,
        "healing_id": healing,
        "load": load,
        "scale": scale_id,
        "seed": seed,
        "map_profile": profile,
        "topology": {
            "node_count": scale_rule["nodes"],
            "cluster_count": scale_rule["clusters"],
            "bs": scale_rule["bs"],
            "area": [scale_rule["area_x"], scale_rule["area_y"]]
        },
        "timing": {
            "sim_time_s": 300.0,
            "traffic_interval_s": 1.0,
            "aggregation_interval_s": 30.0,
            "dashboard_interval_s": 10.0,
            "failure_time_s": None if is_baseline else 60.0,
            "recovery_delay_s": 0.0 if healing == "H0" else 12.0
        },
        "failure_injection": {
            "enabled": not is_baseline
        },
        "recovery": {
            "enabled": healing != "H0",
            "profile": "v3_energy_aware" if healing != "H0" else "none"
        },
        "execution": {
            "sim_source": "ns3",
            "enable_run_export": True
        }
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scale-id", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--seed-end", type=int, default=3)
    p.add_argument("--scales", default="campaign/config/scales.json")
    p.add_argument("--output-root", required=True)
    args = p.parse_args()

    scales = load_json(args.scales)
    rule = scales[args.scale_id]

    out_root = Path(args.output_root) / args.profile
    out_root.mkdir(parents=True, exist_ok=True)

    count = 0
    for seed in range(args.seed_start, args.seed_end + 1):
        for arch in ["A", "B"]:
            for load in ["L1", "L2"]:
                for failure, healing, variant in SCENARIOS:
                    s = spec(args.scale_id, rule, args.profile, arch, load, failure, healing, variant, seed)
                    path = out_root / f"{s['run_spec_id']}.json"
                    path.write_text(json.dumps(s, indent=2) + "\n")
                    count += 1

    print(f"Generated {count} specs in {out_root}")

if __name__ == "__main__":
    main()
