"""Download a sample of recent NYC 311 service requests."""

from io import StringIO
from pathlib import Path

import pandas as pd
import requests


API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "nyc311_sample.csv"

# Select useful columns and retrieve the most recent 100 requests.
QUERY = {
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
    "$limit": 1000,
}


def extract_data() -> pd.DataFrame:
    """Download recent NYC 311 records and save them locally."""

    print("Downloading NYC 311 data...")

    response = requests.get(
        API_URL,
        params=QUERY,
        timeout=60,
    )

    response.raise_for_status()

    df = pd.read_csv(
        StringIO(response.text)
    )

    if df.empty:
        raise ValueError("The NYC 311 API returned no records.")

    for column in ["created_date", "closed_date"]:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(f"Downloaded {len(df):,} rows")
    print(f"Saved to: {OUTPUT_FILE}")
    print("\nFirst five rows:")
    print(df.head())

    return df


if __name__ == "__main__":
    extract_data()
