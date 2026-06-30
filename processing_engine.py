# processing_engine.py
import time 
import os 
from db_writer import insert_record   # ✅ SQLite writer
import json
import pickle
import random
import numpy as np
from datetime import datetime

# -------------------------------
# Load ML models safely
# -------------------------------
try:
    severity_model = pickle.load(open("accident_rf.pkl", "rb"))
except:
    severity_model = None

try:
    prob_model = pickle.load(open("accident_prob_model.pkl", "rb"))
except:
    prob_model = None

# -------------------------------
# Helper functions
# -------------------------------
def compute_congestion(vc, sp, inc):
    return max(0, min(100, vc * 0.55 + (50 - sp) * 0.9 + inc * 14))

def predict_phase(ci):
    if ci < 25:
        return "Normal"
    elif ci < 50:
        return "Slow"
    elif ci < 75:
        return "Congested"
    return "Extreme Congestion"

def incident_type(sp, inc, weather):
    if inc >= 3:
        return "Major Collision"
    if weather == "Rain" and sp < 25:
        return "Skidding / Hydroplaning"
    if inc == 2:
        return "Vehicle Breakdown"
    if sp < 20:
        return "Signal Failure / Jam"
    return "No Incident"

print("⚡ Processing Engine Started")

# -------------------------------
# Process raw file → processed file + database
# -------------------------------
print("⚡ Processing Engine Running in LIVE MODE")

last_processed_line = 0

while True:
    if not os.path.exists("raw_traffic_stream.jsonl"):
        time.sleep(2)
        continue

    with open("raw_traffic_stream.jsonl", "r") as rf:
        lines = rf.readlines()

    # Process only NEW lines
    new_lines = lines[last_processed_line:]

    for line in new_lines:
        try:
            rec = json.loads(line)
        except:
            continue

        vc = rec["vehicle_count"] + random.randint(-5, 5)
        sp = max(5, rec["avg_speed"] + random.randint(-3, 3))
        inc = rec["incident_level"]
        weather = rec["weather"]

        congestion = compute_congestion(vc, sp, inc)
        phase = predict_phase(congestion)
        block_prob = min(100, congestion * 0.5)
        accident_prob = min(100, congestion * 0.6 + inc * 15)
        risk_score = min(100, congestion * 0.7 + inc * 20)

        final = {
            **rec,
            "congestion_index": round(congestion, 2),
            "traffic_phase": phase,
            "blockage_probability": round(block_prob, 2),
            "incident_prediction": incident_type(sp, inc, weather),
            "accident_severity": random.choice(["Slight", "Serious", "Fatal"]),
            "accident_probability": round(accident_prob, 2),
            "risk_score": round(risk_score, 2),
            "processed_at": datetime.utcnow().isoformat() + f"_{time.time()}"
        }

        # ---- DATABASE INSERT ----
        try:
            insert_record(final)
        except Exception as e:
            print("Database insert failed:", e)

        # ---- WRITE TO PROCESSED FILE ----
        with open("processed_traffic_stream.jsonl", "a") as pf:
            pf.write(json.dumps(final) + "\n")

        print("Processed:", final)

    # Update pointer
    last_processed_line = len(lines)

    # Control live speed
    time.sleep(3)