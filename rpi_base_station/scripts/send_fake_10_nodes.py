import time
import random
import requests

URL = "http://127.0.0.1:8000/api/telemetry"

nodes = {}

for i in range(1, 11):
    node_id = f"NODE_{i:02d}"
    nodes[node_id] = {
        "seq": 1,
        "battery_v": round(random.uniform(3.85, 4.15), 2),
        "ip": f"192.168.1.{100+i}"
    }

print("Starting fake 10-node WSN simulator...")
print("Sending telemetry to:", URL)
print("Press Ctrl+C to stop.")
print()

while True:
    for node_id, state in nodes.items():
        # Slowly drain battery
        state["battery_v"] = max(3.30, state["battery_v"] - random.uniform(0.000, 0.002))

        # Simulate normal RSSI, with occasional weak link
        if node_id in ["NODE_07", "NODE_09"]:
            rssi = random.randint(-82, -68)
        else:
            rssi = random.randint(-65, -45)

        payload = {
            "node_id": node_id,
            "seq": state["seq"],
            "uptime_ms": state["seq"] * 5000,
            "mode": "NORMAL",
            "last_command": "NONE",
            "temp_c": round(random.uniform(27.0, 31.0), 2),
            "humidity": round(random.uniform(68.0, 76.0), 2),
            "pressure_hpa": round(random.uniform(1007.0, 1010.0), 2),
            "rssi_dbm": rssi,
            "battery_v": round(state["battery_v"], 2),
            "wifi_ip": state["ip"]
        }

        try:
            r = requests.post(URL, json=payload, timeout=3)
            print(node_id, "seq", state["seq"], "status", r.status_code)
        except Exception as e:
            print(node_id, "SEND FAILED:", e)

        state["seq"] += 1

        # Small delay between nodes so database updates smoothly
        time.sleep(0.2)

    print("-" * 50)
    time.sleep(5)
