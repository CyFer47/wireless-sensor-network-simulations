import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone
import psutil

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "wsn_base_station.db"

HEARTBEAT_TIMEOUT_S = 15
REFRESH_S = 1

console = Console()


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_node_rows():
    if not DB_PATH.exists():
        return []

    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM node_status ORDER BY node_id"
    ).fetchall()
    conn.close()
    return rows


def fetch_latest_events(limit=8):
    if not DB_PATH.exists():
        return []

    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT event_time, event_type, node_id
        FROM events
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()
    return rows


def fetch_latest_telemetry(limit=6):
    if not DB_PATH.exists():
        return []

    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT server_time, node_id, seq, temp_c, humidity, rssi_dbm, battery_v
        FROM telemetry
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()
    return rows


def make_header():
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = Text()
    title.append(" WSN RPi Base Station Monitor ", style="bold white on blue")
    title.append(f"  {now_local}  ", style="bold cyan")
    title.append(" Press Ctrl+C to exit ", style="bold yellow")
    return Panel(title, style="blue")


def make_system_panel():
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(BASE_DIR))

    text = Text()
    text.append("CPU     ", style="bold")
    text.append(f"{cpu:5.1f}%\n", style="green" if cpu < 70 else "red")

    text.append("RAM     ", style="bold")
    text.append(f"{mem.percent:5.1f}%  ", style="green" if mem.percent < 75 else "red")
    text.append(f"Used {mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB\n")

    text.append("DISK    ", style="bold")
    text.append(f"{disk.percent:5.1f}%  ", style="green" if disk.percent < 80 else "red")
    text.append(f"Free {disk.free / (1024**3):.2f} GB\n")

    text.append("DB      ", style="bold")
    text.append(str(DB_PATH), style="cyan")

    return Panel(text, title="System", border_style="cyan")


def make_summary_panel(node_rows):
    now = datetime.now(timezone.utc)

    online = 0
    offline = 0
    weak_rssi = 0
    low_battery = 0

    for row in node_rows:
        last_seen = datetime.fromisoformat(row["last_seen"])
        age_s = (now - last_seen).total_seconds()

        status = row["status"]
        if age_s > HEARTBEAT_TIMEOUT_S:
            status = "OFFLINE"

        if status == "ONLINE":
            online += 1
        else:
            offline += 1

        if row["rssi_dbm"] is not None and row["rssi_dbm"] <= -75:
            weak_rssi += 1

        if row["battery_v"] is not None and row["battery_v"] < 3.5:
            low_battery += 1

    total = online + offline

    text = Text()
    text.append("Nodes total     ", style="bold")
    text.append(f"{total}\n", style="white")

    text.append("Online          ", style="bold")
    text.append(f"{online}\n", style="green")

    text.append("Offline         ", style="bold")
    text.append(f"{offline}\n", style="red" if offline > 0 else "green")

    text.append("Weak RSSI       ", style="bold")
    text.append(f"{weak_rssi}\n", style="yellow" if weak_rssi > 0 else "green")

    text.append("Low battery     ", style="bold")
    text.append(f"{low_battery}\n", style="yellow" if low_battery > 0 else "green")

    text.append("Timeout         ", style="bold")
    text.append(f"{HEARTBEAT_TIMEOUT_S}s", style="cyan")

    return Panel(text, title="Network Summary", border_style="green")


def make_node_table(node_rows):
    now = datetime.now(timezone.utc)

    table = Table(
        title="Live Node Status",
        expand=True,
        show_lines=False,
        header_style="bold magenta"
    )

    table.add_column("Node", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Age", justify="right", no_wrap=True)
    table.add_column("Seq", justify="right", no_wrap=True)
    table.add_column("RSSI", justify="right", no_wrap=True)
    table.add_column("Bat", justify="right", no_wrap=True)
    table.add_column("Miss", justify="right", no_wrap=True)
    table.add_column("Mode", no_wrap=True)
    table.add_column("IP", no_wrap=True)

    if not node_rows:
        table.add_row("-", "NO DATA", "-", "-", "-", "-", "-", "-", "-")
        return Panel(table, border_style="magenta")

    for row in node_rows:
        last_seen = datetime.fromisoformat(row["last_seen"])
        age_s = (now - last_seen).total_seconds()

        status = row["status"]
        if age_s > HEARTBEAT_TIMEOUT_S:
            status = "OFFLINE"

        if status == "ONLINE":
            status_text = "[bold green]ONLINE[/bold green]"
        else:
            status_text = "[bold red]OFFLINE[/bold red]"

        rssi = row["rssi_dbm"]
        if rssi is None:
            rssi_text = "-"
        elif rssi <= -75:
            rssi_text = f"[yellow]{rssi}[/yellow]"
        else:
            rssi_text = f"[green]{rssi}[/green]"

        battery = row["battery_v"]
        if battery is None:
            battery_text = "-"
        elif battery < 3.5:
            battery_text = f"[yellow]{battery:.2f}[/yellow]"
        else:
            battery_text = f"{battery:.2f}"

        table.add_row(
            str(row["node_id"]),
            status_text,
            f"{age_s:.1f}s",
            str(row["last_seq"]),
            rssi_text,
            battery_text,
            str(row["missed_packets"]),
            str(row["mode"]),
            str(row["wifi_ip"])
        )

    return Panel(table, border_style="magenta")


def make_events_table(events):
    table = Table(
        title="Latest Events",
        expand=True,
        header_style="bold yellow"
    )

    table.add_column("Time", no_wrap=True)
    table.add_column("Event", no_wrap=True)
    table.add_column("Node", no_wrap=True)

    if not events:
        table.add_row("-", "NO EVENTS", "-")
        return Panel(table, border_style="yellow")

    for row in events:
        t = row["event_time"].split("T")[-1].split(".")[0]
        event_type = row["event_type"]
        node_id = row["node_id"] or "-"

        style = "white"
        if "TIMEOUT" in event_type:
            style = "red"
        elif "RECOVERED" in event_type:
            style = "green"
        elif "COMMAND" in event_type:
            style = "cyan"

        table.add_row(t, f"[{style}]{event_type}[/{style}]", node_id)

    return Panel(table, border_style="yellow")


def make_telemetry_table(records):
    table = Table(
        title="Latest Telemetry",
        expand=True,
        header_style="bold blue"
    )

    table.add_column("Time", no_wrap=True)
    table.add_column("Node", no_wrap=True)
    table.add_column("Seq", justify="right")
    table.add_column("Temp", justify="right")
    table.add_column("Hum", justify="right")
    table.add_column("RSSI", justify="right")
    table.add_column("Bat", justify="right")

    if not records:
        table.add_row("-", "-", "-", "-", "-", "-", "-")
        return Panel(table, border_style="blue")

    for row in records:
        t = row["server_time"].split("T")[-1].split(".")[0]

        temp = "-" if row["temp_c"] is None else f"{row['temp_c']:.1f}"
        hum = "-" if row["humidity"] is None else f"{row['humidity']:.1f}"
        bat = "-" if row["battery_v"] is None else f"{row['battery_v']:.2f}"

        table.add_row(
            t,
            str(row["node_id"]),
            str(row["seq"]),
            temp,
            hum,
            str(row["rssi_dbm"]),
            bat
        )

    return Panel(table, border_style="blue")


def build_layout():
    node_rows = fetch_node_rows()
    events = fetch_latest_events()
    telemetry = fetch_latest_telemetry()

    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="bottom", size=13)
    )

    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=3)
    )

    layout["left"].split_column(
        Layout(name="system"),
        Layout(name="summary")
    )

    layout["bottom"].split_row(
        Layout(name="events"),
        Layout(name="telemetry")
    )

    layout["header"].update(make_header())
    layout["system"].update(make_system_panel())
    layout["summary"].update(make_summary_panel(node_rows))
    layout["right"].update(make_node_table(node_rows))
    layout["events"].update(make_events_table(events))
    layout["telemetry"].update(make_telemetry_table(telemetry))

    return layout


def main():
    with Live(
        build_layout(),
        refresh_per_second=1,
        console=console,
        screen=True
    ) as live:
        while True:
            live.update(build_layout())
            time.sleep(REFRESH_S)


if __name__ == "__main__":
    main()
