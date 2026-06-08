import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "wsn_base_station.db"

HEARTBEAT_TIMEOUT_S = 15

console = Console()


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_rows():
    if not DB_PATH.exists():
        return []

    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM node_status ORDER BY node_id").fetchall()
    conn.close()
    return rows


def make_screen():
    rows = get_rows()
    now = datetime.now(timezone.utc)

    table = Table(title="WSN Raspberry Pi Base Station - Live Node Monitor")

    table.add_column("Node ID", justify="left")
    table.add_column("Status", justify="center")
    table.add_column("Age (s)", justify="right")
    table.add_column("Seq", justify="right")
    table.add_column("RSSI", justify="right")
    table.add_column("Battery", justify="right")
    table.add_column("Missed", justify="right")
    table.add_column("Mode", justify="left")
    table.add_column("IP", justify="left")

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
            status_text = "[green]ONLINE[/green]"
        else:
            offline += 1
            status_text = "[red]OFFLINE[/red]"

        battery_text = ""
        if row["battery_v"] is not None:
            battery_text = f"{row['battery_v']:.2f}V"

        table.add_row(
            str(row["node_id"]),
            status_text,
            f"{age_s:.1f}",
            str(row["last_seq"]),
            str(row["rssi_dbm"]),
            battery_text,
            str(row["missed_packets"]),
            str(row["mode"]),
            str(row["wifi_ip"])
        )

    summary = (
        f"Database: {DB_PATH}\n"
        f"Heartbeat timeout: {HEARTBEAT_TIMEOUT_S}s\n"
        f"Online: {online} | Offline: {offline}"
    )

    return Panel.fit(table, title=summary)


def main():
    with Live(make_screen(), refresh_per_second=1, console=console) as live:
        while True:
            live.update(make_screen())
            time.sleep(1)


if __name__ == "__main__":
    main()
