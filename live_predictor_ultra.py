import requests
import joblib
import numpy as np
import datetime
import sqlite3

# === Load the trained model ===
model = joblib.load("aerocast_model_ultra.pkl")

# === Input: Location coordinates ===
lat = float(input("Enter latitude: "))
lon = float(input("Enter longitude: "))

# === Pull live weather data from Open-Meteo ===
weather_url = (
    "https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}"
    "&hourly=temperature_2m,dew_point_2m,relative_humidity_2m,"
    "surface_pressure,wind_speed_10m,cloud_cover,cloud_cover_mid,"
    "precipitation,apparent_temperature"
    "&forecast_days=1"
)

response = requests.get(weather_url)
data = response.json()["hourly"]

# === Use the most recent hour's data ===
idx = -1
features = [
    "temperature_2m", "dew_point_2m", "relative_humidity_2m",
    "surface_pressure", "wind_speed_10m", "cloud_cover",
    "cloud_cover_mid", "precipitation", "apparent_temperature"
]
latest = [data[feature][idx] for feature in features]

# === Compute intelligent deltas (mocked as 0 for now) ===
temp_delta = 0
humidity_delta = 0
wind_delta = 0

final_input = latest + [temp_delta, humidity_delta, wind_delta]

# === Run model prediction ===
prediction = model.predict([final_input])[0]
confidence = model.predict_proba([final_input])[0][1] if prediction == 1 else model.predict_proba([final_input])[0][0]

# === Output Results ===
print("\n🌪️ AEROCASTAI TORNADO PREDICTION 🌪️")
print(f"Location: ({lat}, {lon})")
print(f"Tornado Risk: {'✅ YES' if prediction == 1 else '❌ NO'}")
print(f"Confidence: {confidence * 100:.2f}%")
print("\n📊 Weather Data Used:")
for key, value in zip(features, latest):
    print(f" - {key.replace('_', ' ').capitalize()}: {value}")

# === 🧠 Log to SQLite Database ===
try:
    conn = sqlite3.connect("aerocastai_weather.db")
    cursor = conn.cursor()

    # Prepare values matching actual table columns
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    temperature = latest[0]
    dew_point = latest[1]
    humidity = latest[2]
    pressure = latest[3]
    wind_speed = latest[4]
    cloud_cover_mid = latest[6]
    precipitation = latest[7]
    apparent_temp = latest[8]

    # Insert into predictions table
    cursor.execute("""
        INSERT INTO predictions (
            timestamp, lat, lon, temperature_2m, dew_point_2m,
            relative_humidity_2m, surface_pressure, wind_speed_10m,
            cloud_cover_mid, precipitation, apparent_temperature,
            tornado_risk, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        lat,
        lon,
        temperature,
        dew_point,
        humidity,
        pressure,
        wind_speed,
        cloud_cover_mid,
        precipitation,
        apparent_temp,
        int(prediction),
        round(confidence * 100, 2)
    ))

    conn.commit()
    conn.close()
    print("\n✅ Prediction logged to database.")

except Exception as e:
    print("\n❌ Failed to log prediction to database:", e)
