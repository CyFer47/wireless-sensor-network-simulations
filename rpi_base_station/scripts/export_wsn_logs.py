import sqlite3
import csv
import argparse
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "wsn_base_station.db"
EXPORT_ROOT = BASE_DIR / "exports"

HEARTBEAT_TIMEOUT_S = 15


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def export_query(conn, query, out_path, params=None):
    params = params or []

    cur = conn.cursor()
    rows = cur.execute(query, params).fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if rows:
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow([row[k] for k in row.keys()])
        else:
            # Try to write column names even when table is empty
            desc = cur.description
            if desc:
                writer.writerow([d[0] for d in desc])

    return len(rows)


def export_status_snapshot(conn, out_path):
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM node_status ORDER BY node_id").fetchall()

    now = datetime.now(timezone.utc)

    fieldnames = [
        "export_time",
        "node_id",
        "stored_status",
        "computed_status",
        "age_s",
        "last_seen",
        "last_seq",
        "mode",
        "rssi_dbm",
        "battery_v",
        "wifi_ip",
        "missed_packets"
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            last_seen = datetime.fromisoformat(row["last_seen"])
            age_s = (now - last_seen).total_seconds()

            computed_status = row["status"]
            if age_s > HEARTBEAT_TIMEOUT_S:
                computed_status = "OFFLINE"

            writer.writerow({
                "export_time": now.isoformat(),
                "node_id": row["node_id"],
                "stored_status": row["status"],
                "computed_status": computed_status,
                "age_s": round(age_s, 3),
                "last_seen": row["last_seen"],
                "last_seq": row["last_seq"],
                "mode": row["mode"],
                "rssi_dbm": row["rssi_dbm"],
                "battery_v": row["battery_v"],
                "wifi_ip": row["wifi_ip"],
                "missed_packets": row["missed_packets"]
            })

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Export WSN Raspberry Pi base station SQLite logs to CSV.")
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output folder. If omitted, a timestamped folder is created under exports/."
    )

    args = parser.parse_args()

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    if args.out:
        out_dir = Path(args.out)
        if not out_dir.is_absolute():
            out_dir = BASE_DIR / out_dir
    else:
        out_dir = EXPORT_ROOT / f"wsn_export_{now_stamp()}"

    out_dir.mkdir(parents=True, exist_ok=True)

    conn = connect_db()

    counts = {}

    counts["telemetry"] = export_query(
        conn,
        "SELECT * FROM telemetry ORDER BY id",
        out_dir / "telemetry.csv"
    )

    counts["events"] = export_query(
        conn,
        "SELECT * FROM events ORDER BY id",
        out_dir / "events.csv"
    )

    counts["node_status"] = export_query(
        conn,
        "SELECT * FROM node_status ORDER BY node_id",
        out_dir / "node_status.csv"
    )

    counts["commands"] = export_query(
        conn,
        "SELECT * FROM commands ORDER BY node_id",
        out_dir / "commands.csv"
    )

    counts["status_snapshot"] = export_status_snapshot(
        conn,
        out_dir / "status_snapshot.csv"
    )

    conn.close()

    summary_path = out_dir / "export_summary.txt"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("WSN Raspberry Pi Base Station CSV Export Summary\n")
        f.write("================================================\n\n")
        f.write(f"Export time: {datetime.now().isoformat()}\n")
        f.write(f"Database: {DB_PATH}\n")
        f.write(f"Output folder: {out_dir}\n")
        f.write(f"Heartbeat timeout: {HEARTBEAT_TIMEOUT_S}s\n\n")

        for name, count in counts.items():
            f.write(f"{name}: {count} rows\n")

    print("CSV export complete.")
    print(f"Output folder: {out_dir}")
    print()
    for name, count in counts.items():
        print(f"{name}: {count} rows")
    print()
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
