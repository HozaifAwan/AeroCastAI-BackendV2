import pandas as pd
import sqlite3
import glob

# === Step 1: Load Weather CSV ===
print("Loading weather data...")
weather_df = pd.read_csv("weather_full_multilocation.csv")
weather_df["time"] = pd.to_datetime(weather_df["time"], errors="coerce")
weather_df = weather_df.dropna(subset=["time", "lat", "lon"])
weather_df = weather_df.rename(columns={"time": "date_time", "latitude": "lat", "longitude": "lon"})

# === Step 2: Load and Clean NOAA Tornado Files ===
print("Loading NOAA tornado files...")
tornado_files = sorted(glob.glob("tornado_data/StormEvents_details-ftp_v1.0_d*.csv"))
tornado_records = []

for file in tornado_files:
    try:
        print(f"Processing {file}...")
        df = pd.read_csv(file, low_memory=False)
        df.columns = [col.upper() for col in df.columns]  # Normalize headers

        if "EVENT_TYPE" in df.columns:
            df = df[df["EVENT_TYPE"].str.lower() == "tornado"]
        else:
            print(f"⚠️ Skipping {file} — EVENT_TYPE column missing.")
            continue

        if not {"BEGIN_DATE_TIME", "BEGIN_LAT", "BEGIN_LON"}.issubset(df.columns):
            print(f"⚠️ Skipping {file} — Required columns missing.")
            continue

        df = df.dropna(subset=["BEGIN_DATE_TIME", "BEGIN_LAT", "BEGIN_LON"])
        df["BEGIN_DATE_TIME"] = pd.to_datetime(df["BEGIN_DATE_TIME"], errors="coerce")
        df = df.dropna(subset=["BEGIN_DATE_TIME", "BEGIN_LAT", "BEGIN_LON"])

        if df.empty:
            print(f"⚠️ Skipping {file} — no valid tornado rows.")
            continue

        tornado_records.append(df)

    except Exception as e:
        print(f"⚠️ Error processing {file}: {e}")

# === Step 3: Save Tornado Data to SQLite ===
if tornado_records:
    tornado_df = pd.concat(tornado_records, ignore_index=True)
    tornado_df = tornado_df.rename(columns={
        "BEGIN_DATE_TIME": "date_time",
        "BEGIN_LAT": "lat",
        "BEGIN_LON": "lon"
    })
else:
    print("⚠️ No tornado records were processed. Database will only contain weather data.")
    tornado_df = pd.DataFrame(columns=["date_time", "lat", "lon"])

# === Step 4: Save to SQLite Database ===
conn = sqlite3.connect("aerocastai_weather.db")

print("Saving to SQLite: weather table")
weather_df.to_sql("weather", conn, if_exists="replace", index=False)

print("Saving to SQLite: tornado_events table")
tornado_df.to_sql("tornado_events", conn, if_exists="replace", index=False)

conn.close()
print("✅ Database build complete: aerocastai_weather.db")
