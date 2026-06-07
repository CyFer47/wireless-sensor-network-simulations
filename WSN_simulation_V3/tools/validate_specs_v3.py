#!/usr/bin/env python3
import json, sys
from pathlib import Path

valid_arch = {"A", "B"}
valid_load = {"L1", "L2"}
valid_variant = {"V1", "V2", "V3"}
valid_failure = {"F0", "F1", "F2", "F3", "F4"}
valid_healing = {"H0", "H1", "H2", "H3", "H4"}

errors = 0

for path in Path(sys.argv[1]).rglob("*.json"):
    s = json.loads(path.read_text())

    if s["architecture"] not in valid_arch: errors += 1; print("bad arch", path)
    if s["load"] not in valid_load: errors += 1; print("bad load", path)
    if s["variant"] not in valid_variant: errors += 1; print("bad variant", path)
    if s["failure_family"] not in valid_failure: errors += 1; print("bad failure", path)
    if s["healing_id"] not in valid_healing: errors += 1; print("bad healing", path)

    if s["variant"] == "V1" and not (s["failure_family"] == "F0" and s["healing_id"] == "H0"):
        errors += 1; print("bad V1", path)

    if s["variant"] == "V2" and not (s["failure_family"] != "F0" and s["healing_id"] == "H0"):
        errors += 1; print("bad V2", path)

    if s["variant"] == "V3" and not (s["failure_family"] != "F0" and s["healing_id"] != "H0"):
        errors += 1; print("bad V3", path)

print(f"Checked specs. Errors = {errors}")
sys.exit(1 if errors else 0)
