from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "wsn_base_station.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEARTBEAT_TIMEOUT_S = 15

app = FastAPI(title="WSN Raspberry Pi Base Station")


class TelemetryPayload(BaseModel):
    node_id: str
    seq: Optional[int] = None
    uptime_ms: Optional[int] = None
    mode: Optional[str] = "NORMAL"
    last_command: Optional[str] = "NONE"
    temp_c: Optional[float] = None
    humidity: Optional[float] = None
    pressure_hpa: Optional[float] = None
    rssi_dbm: Optional[int] = None
    battery_v: Optional[float] = None
    wifi_ip: Optional[str] = None


class CommandPayload(BaseModel):
    command: str = "NORMAL"
    send_interval_ms: Optional[int] = None


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_time TEXT NOT NULL,
        node_id TEXT NOT NULL,
        seq INTEGER,
        uptime_ms INTEGER,
        mode TEXT,
        last_command TEXT,
        temp_c REAL,
        humidity REAL,
        pressure_hpa REAL,
        rssi_dbm INTEGER,
        battery_v REAL,
        wifi_ip TEXT,
        raw_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS node_status (
        node_id TEXT PRIMARY KEY,
        last_seen TEXT NOT NULL,
        last_seq INTEGER,
        status TEXT NOT NULL,
        mode TEXT,
        rssi_dbm INTEGER,
        battery_v REAL,
        wifi_ip TEXT,
        missed_packets INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_time TEXT NOT NULL,
        event_type TEXT NOT NULL,
        node_id TEXT,
        details_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS commands (
        node_id TEXT PRIMARY KEY,
        command TEXT NOT NULL,
        send_interval_ms INTEGER,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def log_event(event_type, node_id, details):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (event_time, event_type, node_id, details_json) VALUES (?, ?, ?, ?)",
        (now_iso(), event_type, node_id, json.dumps(details))
    )
    conn.commit()
    conn.close()


def get_command_for_node(node_id):
    conn = connect_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT command, send_interval_ms FROM commands WHERE node_id = ?",
        (node_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return {"command": "NORMAL"}

    result = {"command": row["command"]}
    if row["send_interval_ms"] is not None:
        result["send_interval_ms"] = row["send_interval_ms"]
    return result


@app.on_event("startup")
def startup_event():
    init_db()
    print(f"Database ready: {DB_PATH}")


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "WSN Raspberry Pi Base Station",
        "database": str(DB_PATH)
    }


@app.post("/api/telemetry")
def receive_telemetry(payload: TelemetryPayload):
    init_db()

    server_time = now_iso()
    data = payload.dict()
    raw_json = json.dumps(data)

    conn = connect_db()
    cur = conn.cursor()

    previous = cur.execute(
        "SELECT * FROM node_status WHERE node_id = ?",
        (payload.node_id,)
    ).fetchone()

    missed_packets = 0

    if previous is None:
        log_event("NODE_FIRST_SEEN", payload.node_id, data)
    else:
        missed_packets = previous["missed_packets"] or 0

        if previous["status"] == "OFFLINE":
            log_event("NODE_RECOVERED", payload.node_id, data)

        if payload.seq is not None and previous["last_seq"] is not None:
            gap = payload.seq - previous["last_seq"] - 1
            if gap > 0:
                missed_packets += gap
                log_event(
                    "PACKET_GAP",
                    payload.node_id,
                    {
                        "previous_seq": previous["last_seq"],
                        "current_seq": payload.seq,
                        "gap": gap
                    }
                )

    cur.execute("""
        INSERT INTO telemetry (
            server_time, node_id, seq, uptime_ms, mode, last_command,
            temp_c, humidity, pressure_hpa, rssi_dbm, battery_v, wifi_ip, raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        server_time,
        payload.node_id,
        payload.seq,
        payload.uptime_ms,
        payload.mode,
        payload.last_command,
        payload.temp_c,
        payload.humidity,
        payload.pressure_hpa,
        payload.rssi_dbm,
        payload.battery_v,
        payload.wifi_ip,
        raw_json
    ))

    cur.execute("""
        INSERT INTO node_status (
            node_id, last_seen, last_seq, status, mode, rssi_dbm, battery_v,
            wifi_ip, missed_packets
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            last_seen = excluded.last_seen,
            last_seq = excluded.last_seq,
            status = excluded.status,
            mode = excluded.mode,
            rssi_dbm = excluded.rssi_dbm,
            battery_v = excluded.battery_v,
            wifi_ip = excluded.wifi_ip,
            missed_packets = excluded.missed_packets
    """, (
        payload.node_id,
        server_time,
        payload.seq,
        "ONLINE",
        payload.mode,
        payload.rssi_dbm,
        payload.battery_v,
        payload.wifi_ip,
        missed_packets
    ))

    conn.commit()
    conn.close()

    command_info = get_command_for_node(payload.node_id)

    return {
        "status": "ok",
        "server_time": server_time,
        "node_id": payload.node_id,
        "received_seq": payload.seq,
        **command_info
    }


@app.get("/api/status")
def get_status():
    init_db()

    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM node_status ORDER BY node_id").fetchall()

    nodes = []
    now = datetime.now(timezone.utc)

    for row in rows:
        last_seen = datetime.fromisoformat(row["last_seen"])
        age_s = (now - last_seen).total_seconds()
        current_status = row["status"]

        if age_s > HEARTBEAT_TIMEOUT_S and current_status != "OFFLINE":
            current_status = "OFFLINE"
            cur.execute(
                "UPDATE node_status SET status = ? WHERE node_id = ?",
                ("OFFLINE", row["node_id"])
            )
            log_event(
                "NODE_TIMEOUT",
                row["node_id"],
                {
                    "last_seen": row["last_seen"],
                    "age_s": age_s,
                    "timeout_s": HEARTBEAT_TIMEOUT_S
                }
            )

        nodes.append({
            "node_id": row["node_id"],
            "status": current_status,
            "age_s": round(age_s, 2),
            "last_seq": row["last_seq"],
            "mode": row["mode"],
            "rssi_dbm": row["rssi_dbm"],
            "battery_v": row["battery_v"],
            "wifi_ip": row["wifi_ip"],
            "missed_packets": row["missed_packets"]
        })

    conn.commit()
    conn.close()

    online_count = sum(1 for n in nodes if n["status"] == "ONLINE")
    offline_count = sum(1 for n in nodes if n["status"] == "OFFLINE")

    return {
        "server_time": now_iso(),
        "heartbeat_timeout_s": HEARTBEAT_TIMEOUT_S,
        "online_count": online_count,
        "offline_count": offline_count,
        "nodes": nodes
    }


@app.get("/api/latest")
def get_latest(limit: int = 20):
    init_db()
    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return {"count": len(rows), "records": [dict(row) for row in rows]}


@app.get("/api/events")
def get_events(limit: int = 50):
    init_db()
    conn = connect_db()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return {"count": len(rows), "events": [dict(row) for row in rows]}


@app.post("/api/command/{node_id}")
def set_command(node_id: str, payload: CommandPayload):
    init_db()

    allowed = {"NORMAL", "H1_FAST_REJOIN", "H3_LOAD_SHEDDING", "H4_RELAY_REBALANCE"}

    if payload.command not in allowed:
        return {
            "status": "error",
            "message": f"Invalid command. Allowed: {sorted(list(allowed))}"
        }

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO commands (node_id, command, send_interval_ms, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            command = excluded.command,
            send_interval_ms = excluded.send_interval_ms,
            updated_at = excluded.updated_at
    """, (
        node_id,
        payload.command,
        payload.send_interval_ms,
        now_iso()
    ))

    conn.commit()
    conn.close()

    log_event(
        "COMMAND_SET",
        node_id,
        {
            "command": payload.command,
            "send_interval_ms": payload.send_interval_ms
        }
    )

    return {
        "status": "ok",
        "node_id": node_id,
        "command": payload.command,
        "send_interval_ms": payload.send_interval_ms
    }
