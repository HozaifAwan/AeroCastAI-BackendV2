import sqlite3

conn = sqlite3.connect("aerocastai_weather.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zipcode TEXT NOT NULL,
    lat REAL,
    lon REAL,
    phone TEXT,
    email TEXT,
    subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    alert_time TEXT DEFAULT CURRENT_TIMESTAMP,
    risk_level INTEGER,
    message TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
""")

conn.commit()
conn.close()
print("✅ users and alerts tables added to aerocastai_weather.db")