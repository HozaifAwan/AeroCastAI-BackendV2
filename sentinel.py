import sqlite3
import requests
import pickle
import numpy as np
from datetime import datetime
from mailjet_rest import Client

# --- CONFIG ---
DB_PATH = "aerocastai_weather.db"
MODEL_PATH = "aerocast_model_ultra.pkl"  # <-- update to your actual model file
MAILJET_API_KEY = "0460478a7d78d90d7b7681a5d775e6b3"
MAILJET_API_SECRET = "e1b7f741a7f4b3979a9530ea0dff756f"
MAILJET_FROM = "aerocastai@gmail.com"

# --- Load Model ---
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

# --- Mailjet Setup ---
mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3.1')

def send_alert_email(to_email, zipcode, confidence):
    confidence_percent = f"{confidence*100:.1f}"
    data = {
        'Messages': [
            {
                "From": {"Email": MAILJET_FROM, "Name": "AeroCastAI"},
                "To": [{"Email": to_email, "Name": "AeroCastAI User"}],
                "Subject": "🚨 Tornado Risk Detected Near You",
                "TextPart": (
                    f"AeroCastAI has detected a HIGH risk of tornado activity near your location (ZIP: {zipcode}).\n\n"
                    f"AI Confidence: {confidence_percent}%\n\n"
                    "Please seek shelter immediately and monitor local weather alerts for further instructions.\n\n"
                    "Stay safe,\nAeroCastAI Team"
                ),
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(f"Email sent to {to_email}: {result.status_code} {result.json()}")

def geocode_zip(zipcode):
    resp = requests.get(f"https://api.zippopotam.us/us/{zipcode}")
    if resp.status_code == 200:
        data = resp.json()
        lat = float(data["places"][0]["latitude"])
        lon = float(data["places"][0]["longitude"])
        return lat, lon
    return None, None

def fetch_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current=temperature_2m,dew_point_2m,"
        f"relative_humidity_2m,surface_pressure,wind_speed_10m,cloud_cover,"
        f"precipitation,apparent_temperature"
    )
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()["current"]
    return None

def format_features(weather):
    # Adjust this order and count to match your model's expected input
    features = [
        weather.get("temperature_2m", 0),
        weather.get("dew_point_2m", 0),
        weather.get("relative_humidity_2m", 0),
        weather.get("surface_pressure", 0),
        weather.get("wind_speed_10m", 0),
        weather.get("cloud_cover", 0),
        weather.get("precipitation", 0),
        weather.get("apparent_temperature", 0),
        0, 0, 0, 0  # Fillers for missing features if needed
    ]
    return np.array(features).reshape(1, -1)

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email, zipcode FROM users")
    users = cursor.fetchall()

    for email, zipcode in users:
        print(f"Checking {email} ({zipcode})")
        lat, lon = geocode_zip(zipcode)
        if lat is None:
            print(f"Could not geocode ZIP {zipcode}")
            continue

        weather = fetch_weather(lat, lon)
        if not weather:
            print(f"Could not fetch weather for {lat},{lon}")
            continue

        X = format_features(weather)
        pred_prob = model.predict_proba(X)[0][1]
        pred = int(pred_prob > 0.5)  # Or use model.predict(X)[0] if that's your convention

        print(f"Prediction: {pred}, Confidence: {pred_prob:.2f}")

        if pred == 1 and pred_prob > 0.6:
            # Check for recent alert (1 hour window)
            cursor.execute(
                "SELECT timestamp FROM tornado_alerts WHERE email=? ORDER BY timestamp DESC LIMIT 1",
                (email,)
            )
            row = cursor.fetchone()
            if row:
                last_alert = datetime.fromisoformat(row[0])
                if (datetime.utcnow() - last_alert).total_seconds() < 3600:
                    print("Alert already sent recently, skipping.")
                    continue
            # Log to tornado_alerts
            cursor.execute(
                "INSERT INTO tornado_alerts (timestamp, email, lat, lon, prediction, confidence, temperature, wind_speed, humidity) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.utcnow().isoformat(),
                    email,
                    lat,
                    lon,
                    pred,
                    float(pred_prob),
                    weather["temperature_2m"],
                    weather["wind_speed_10m"],
                    weather["relative_humidity_2m"],
                ),
            )
            conn.commit()
            send_alert_email(email, zipcode, pred_prob)
        else:
            print("No tornado risk detected or confidence too low.")

    conn.close()

if __name__ == "__main__":
    main()