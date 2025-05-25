import sqlite3

conn = sqlite3.connect("aerocastai_weather.db")
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS user_logs")
cursor.execute("""
CREATE TABLE user_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    latitude REAL,
    longitude REAL,
    temperature REAL,
    dew_point REAL,
    humidity REAL,
    pressure REAL,
    wind_speed REAL,
    cloud_cover REAL,
    precipitation REAL,
    apparent_temp REAL,
    prediction INTEGER,
    confidence REAL,
    place TEXT
)
""")
conn.commit()
conn.close()