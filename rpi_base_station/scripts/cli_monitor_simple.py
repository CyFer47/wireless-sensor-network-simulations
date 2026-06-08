import sqlite3
import time
import os
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "wsn_base_station.db"
HEARTBEAT_TIMEOUT_S = 15


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def draw():
    os.system("clear")

    print("WSN RASPBERRY PI BASE STATION - SIMPLE LIVE MONITOR")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print(f"Heartbeat timeout: {HEARTBEAT_TIMEOUT_S}s")
    print("=" * 70)

    if not DB_PATH.exists():
        print("Database not found yet.")
        return

    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM node_status ORDER BY node_id").fetchall()
    conn.close()

    now = datetime.now(timezone.utc)

    if not rows:
        print("No nodes received yet.")
        return

    print(f"{'NODE':<10} {'STATUS':<10} {'AGE(s)':<8} {'SEQ':<6} {'RSSI':<7} {'BAT':<7} {'MISSED':<7} {'MODE':<18}")
    print("-" * 90)

    online = 0
    offline = 0

    for row in rows:
        last_seen = datetime.fromisoformat(row["last_seen"])
        age_s = (now - last_seen).total_seconds()

        status = row["status"]
        if age_s > HEARTBEAT_TIMEOUT_S:
            status = "OFFLINE"

        if status == "ONLINE":
            online += 1
        else:
            offline += 1

        battery = ""
        if row["battery_v"] is not None:
            battery = f"{row['battery_v']:.2f}"

        print(
            f"{row['node_id']:<10} "
            f"{status:<10} "
            f"{age_s:<8.1f} "
            f"{str(row['last_seq']):<6} "
            f"{str(row['rssi_dbm']):<7} "
            f"{battery:<7} "
            f"{str(row['missed_packets']):<7} "
            f"{str(row['mode']):<18}"
        )

    print("-" * 90)
    print(f"Online: {online} | Offline: {offline}")
    print()
    print("Press Ctrl+C to stop monitor.")


while True:
    draw()
    time.sleep(1)
