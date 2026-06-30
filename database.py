import sqlite3

DB_NAME = "traffic_data.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS traffic_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            city TEXT,
            junction_id TEXT,
            vehicle_count INTEGER,
            avg_speed REAL,
            congestion_index REAL,
            accident_probability REAL,
            accident_severity TEXT,
            risk_score REAL,
            incident_level INTEGER
        )
    """)

    conn.commit()
    conn.close()