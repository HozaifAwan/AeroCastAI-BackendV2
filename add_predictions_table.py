import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("aerocastai_weather.db")
cursor = conn.cursor()

# Create the predictions table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    timestamp TEXT,
    lat REAL,
    lon REAL,
    temperature_2m REAL,
    dew_point_2m REAL,
    relative_humidity_2m REAL,
    surface_pressure REAL,
    wind_speed_10m REAL,
    cloud_cover REAL,
    cloud_cover_mid REAL,
    precipitation REAL,
    apparent_temperature REAL,
    tornado_risk INTEGER,
    confidence REAL
);
""")

conn.commit()
conn.close()

print("✅ predictions table added to aerocastai_weather.db")
