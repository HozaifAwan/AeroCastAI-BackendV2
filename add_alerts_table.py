import sqlite3

conn = sqlite3.connect("aerocastai_weather.db")
cursor = conn.cursor()

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
print("✅ alerts table added to aerocastai_weather.db")