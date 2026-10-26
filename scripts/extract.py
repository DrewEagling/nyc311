from pathlib import Path

import pandas as pd


API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "nyc311_recent.csv"

# Select useful columns and retrieve the most recent 100 requests.
query = {
    "$select": (
        "unique_key,"
        "created_date,"
        "closed_date,"
        "agency,"
        "agency_name,"
        "complaint_type,"
        "descriptor,"
        "status,"
        "borough,"
        "incident_zip,"
        "latitude,"
        "longitude"
    ),
    "$order": "created_date DESC",
    "$limit": 100,
}

print("Downloading NYC 311 data...")

df = pd.read_csv(API_URL, params=query)

# Convert date columns from text to pandas datetimes.
df["created_date"] = pd.to_datetime(
    df["created_date"],
    errors="coerce"
)

df["closed_date"] = pd.to_datetime(
    df["closed_date"],
    errors="coerce"
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"Downloaded {len(df):,} rows")
print(f"Saved to: {OUTPUT_FILE}")
print()
print(df.head())