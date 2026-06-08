import time
import requests
import random

URL = "http://127.0.0.1:8000/api/telemetry"

seq = 100

while True:
    payload = {
        "node_id": "NODE_01",
        "seq": seq,
        "uptime_ms": seq * 1000,
        "mode": "NORMAL",
        "last_command": "NONE",
        "temp_c": round(28.0 + random.random() * 2.0, 2),
        "humidity": round(70.0 + random.random() * 4.0, 2),
        "pressure_hpa": round(1008.0 + random.random(), 2),
        "rssi_dbm": random.randint(-65, -50),
        "battery_v": round(4.0 + random.random() * 0.1, 2),
        "wifi_ip": "192.168.1.101"
    }

    try:
        r = requests.post(URL, json=payload, timeout=3)
        print(seq, r.status_code, r.text)
    except Exception as e:
        print("SEND FAILED:", e)

    seq += 1
    time.sleep(5)
