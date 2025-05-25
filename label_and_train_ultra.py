
import pandas as pd
import joblib
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE
import glob
from datetime import datetime

# === Load Weather Data ===
df = pd.read_csv("weather_full_multilocation.csv")
df['time'] = pd.to_datetime(df['time'], errors='coerce')
df['rounded_time'] = df['time'].dt.floor("h")

# === Add Intelligent Features (Deltas) ===
df["temp_delta"] = df["temperature_2m"].diff().fillna(0)
df["humidity_delta"] = df["relative_humidity_2m"].diff().fillna(0)
df["wind_delta"] = df["wind_speed_10m"].diff().fillna(0)

# === Load Tornado Data ===
tornado_files = glob.glob("tornado_data/*.csv")
tornado_rows = []

for file in tornado_files:
    tdf = pd.read_csv(file, low_memory=False)
    tdf = tdf[tdf["EVENT_TYPE"].str.lower() == "tornado"]
    tdf = tdf[["BEGIN_DATE_TIME", "BEGIN_LAT", "BEGIN_LON"]].dropna()
    tdf["BEGIN_DATE_TIME"] = pd.to_datetime(tdf["BEGIN_DATE_TIME"], errors="coerce")
    tdf["rounded_time"] = tdf["BEGIN_DATE_TIME"].dt.floor("h")
    tornado_rows.append(tdf.dropna())

tornado_df = pd.concat(tornado_rows, ignore_index=True)

# === Match Tornado Events to Weather ===
def is_tornado(row):
    return int(((abs(tornado_df["BEGIN_LAT"] - row["lat"]) < 0.1) &
                (abs(tornado_df["BEGIN_LON"] - row["lon"]) < 0.1) &
                (tornado_df["rounded_time"] == row["rounded_time"])).any())

df["tornado"] = df.apply(is_tornado, axis=1)

# === Select Features for Training ===
features = [
    "temperature_2m", "dew_point_2m", "relative_humidity_2m",
    "surface_pressure", "wind_speed_10m", "cloud_cover",
    "cloud_cover_mid", "precipitation", "apparent_temperature",
    "temp_delta", "humidity_delta", "wind_delta"
]

df = df.dropna(subset=features + ["tornado"])

X = df[features]
y = df["tornado"]

# === Balance Dataset Using SMOTE ===
X_balanced, y_balanced = SMOTE(k_neighbors=3).fit_resample(X, y)

# === Cross-Validated Grid Search ===
params = {
    "n_estimators": [300],
    "max_depth": [4, 6],
    "learning_rate": [0.03, 0.05],
    "subsample": [0.8],
    "colsample_bytree": [0.8, 0.9]
}

model = XGBClassifier(
    use_label_encoder=False,
    eval_metric="logloss",
    n_jobs=-1
)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

grid = GridSearchCV(model, params, scoring='f1', cv=cv, verbose=1)
grid.fit(X_balanced, y_balanced)

# === Best Model Evaluation ===
best_model = grid.best_estimator_

X_train, X_test, y_train, y_test = train_test_split(X_balanced, y_balanced, test_size=0.2, random_state=42)
y_pred = best_model.predict(X_test)

print("Best Params:", grid.best_params_)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("Classification Report:\n", classification_report(y_test, y_pred))

# === Save Final Model ===
joblib.dump(best_model, "aerocast_model_ultra.pkl")
