import sqlite3

conn = sqlite3.connect("aerocastai_weather.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zipcode TEXT NOT NULL,
    lat REAL,
    lon REAL,
    email TEXT NOT NULL,
    subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()
conn.close()
print("✅ users table added to aerocastai_weather.db")