#!/usr/bin/env python3
"""Validate Stage C completion: check 64/64 rows, balance, map lineage, DB integrity."""

import json
import sys
from pathlib import Path
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "outputs" / "s8_stagec_state.json"
DB_ENV_FILE = Path("/home/cyfer/FYP/WSN Dashboard Milestone V2/web-monitor/backend/config/.env")


def load_env(cfg_file: Path) -> dict:
    env = {}
    for line in cfg_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> int:
    if not STATE_FILE.exists():
        print(f"❌ State file not found: {STATE_FILE}")
        return 1

    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    ok_rows = [k for k, v in state.items() if v.get("status") == "ok"]
    failed_rows = [k for k, v in state.items() if v.get("status") == "failed"]

    print(f"\n=== Stage C Validation ===\n")
    print(f"State file: {STATE_FILE}")
    print(f"Complete (ok): {len(ok_rows)}/64 rows")
    print(f"Failed: {len(failed_rows)}/64 rows")

    if len(ok_rows) < 64:
        print(f"\n❌ INCOMPLETE: Only {len(ok_rows)}/64 rows complete")
        if failed_rows:
            print(f"Failed rows: {failed_rows[:5]}")
        return 1

    if len(failed_rows) > 0:
        print(f"\n❌ FAILED ROWS DETECTED: {len(failed_rows)} failures")
        print(f"First 5 failures: {failed_rows[:5]}")
        return 1

    # Validate balance
    families = {}
    healings = {}
    architectures = {"A": 0, "B": 0}
    loads = {"L1": 0, "L2": 0}
    seeds = {1: 0, 2: 0}

    for row in ok_rows:
        data = state[row]
        family = data.get("failure_family", "?")
        healing = data.get("healing_id", "?")
        arch = data.get("architecture", "?")
        load = data.get("load", "?")
        seed = data.get("seed", 0)

        families[family] = families.get(family, 0) + 1
        healings[healing] = healings.get(healing, 0) + 1
        architectures[arch] = architectures.get(arch, 0) + 1
        loads[load] = loads.get(load, 0) + 1
        seeds[seed] = seeds.get(seed, 0) + 1

    print(f"\nBalance Check:")
    print(f"  Families: {families}")
    print(f"  Healing IDs: {healings}")
    print(f"  Architectures: {architectures}")
    print(f"  Loads: {loads}")
    print(f"  Seeds: {seeds}")

    # Validate expected counts
    # Stage C Paired Comparison Matrix:
    # 8 (family, healing) pairs × 2 arch × 2 load × 2 seed = 64 rows
    # Pairs: (F1,H0), (F1,H1), (F2,H0), (F2,H2), (F3,H0), (F3,H3), (F4,H0), (F4,H4)
    errors = []
    if families.get("F1", 0) != 16:  # 2 scenarios (F1/H0, F1/H1) × 8 permutations each
        errors.append(f"F1: expected 16, got {families.get('F1', 0)}")
    if families.get("F2", 0) != 16:
        errors.append(f"F2: expected 16, got {families.get('F2', 0)}")
    if families.get("F3", 0) != 16:
        errors.append(f"F3: expected 16, got {families.get('F3', 0)}")
    if families.get("F4", 0) != 16:
        errors.append(f"F4: expected 16, got {families.get('F4', 0)}")
    # Healing counts: H0 (paired with 4 families), H1–H4 (each paired with 1 family)
    if healings.get("H0", 0) != 32:  # 4 families × H0 × 8 permutations / 1 = 32
        errors.append(f"H0: expected 32, got {healings.get('H0', 0)}")
    if healings.get("H1", 0) != 8:  # F1/H1 only × 8 permutations
        errors.append(f"H1: expected 8, got {healings.get('H1', 0)}")
    if healings.get("H2", 0) != 8:  # F2/H2 only × 8 permutations
        errors.append(f"H2: expected 8, got {healings.get('H2', 0)}")
    if healings.get("H3", 0) != 8:  # F3/H3 only × 8 permutations
        errors.append(f"H3: expected 8, got {healings.get('H3', 0)}")
    if healings.get("H4", 0) != 8:  # F4/H4 only × 8 permutations
        errors.append(f"H4: expected 8, got {healings.get('H4', 0)}")
    if architectures.get("A", 0) != 32:
        errors.append(f"Architecture A: expected 32, got {architectures.get('A', 0)}")
    if architectures.get("B", 0) != 32:
        errors.append(f"Architecture B: expected 32, got {architectures.get('B', 0)}")
    if loads.get("L1", 0) != 32:
        errors.append(f"Load L1: expected 32, got {loads.get('L1', 0)}")
    if loads.get("L2", 0) != 32:
        errors.append(f"Load L2: expected 32, got {loads.get('L2', 0)}")
    if seeds.get(1, 0) != 32:
        errors.append(f"Seed01: expected 32, got {seeds.get(1, 0)}")
    if seeds.get(2, 0) != 32:
        errors.append(f"Seed02: expected 32, got {seeds.get(2, 0)}")

    if errors:
        print(f"\n❌ Balance Check FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"\n✅ Balance Check PASSED\n")

    # DB validation
    try:
        env = load_env(DB_ENV_FILE)
        conn = psycopg2.connect(
            host=env["PGHOST"],
            port=int(env["PGPORT"]),
            database=env["PGDATABASE"],
            user=env["PGUSER"],
            password=env["PGPASSWORD"],
            sslmode=env.get("PGSSLMODE", "disable"),
        )
        conn.autocommit = True

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET search_path TO wsn, public")

            # Check total S8 count
            cur.execute("SELECT COUNT(*) AS c FROM wsn.runs WHERE scale = 'S8'")
            s8_total = int(cur.fetchone()["c"])
            print(f"DB S8 Total Rows: {s8_total}")
            if s8_total < 64:
                print(f"❌ DB S8 count {s8_total} < 64 (Stage C not fully imported?)")
                return 1

            # Check completion status
            cur.execute(
                "SELECT COUNT(*) AS c FROM wsn.runs WHERE scale = 'S8' AND run_status = 'complete'"
            )
            s8_complete = int(cur.fetchone()["c"])
            print(f"DB S8 Complete Rows: {s8_complete}")
            if s8_complete != s8_total:
                print(f"❌ Not all S8 rows complete: {s8_complete}/{s8_total}")
                return 1

            # Check Stage C rows are all present
            cur.execute(
                """
                SELECT architecture, failure_family, healing_id, load, seed, COUNT(*) AS cnt
                FROM wsn.runs
                WHERE scale = 'S8' AND run_status = 'complete'
                  AND healing_id IN ('H0', 'H1', 'H2', 'H3', 'H4')
                  AND failure_family IN ('F1', 'F2', 'F3', 'F4')
                GROUP BY architecture, failure_family, healing_id, load, seed
                ORDER BY failure_family, healing_id, architecture, load, seed
                """
            )
            db_rows = cur.fetchall()
            print(f"\nDB Stage C Rows: {len(db_rows)} groups")
            if len(db_rows) < 64:
                print(f"❌ DB has {len(db_rows)} row groups, expected 64+")
                return 1

            # Check map integrity
            cur.execute(
                """
                SELECT DISTINCT scale, map_id, map_signature
                FROM wsn.runs
                WHERE scale = 'S8'
                ORDER BY scale, map_id
                """
            )
            map_rows = cur.fetchall()
            print(f"\nDB Map Integrity (S8):")
            for row in map_rows:
                print(f"  {row['scale']} map_id={row['map_id']} sig={row['map_signature'][:8]}...")

            # Verify DB completeness
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM wsn.runs
                WHERE scale = 'S8' AND run_status = 'complete'
                """
            )
            api_vis = int(cur.fetchone()["c"])
            print(f"\nComplete S8 Rows (DB): {api_vis}")

        conn.close()
        print(f"\n✅ DB Validation PASSED\n")

    except Exception as exc:
        print(f"\n❌ DB Validation FAILED: {exc}")
        return 1

    print(f"\n{'='*50}")
    print(f"✅ STAGE C VALIDATION COMPLETE")
    print(f"   64/64 rows present and balanced")
    print(f"   DB integrity confirmed")
    print(f"   Completion time: {datetime.now().isoformat()}")
    print(f"{'='*50}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
