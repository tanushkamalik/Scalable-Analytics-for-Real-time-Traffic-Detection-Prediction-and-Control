import time 
import streamlit as st
import pandas as pd
import json, os
import plotly.express as px
import numpy as np
from datetime import timedelta
import sqlite3
import os 

if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True


def load_db_data(limit=100):
    try:
        conn = sqlite3.connect("traffic_data.db")
        df = pd.read_sql_query(
            f"SELECT * FROM traffic_data ORDER BY id DESC LIMIT {limit}",
            conn
        )
        conn.close()
        return df
    except Exception as e:
        return None

def get_db_stats():
    if not os.path.exists("traffic_data.db"):
        return None

    conn = sqlite3.connect("traffic_data.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM traffic_data")
    count = cur.fetchone()[0]

    cur.execute("SELECT timestamp FROM traffic_data ORDER BY id DESC LIMIT 1")
    last = cur.fetchone()
    last_time = last[0] if last else "N/A"

    conn.close()

    size_mb = round(os.path.getsize("traffic_data.db") / (1024 * 1024), 2)

    return {
        "count": count,
        "last_time": last_time,
        "size_mb": size_mb
    }

st.set_page_config("Smart City Traffic Dashboard", layout="wide")

# ------------------ CSS ------------------
st.markdown("""
<style>
section[data-testid="stSidebar"] * { color:black !important; }
.metric-box {
    background:#ffffff;
    padding:20px;
    border-radius:12px;
    box-shadow:0px 4px 14px rgba(0,0,0,0.08);
    text-align:center;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# GLOBAL DATA GUARANTEE (FIX ALL NameError ISSUES)
# ======================================================
def load_data():
    try:
        conn = sqlite3.connect("traffic_data.db")

        df = pd.read_sql_query(
            "SELECT * FROM traffic_data ORDER BY id DESC LIMIT 1000",
            conn
        )

        conn.close()

        if df.empty:
            return pd.DataFrame()

        # Convert timestamp safely
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])

        return df

    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

df = load_data()
if df is None:
    df = pd.DataFrame()

# ------------------ SIDEBAR ------------------
section = st.sidebar.radio(
    "Navigation",
    [
        "🚦 Live Overview",
        "🔥 Accident Intelligence",
        "📈 Congestion Trends",
        "🚦 Signal & Ambulance Control",
        "🗺 Hotspot Map",
        "📽 Camera Feed",
        "📑 Admin Summary",
        "🗄 Database Records"
    ]
)

st.title("🚦 Smart City Traffic Dashboard – Bengaluru")
st.caption(f"🔄 Data reloaded at: {pd.Timestamp.now()}")

# ======================================================
# 🚦 LIVE OVERVIEW
# ======================================================
if section == "🚦 Live Overview":
    
    latest = df.sort_values("timestamp").groupby("junction_id").tail(1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Vehicles", int(latest.vehicle_count.mean()))
    c2.metric("Avg Speed (km/h)", int(latest.avg_speed.mean()))
    c3.metric("Avg Congestion", round(latest.congestion_index.mean(),1))
    c4.metric("Risk Score", round(latest.risk_score.mean(),1))

    st.dataframe(latest, use_container_width=True)

# ======================================================
# 🔥 ACCIDENT INTELLIGENCE (DECISION-ORIENTED)
# ======================================================
elif section == "🔥 Accident Intelligence":
    st.subheader("🔥 Accident Intelligence & Risk Prioritization")

    # ---------- PREP ----------
    window = df.sort_values("timestamp").tail(300).copy()

    # ✅ FIXED: weather handling INSIDE block
    if "weather" not in window.columns:
        window["weather"] = "Clear"

    window["weather"] = window["weather"].fillna("Clear")

    # Normalize severity score
    sev_weight = {"Slight": 1, "Serious": 2, "Fatal": 3}
    window["sev_w"] = window["accident_severity"].map(sev_weight).fillna(1)

    # Composite Accident Risk Index (0–100)
    window["ARI"] = (
        0.55 * window["accident_probability"] +
        0.30 * window["sev_w"] * 20 +
        0.15 * window["congestion_index"]
    ).clip(0, 100)

    # Junction-level aggregation
    jn = (
        window.groupby("junction_id")
        .agg(
            avg_prob=("accident_probability", "mean"),
            max_sev=("accident_severity", lambda x: x.value_counts().index[0]),
            avg_ci=("congestion_index", "mean"),
            ari=("ARI", "mean"),
            events=("ARI", "count")
        )
        .sort_values("ari", ascending=False)
        .reset_index()
    )

    # KPI
    top = jn.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚨 Highest Risk Junction", top["junction_id"])
    c2.metric("🧮 Accident Risk Index", f"{top['ari']:.1f}")
    c3.metric("💥 Dominant Severity", top["max_sev"])
    c4.metric("🧯 Events (window)", int(top["events"]))

    # Root cause
    cause = (
        window.assign(
            cause=np.select(
                [
                    window["avg_speed"] < 20,
                    window["weather"].isin(["Rain", "Fog"]),
                    window["incident_level"] >= 2
                ],
                [
                    "Low Speed / Jam",
                    "Adverse Weather",
                    "Incident / Breakdown"
                ],
                default="Mixed Traffic"
            )
        )
        .groupby("cause")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    st.plotly_chart(
        px.bar(cause, x="cause", y="count", text_auto=True),
        use_container_width=True
    )

    # ---------- RISK DISTRIBUTION (CLEAR, NOT NOISY) ----------
    st.markdown("### 📊 Accident Risk by Junction (Ranked)")
    st.plotly_chart(
        px.bar(
            jn,
            x="junction_id",
            y="ari",
            color="ari",
            color_continuous_scale=["#2ECC71", "#F1C40F", "#E67E22", "#E74C3C"],
            text_auto=".1f"
        ),
        use_container_width=True
    )

    # ---------- ACTION PLAYBOOK ----------
    st.markdown("### 🛠️ Action Playbook (Auto-Generated)")
    def recommend(row):
        if row["ari"] >= 80:
            return "🚑 Alert EMS • 🚦 Extend green • 🚓 Deploy police • 📣 Public advisory"
        if row["ari"] >= 60:
            return "🚦 Adaptive signals • 🚓 Patrol • ⚠️ Warning signage"
        if row["ari"] >= 40:
            return "🟡 Monitor • 🚦 Minor timing tweaks"
        return "🟢 Observe"

    actions = jn.copy()
    actions["Recommended Action"] = actions.apply(recommend, axis=1)

    st.dataframe(
        actions[["junction_id", "ari", "Recommended Action"]],
        use_container_width=True
    )

    # ---------- TREND (SMOOTHED & FOCUSED) ----------
    st.markdown("### 📈 Risk Trend (Smoothed, Top Junction)")
    tj = top["junction_id"]
    trend = window[window["junction_id"] == tj].sort_values("timestamp").copy()
    trend["ARI_smooth"] = trend["ARI"].rolling(5, min_periods=1).mean()

    st.plotly_chart(
        px.line(
            trend.tail(120),
            x="timestamp",
            y="ARI_smooth",
            title=f"Smoothed Accident Risk Trend – {tj}",
            labels={"ARI_smooth": "Accident Risk Index"}
        ),
        use_container_width=True
    )

    # ---------- EXEC SUMMARY ----------
    st.markdown(
        f"""
        **Executive Summary**
        - **Critical junction:** `{top['junction_id']}`
        - **Why:** Elevated congestion + severity mix
        - **Now:** {recommend(top)}
        """
    )

# ======================================================
# 📈 CONGESTION TRENDS (FIXED)
# ======================================================
elif section == "📈 Congestion Trends":
    junction = st.selectbox("Select Junction", df.junction_id.unique())

    sub = df[df.junction_id==junction].sort_values("timestamp")
    sub = sub[sub.timestamp > sub.timestamp.max() - timedelta(minutes=15)]

    sub["smooth"] = sub.congestion_index.rolling(5, min_periods=1).mean()

    fig = px.line(
        sub,
        x="timestamp",
        y="smooth",
        title=f"Smoothed Congestion Trend – {junction}"
    )
    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# 🚦 SIGNAL & 🚑 AMBULANCE CONTROL (SIMULATED)
# ======================================================
elif section == "🚦 Signal & Ambulance Control":
    st.subheader("🚦 Intelligent Signal & 🚑 Ambulance Control Center")

    import random
    import plotly.express as px

    # --------------------------------------------------
    # FALLBACK SAFE DATA
    # --------------------------------------------------
    fallback = pd.DataFrame([
        {"junction_id":"J1","congestion_index":78,"incident_level":2},
        {"junction_id":"J2","congestion_index":56,"incident_level":1},
        {"junction_id":"J3","congestion_index":35,"incident_level":0},
        {"junction_id":"J4","congestion_index":22,"incident_level":0},
        {"junction_id":"J5","congestion_index":15,"incident_level":0},
    ])

    try:
        if df is None or df.empty:
            live = fallback
            st.warning("Simulation mode: Live feed unavailable")
        else:
            df_use = df.copy()
            df_use["timestamp"] = pd.to_datetime(df_use["timestamp"], errors="coerce")
            df_use = df_use.dropna(subset=["timestamp"])
            if df_use.empty:
                live = fallback
            else:
                live = (
                    df_use.sort_values("timestamp")
                    .groupby("junction_id")
                    .tail(1)[["junction_id","congestion_index","incident_level"]]
                )
    except:
        live = fallback

    # --------------------------------------------------
    # 🚦 SIGNAL LOGIC + COUNTDOWN
    # --------------------------------------------------
    def signal_logic(ci):
        if ci >= 75:
            return "🔴 RED EXTENDED", random.randint(70, 110), "Severe congestion"
        elif ci >= 50:
            return "🟡 ADAPTIVE", random.randint(40, 70), "Rising traffic density"
        return "🟢 NORMAL", random.randint(20, 40), "Smooth traffic flow"

    live[["Signal State","Countdown","Signal Reason"]] = live.apply(
        lambda r: pd.Series(signal_logic(r["congestion_index"])),
        axis=1
    )

    # --------------------------------------------------
    # 🚑 AMBULANCE PRIORITY + CORRIDOR
    # --------------------------------------------------
    def ambulance_logic(inc):
        if inc >= 2:
            return "🚑 ACTIVE", "Green corridor enabled"
        return "—", "No ambulance priority"

    live[["Ambulance Status","Ambulance Action"]] = live.apply(
        lambda r: pd.Series(ambulance_logic(r["incident_level"])),
        axis=1
    )

    # --------------------------------------------------
    # KPI ROW
    # --------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚦 Adaptive Signals", int((live["Signal State"] != "🟢 NORMAL").sum()))
    c2.metric("🚑 Ambulance Active", int((live["Ambulance Status"] == "🚑 ACTIVE").sum()))
    c3.metric("🔥 High Congestion", int((live["congestion_index"] > 70).sum()))
    c4.metric("🧠 Control Mode", "AI-DRIVEN")

    # --------------------------------------------------
    # SIGNAL CONTROL BOARD
    # --------------------------------------------------
    st.markdown("### 🧭 Live Signal Control Board")

    board = live.rename(columns={
        "junction_id":"Junction",
        "congestion_index":"Congestion Index",
        "incident_level":"Incident Level"
    })

    st.dataframe(
        board[[
            "Junction",
            "Congestion Index",
            "Signal State",
            "Countdown",
            "Signal Reason",
            "Ambulance Status"
        ]].sort_values("Congestion Index", ascending=False),
        use_container_width=True
    )

    # --------------------------------------------------
    # 🚑 AMBULANCE CORRIDOR MAP
    # --------------------------------------------------
    st.markdown("### 🚑 Ambulance Green Corridor")

    coords = {
        "J1":(12.9716,77.5946),
        "J2":(12.975,77.6),
        "J3":(12.968,77.59),
        "J4":(12.965,77.585),
        "J5":(12.96,77.58)
    }

    map_df = live.copy()
    map_df["lat"] = map_df["junction_id"].map(lambda j: coords[j][0])
    map_df["lon"] = map_df["junction_id"].map(lambda j: coords[j][1])

    map_df["priority"] = map_df["Ambulance Status"].apply(
        lambda x: "Ambulance Corridor" if x == "🚑 ACTIVE" else "Normal Traffic"
    )

    fig = px.scatter_mapbox(
        map_df,
        lat="lat",
        lon="lon",
        color="priority",
        size="congestion_index",
        size_max=35,
        zoom=12,
        center={"lat":12.9716,"lon":77.5946},
        color_discrete_map={
            "Ambulance Corridor":"#2ECC71",
            "Normal Traffic":"#E74C3C"
        },
        hover_name="junction_id"
    )

    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0,r=0,t=0,b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------
    # 🧠 EXPLAINABLE AI PANEL
    # --------------------------------------------------
    st.markdown("### 🧠 AI Decision Explanation")

    critical = board.sort_values("Congestion Index", ascending=False).iloc[0]

    st.success(
        f"""
        **Why did the system act?**

        - **Junction:** {critical['Junction']}
        - **Observed congestion:** {critical['Congestion Index']}
        - **Signal decision:** {critical['Signal State']}
        - **Reason:** {critical['Signal Reason']}
        - **Ambulance handling:** {critical['Ambulance Status']}

        **System Action:** Signal timing adjusted automatically to minimize delays
        """
    )

# ======================================================
# 🗺 HOTSPOT MAP (CLEAN & MEANINGFUL)
# ======================================================
elif section == "🗺 Hotspot Map":
    st.subheader("🌆 City-Wide Traffic Intelligence Map")

    import random

    # -------------------------------------------------
    # FIXED JUNCTION COORDINATES
    # -------------------------------------------------
    JUNCTION_COORDS = {
        "J1": (12.9716, 77.5946),
        "J2": (12.9750, 77.6000),
        "J3": (12.9680, 77.5900),
        "J4": (12.9650, 77.5850),
        "J5": (12.9600, 77.5800),
    }

    # -------------------------------------------------
    # LATEST SNAPSHOT
    # -------------------------------------------------
    latest = (
        df.sort_values("timestamp")
          .groupby("junction_id")
          .tail(1)
          .copy()
    )

    # -------------------------------------------------
    # KPI CARDS (ABOVE MAP)
    # -------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🔥 Most Congested Junction",
        latest.sort_values("congestion_index", ascending=False).iloc[0]["junction_id"]
    )
    c2.metric(
        "📈 Avg City Congestion",
        f"{latest['congestion_index'].mean():.1f}"
    )
    c3.metric(
        "🚑 High-Risk Zones",
        int((latest["congestion_index"] > 70).sum())
    )
    c4.metric(
        "🚦 Signals in Adaptive Mode",
        int((latest["congestion_index"] > 60).sum())
    )

    # -------------------------------------------------
    # ZOOM-BASED DETAIL CONTROL
    # -------------------------------------------------
    zoom_level = st.slider(
        "Map Detail Level",
        min_value=10,
        max_value=14,
        value=12
    )

    spread = 0.008 if zoom_level <= 11 else 0.004
    density = 20 if zoom_level <= 11 else 35

    # -------------------------------------------------
    # GENERATE CITY-WIDE HEAT POINTS
    # -------------------------------------------------
    heat_points = []

    for _, row in latest.iterrows():
        base_lat, base_lon = JUNCTION_COORDS[row["junction_id"]]
        ci = row["congestion_index"]

        for _ in range(density):
            heat_points.append({
                "lat": base_lat + random.uniform(-spread, spread),
                "lon": base_lon + random.uniform(-spread, spread),
                "congestion": max(5, min(100, ci + random.uniform(-20, 20))),
                "junction": row["junction_id"]
            })

    heat_df = pd.DataFrame(heat_points)
    heat_df["size"] = heat_df["congestion"] / 100 * 28 + 6

    # -------------------------------------------------
    # 🚦 TRAFFIC SIGNAL STATE (ANIMATED LOGIC)
    # -------------------------------------------------
    def signal_state(ci):
        if ci > 75:
            return "🔴 Red (Extended)"
        elif ci > 45:
            return "🟡 Yellow (Adaptive)"
        return "🟢 Green (Normal)"

    latest["signal"] = latest["congestion_index"].apply(signal_state)

    # -------------------------------------------------
    # MAP VISUALIZATION
    # -------------------------------------------------
    fig = px.scatter_mapbox(
        heat_df,
        lat="lat",
        lon="lon",
        size="size",
        color="congestion",
        color_continuous_scale=[
            "#2ECC71",
            "#F1C40F",
            "#E67E22",
            "#E74C3C"
        ],
        zoom=zoom_level,
        center={"lat": 12.9716, "lon": 77.5946},
        opacity=0.6,
        hover_data={
            "junction": True,
            "congestion": True,
            "size": False
        }
    )

    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_showscale=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------
    # SIGNAL STATUS TABLE (LIVE)
    # -------------------------------------------------
    st.subheader("🚦 Live Traffic Signal Status")

    st.dataframe(
        latest[["junction_id", "congestion_index", "signal"]]
        .sort_values("congestion_index", ascending=False),
        use_container_width=True
    )

    # -------------------------------------------------
    # SMART INSIGHT
    # -------------------------------------------------
    worst = latest.sort_values("congestion_index", ascending=False).iloc[0]

    st.markdown(f"""
    ### 🧠 System Insight
    - **Critical junction:** `{worst['junction_id']}`
    - **Congestion index:** `{worst['congestion_index']:.1f}`
    - **Signal action:** `{worst['signal']}`
    - **City status:** Traffic dynamically controlled using congestion-aware logic
    """)
# ======================================================
# 📽 CAMERA FEED (SAFE PLACEHOLDER)
# ======================================================
elif section == "📽 Camera Feed":
    st.warning("Live camera feed unavailable")
    st.image("https://via.placeholder.com/800x400.png?text=Camera+Feed+Offline")

# ======================================================
# 📑 ADMIN SUMMARY
# ======================================================
elif section == "📑 Admin Summary":

    # ------------------------------------
    # DATABASE STATUS
    # ------------------------------------
    st.markdown("### 💾 Database Status")

    stats = get_db_stats()

    if stats is None:
        st.error("Database not found")
    else:
        c1, c2, c3, c4 = st.columns(4)

        c1.metric("📦 Total Records", stats["count"])
        c2.metric("🕒 Last Insert", stats["last_time"])
        c3.metric("💾 DB Size (MB)", stats["size_mb"])
        c4.metric("🟢 DB Health", "OK")

    # ------------------------------------
    # EXECUTIVE SUMMARY
    # ------------------------------------
    st.subheader("Executive Summary")

    st.markdown(f"""
    - **Peak congestion junction:** {df.groupby("junction_id").congestion_index.mean().idxmax()}
    - **Average city congestion:** {df.congestion_index.mean():.1f}
    - **High-risk incidents detected:** {(df.incident_level >= 2).sum()}
    """)

    st.caption("Smart City Traffic Intelligence System | Academic Demonstration")


    # ======================================================
elif section == "🗄 Database Records":

    st.subheader("🗄 Stored Traffic Data (Database View)")
    st.caption("Live data stored in SQLite database")

    df_db = load_db_data(limit=10000000000)

    if df_db is None or df_db.empty:
        st.warning("No data found in database")
    else:
        st.success(f"Showing latest {len(df_db)} records")

        st.dataframe(
            df_db,
            use_container_width=True
        )

# ======================================================
# SAFE AUTO REFRESH (AFTER UI RENDER)
# ======================================================
if st.session_state.get("auto_refresh", True):
    time.sleep(6)
    st.rerun()