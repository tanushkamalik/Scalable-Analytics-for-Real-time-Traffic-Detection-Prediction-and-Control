import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

print("🚀 Loading dataset...")

# LOAD DATASET
df = pd.read_csv("data/Accident_Information.csv", low_memory=False)

print("Dataset loaded. Preparing columns...")

# SELECT REQUIRED COLUMNS
df = df[[
    "Number_of_Vehicles",
    "Speed_limit",
    "Weather_Conditions",
    "Road_Type",
    "Accident_Severity"
]]

# RENAME COLUMNS
df = df.rename(columns={
    "Number_of_Vehicles": "vehicle_count",
    "Speed_limit": "avg_speed",
    "Weather_Conditions": "weather",
    "Road_Type": "road_type",
    "Accident_Severity": "severity"
})

# DROP NA
df = df.dropna()

# ENCODE WEATHER + ROAD TYPE
df["weather"] = df["weather"].astype("category").cat.codes
df["road_type"] = df["road_type"].astype("category").cat.codes

# ENCODE SEVERITY LABELS
severity_map = {
    "Slight": 1,
    "Serious": 2,
    "Fatal": 3
}

df["severity"] = df["severity"].map(severity_map)

print("Severity encoded as numbers:", severity_map)

# SIMULATED INCIDENT LEVEL
def compute_incident_level(row):
    if row["avg_speed"] < 20:
        return 3
    if row["avg_speed"] < 30:
        return 2
    if row["avg_speed"] < 40:
        return 1
    return 0

df["incident_level"] = df.apply(compute_incident_level, axis=1)

# PREPARE FEATURES
X = df[["vehicle_count", "avg_speed", "incident_level", "weather", "road_type"]]
y = df["severity"]

# TRAIN/TEST SPLIT
print("Splitting dataset...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# TRAIN MODEL
print("Training model...")
model = RandomForestClassifier(n_estimators=300, max_depth=12, random_state=42)
model.fit(X_train, y_train)

# EVALUATE
print("\n📊 Severity Model Performance:\n")
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# SAVE MODEL
pickle.dump(model, open("accident_rf.pkl", "wb"))
print("\n✅ Accident Severity Model Saved As: accident_rf.pkl")
