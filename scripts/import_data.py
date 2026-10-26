from pathlib import Path

import pandas as pd
import requests


API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
OUTPUT_FILE = Path("data/raw/nyc311_sample.csv")

PARAMS = {
    "$limit": 1000,
    "$order": "created_date DESC",
    "$select": (
        "unique_key,"
        "created_date,"
        "closed_date,"
        "agency,"
        "agency_name,"
        "complaint_type,"
        "descriptor,"
        "location_type,"
        "incident_zip,"
        "borough,"
        "status,"
        "latitude,"
        "longitude"
    ),
}


def import_data() -> None:
    """Download a sample of recent NYC 311 service requests."""

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(
        API_URL,
        params=PARAMS,
        timeout=60,
    )
    response.raise_for_status()

    records = response.json()
    dataframe = pd.DataFrame(records)

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(f"Imported {len(dataframe):,} service requests")
    print(f"Saved data to: {OUTPUT_FILE.resolve()}")
    print("\nFirst five rows:")
    print(dataframe.head())


if __name__ == "__main__":
    import_data()