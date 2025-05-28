from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import joblib
import numpy as np
import requests
from fastapi.middleware.cors import CORSMiddleware
from mailjet_rest import Client
import os

app = FastAPI()

# Mailjet setup
api_key = '0460478a7d78d90d7b7681a5d775e6b3'
api_secret = 'e1b7f741a7f4b3979a9530ea0dff756f'
mailjet = Client(auth=(api_key, api_secret), version='v3.1')

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Model download and load ===
MODEL_PATH = "aerocast_model_ultra.pkl"
MODEL_URL = "https://drive.google.com/uc?export=download&id=1ZrESyGIr0sTd531Hp9ZxB7l4mkU5-jG9"

def download_model():
    print("Model file not found. Downloading...")
    response = requests.get(MODEL_URL)
    if response.status_code == 200 and response.content.startswith(b'\x80'):  # joblib file starts with 0x80
        with open(MODEL_PATH, "wb") as f:
            f.write(response.content)
        print("✅ Model downloaded successfully.")
    else:
        raise RuntimeError("❌ Downloaded content is not a valid .pkl file — probably an HTML page.")

if not os.path.exists(MODEL_PATH):
    download_model()

model = joblib.load(MODEL_PATH)

# === Schemas ===
class Location(BaseModel):
    latitude: float
    longitude: float

class SubscribeRequest(BaseModel):
    zipcode: str
    email: str

class EmailRequest(BaseModel):
    email: str

@app.get("/")
def root():
    return {"status": "AeroCastAI backend is live."}

@app.post("/predict")
def predict(location: Location):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={location.latitude}&longitude={location.longitude}&current=temperature_2m,dew_point_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,cloud_cover,precipitation,apparent_temperature"
        response = requests.get(url)
        weather_data = response.json()["current"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather fetch failed: {e}")

    try:
        features = [
            weather_data["temperature_2m"],
            weather_data["dew_point_2m"],
            weather_data["relative_humidity_2m"],
            weather_data["surface_pressure"],
            weather_data["wind_speed_10m"],
            weather_data["cloud_cover"],
            weather_data["precipitation"],
            weather_data["apparent_temperature"],
            location.latitude,
            location.longitude,
            location.latitude * location.longitude,
            (weather_data["temperature_2m"] + weather_data["apparent_temperature"]) / 2
        ]
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Missing weather field: {e}")

    try:
        prediction = int(model.predict([features])[0])
        confidence = float(np.max(model.predict_proba([features])) * 100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    try:
        geocode_url = f"https://nominatim.openstreetmap.org/reverse?lat={location.latitude}&lon={location.longitude}&format=json"
        geocode_resp = requests.get(geocode_url, headers={"User-Agent": "AeroCastAI/1.0"})
        address = geocode_resp.json().get("address", {})
        city = address.get("city") or address.get("town") or address.get("village") or ""
        state = address.get("state") or ""
        country = address.get("country") or ""
        location_name = ", ".join(filter(None, [city, state, country]))
    except Exception as e:
        location_name = ""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect("aerocastai_weather.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_logs (
                timestamp, latitude, longitude, temperature, dew_point, humidity, pressure,
                wind_speed, cloud_cover, precipitation, apparent_temp, prediction, confidence, place
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp, location.latitude, location.longitude,
                weather_data["temperature_2m"], weather_data["dew_point_2m"], weather_data["relative_humidity_2m"],
                weather_data["surface_pressure"], weather_data["wind_speed_10m"], weather_data["cloud_cover"],
                weather_data["precipitation"], weather_data["apparent_temperature"],
                prediction, confidence, location_name
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB insert error: {e}")

    return {
        "timestamp": timestamp,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "temperature_2m": weather_data["temperature_2m"],
        "dew_point_2m": weather_data["dew_point_2m"],
        "relative_humidity_2m": weather_data["relative_humidity_2m"],
        "surface_pressure": weather_data["surface_pressure"],
        "wind_speed_10m": weather_data["wind_speed_10m"],
        "cloud_cover": weather_data["cloud_cover"],
        "precipitation": weather_data["precipitation"],
        "apparent_temperature": weather_data["apparent_temperature"],
        "prediction": prediction,
        "confidence": round(confidence, 2),
        "location_name": location_name,
    }

@app.post("/test-email")
async def test_email_endpoint(req: EmailRequest):
    send_email(req.email)
    return {"message": f"Test email sent to {req.email}"}

@app.post("/subscribe")
async def subscribe(req: SubscribeRequest):
    conn = sqlite3.connect("aerocastai_weather.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (zipcode, email) VALUES (?, ?)", (req.zipcode, req.email))
    conn.commit()
    conn.close()
    send_email(req.email)
    return {"message": "Subscribed!"}

def send_email(to_email):
    data = {
      'Messages': [
        {
          "From": {
            "Email": "aerocastai@gmail.com",
            "Name": "AeroCastAI"
          },
          "To": [
            {
              "Email": to_email,
              "Name": "AeroCastAI User"
            }
          ],
          "Subject": "AeroCastAI Tornado Alert Subscription",
          "TextPart": "You've now subscribed to AeroCastAI. We will monitor your zipcode 24/7 and let you know if you are in danger of a tornado attack."
        }
      ]
    }
    mailjet.send.create(data=data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

