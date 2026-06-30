import json
import time
import random
from datetime import datetime
from config import CITY_NAME, SIMULATION_INTERVAL_SECONDS

# Optional camera (ignored if not available)
try:
    from edge_vehicle_counter import get_live_metrics
    CAMERA_AVAILABLE = True
except:
    CAMERA_AVAILABLE = False

junctions = ["J1", "J2", "J3", "J4", "J5"]

print("🚦 Data Ingestion Running (Camera Optional)")

def synthetic_data():
    vehicle_count = random.randint(30, 150)
    avg_speed = random.randint(15, 60)
    incident_level = random.choice([0, 1, 2, 3])
    return vehicle_count, avg_speed, incident_level

while True:
    for j in junctions:
        vc = sp = inc = None

        if CAMERA_AVAILABLE:
            try:
                cam = get_live_metrics()
                if cam:
                    vc = cam["vehicle_count"]
                    sp = cam["avg_speed"]
                    inc = cam["incident_level"]
            except:
                pass

        if vc is None:
            vc, sp, inc = synthetic_data()

        record = {
            "timestamp": datetime.now().isoformat(),
            "city": CITY_NAME,
            "junction_id": j,
            "vehicle_count": vc,
            "avg_speed": sp,
            "incident_level": inc,
            "weather": random.choice(["Clear", "Cloudy", "Rain", "Fog"]),
            "road_type": random.choice(["Highway", "Arterial", "Residential"])
        }

        with open("raw_traffic_stream.jsonl", "a") as f:
            f.write(json.dumps(record) + "\n")

        print("Generated:", record)

    time.sleep(SIMULATION_INTERVAL_SECONDS)