import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

print("🚀 Loading dataset for probability model...")

df = pd.read_csv("data/Accident_Information.csv", low_memory=False)

# Select required columns
df = df[[
    "Number_of_Vehicles",
    "Speed_limit",
    "Weather_Conditions",
    "Road_Type",
    "Accident_Severity"
]]

# Rename for consistency
df = df.rename(columns={
    "Number_of_Vehicles": "vehicle_count",
    "Speed_limit": "avg_speed",
    "Weather_Conditions": "weather",
    "Road_Type": "road_type",
    "Accident_Severity": "severity"
})

df = df.dropna()

# Encode weather + road type
df["weather"] = df["weather"].astype("category").cat.codes
df["road_type"] = df["road_type"].astype("category").cat.codes

# Encode severity (used to generate probability)
severity_map = {"Slight": 1, "Serious": 2, "Fatal": 3}
df["severity"] = df["severity"].map(severity_map)

# Downsample for speed
df = df.sample(n=50000, random_state=42)

# Compute incident level (same logic as processing engine)
def compute_incident_level(row):
    if row["avg_speed"] < 20:
        return 3
    if row["avg_speed"] < 30:
        return 2
    if row["avg_speed"] < 40:
        return 1
    return 0

df["incident_level"] = df.apply(compute_incident_level, axis=1)

# Create probability label (0–100)
df["accident_probability"] = df["severity"].map({
    1: np.random.uniform(5, 30),    # Slight
    2: np.random.uniform(30, 70),   # Serious
    3: np.random.uniform(70, 100)   # Fatal
})

# Features and label
X = df[["vehicle_count", "avg_speed", "incident_level", "weather", "road_type"]]
y = df["accident_probability"]

# Split
print("Splitting probability dataset...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train probability model
print("Training accident probability model...")
model = RandomForestRegressor(
    n_estimators=150,
    max_depth=12,
    random_state=42
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
print(f"\n📊 Accident Probability Model MAE: {mae:.2f}")

# Save model
pickle.dump(model, open("accident_prob_model.pkl", "wb"))
print("\n✅ Accident Probability Model Saved As: accident_prob_model.pkl")
