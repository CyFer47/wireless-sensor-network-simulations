from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import sqlite3
import json
from pathlib import Path


def normalize_node_id(node_id):
    """
    Convert NODE_1, NODE_2, node_3 into NODE_01, NODE_02, NODE_03.
    Keeps NODE_10 unchanged.
    """
    if node_id is None:
        return node_id

    node_id = str(node_id).strip().upper()

    if node_id.startswith("NODE_"):
        suffix = node_id.replace("NODE_", "", 1)
        if suffix.isdigit():
            return f"NODE_{int(suffix):02d}"

    return node_id


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
    node_id = normalize_node_id(payload.node_id)

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
        "node_id": node_id,
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

            timeout_details = {
                "last_seen": row["last_seen"],
                "age_s": age_s,
                "timeout_s": HEARTBEAT_TIMEOUT_S
            }

            cur.execute(
                "INSERT INTO events (event_time, event_type, node_id, details_json) VALUES (?, ?, ?, ?)",
                (now_iso(), "NODE_TIMEOUT", row["node_id"], json.dumps(timeout_details))
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



@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html_path = BASE_DIR / "app" / "dashboard.html"
    return html_path.read_text()



@app.get("/api/ml/benchmark")
def get_ml_benchmark():
    import csv

    benchmark_path = BASE_DIR / "ml_results" / "rpi_ml_inference_benchmark.csv"

    if not benchmark_path.exists():
        return {
            "status": "missing",
            "message": "ML benchmark file not found",
            "path": str(benchmark_path),
            "models": []
        }

    rows = []

    with open(benchmark_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            clean = {}

            for key, value in row.items():
                if value is None or value == "":
                    clean[key] = value
                    continue

                try:
                    clean[key] = float(value)
                except ValueError:
                    clean[key] = value

            rows.append(clean)

    return {
        "status": "ok",
        "path": str(benchmark_path),
        "model_count": len(rows),
        "models": rows
    }


@app.get("/api/ml/decision")
def get_ml_decision():
    import sqlite3
    from datetime import datetime, timezone

    db_path = BASE_DIR / "data" / "wsn_base_station.db"

    if not db_path.exists():
        return {
            "status": "missing_database",
            "message": "Database not found",
            "ch_candidate": None,
            "nodes": []
        }

    now = datetime.now(timezone.utc)
    timeout_s = HEARTBEAT_TIMEOUT_S if "HEARTBEAT_TIMEOUT_S" in globals() else 15

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Read current node status table
    try:
        rows = cur.execute("SELECT * FROM node_status ORDER BY node_id").fetchall()
    except Exception as e:
        conn.close()
        return {
            "status": "error",
            "message": f"Could not read node_status table: {e}",
            "ch_candidate": None,
            "nodes": []
        }

    conn.close()

    nodes = []
    online_nodes = []

    for r in rows:
        d = dict(r)

        node_id = d.get("node_id")
        rssi = d.get("rssi_dbm")
        battery = d.get("battery_v")
        missed = d.get("missed_packets") or 0
        last_seq = d.get("last_seq")
        last_seen = d.get("last_seen")
        mode = d.get("mode")
        wifi_ip = d.get("wifi_ip")

        # Work out age/status
        age_s = None
        computed_status = "UNKNOWN"

        if last_seen:
            try:
                # Accept ISO timestamp with +00:00 or without timezone
                ls = str(last_seen).replace("Z", "+00:00")
                dt = datetime.fromisoformat(ls)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_s = (now - dt).total_seconds()
                computed_status = "ONLINE" if age_s <= timeout_s else "OFFLINE"
            except Exception:
                computed_status = d.get("status") or "UNKNOWN"
        else:
            computed_status = d.get("status") or "UNKNOWN"

        # Score parts
        # Battery score: assume 3.0V poor, 4.2V excellent
        if battery is None:
            battery_score = 0.0
        else:
            battery_score = max(0.0, min(1.0, (float(battery) - 3.0) / (4.2 - 3.0)))

        # RSSI score: -90 poor, -40 excellent
        if rssi is None:
            rssi_score = 0.0
        else:
            rssi_score = max(0.0, min(1.0, (float(rssi) - (-90.0)) / ((-40.0) - (-90.0))))

        # Reliability score: reduce score for missed packets
        missed = int(missed)
        reliability_score = max(0.0, 1.0 - min(missed, 20) / 20.0)

        # Online score
        online_score = 1.0 if computed_status == "ONLINE" else 0.0

        # Weighted CH score
        # Battery is most important, then RSSI, then reliability.
        ch_score = (
            0.40 * battery_score +
            0.30 * rssi_score +
            0.20 * reliability_score +
            0.10 * online_score
        )

        if computed_status != "ONLINE":
            ch_score = 0.0

        node_result = {
            "node_id": node_id,
            "status": computed_status,
            "age_s": round(age_s, 2) if age_s is not None else None,
            "battery_v": battery,
            "rssi_dbm": rssi,
            "missed_packets": missed,
            "last_seq": last_seq,
            "mode": mode,
            "wifi_ip": wifi_ip,
            "battery_score": round(battery_score, 3),
            "rssi_score": round(rssi_score, 3),
            "reliability_score": round(reliability_score, 3),
            "ch_score": round(ch_score, 3),
        }

        nodes.append(node_result)

        if computed_status == "ONLINE":
            online_nodes.append(node_result)

    if not online_nodes:
        return {
            "status": "ok",
            "network_health": "DOWN",
            "recommended_healing": "RECOVER",
            "ch_candidate": None,
            "reason": "No online nodes available for cluster-head recommendation.",
            "online_count": 0,
            "offline_count": len(nodes),
            "nodes": nodes
        }

    # Select best CH candidate
    best = max(online_nodes, key=lambda x: x["ch_score"])

    online_count = len(online_nodes)
    offline_count = len(nodes) - online_count

    # Simple network health decision
    if offline_count == 0:
        network_health = "STABLE"
        recommended_healing = "NORMAL"
    elif offline_count <= 2:
        network_health = "DEGRADED"
        recommended_healing = "RECOVER"
    else:
        network_health = "CRITICAL"
        recommended_healing = "RECOVER"

    reason = (
        f"{best['node_id']} selected because it has the best combined CH score "
        f"from battery={best['battery_v']}V, RSSI={best['rssi_dbm']}dBm, "
        f"missed_packets={best['missed_packets']}, and online status."
    )

    return {
        "status": "ok",
        "network_health": network_health,
        "recommended_healing": recommended_healing,
        "ch_candidate": best["node_id"],
        "ch_score": best["ch_score"],
        "reason": reason,
        "online_count": online_count,
        "offline_count": offline_count,
        "decision_type": "base_station_assisted_ch_recommendation",
        "note": "This is a centralized CH recommendation using live telemetry indicators, not full distributed CH election.",
        "nodes": sorted(nodes, key=lambda x: x["ch_score"], reverse=True)
    }
