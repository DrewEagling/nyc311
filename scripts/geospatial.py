"""
Extract a recent sample of NYC 311 service requests.

Source:
    NYC Open Data
    311 Service Requests from 2020 to Present

Output:
    data/raw/nyc311_sample.csv

The script:
    1. Requests recent service requests from the NYC Open Data API.
    2. Retries temporary API and connection failures.
    3. Converts date and coordinate columns.
    4. Validates the downloaded records.
    5. Saves the results as a CSV file.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

# This file is expected to be located at:
# nyc311/scripts/extract.py
#
# parents[1] therefore resolves to the main nyc311 directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "nyc311_sample.csv"
)


# ------------------------------------------------------------
# NYC Open Data API configuration
# ------------------------------------------------------------

DATASET_ID = "erm2-nwe9"

API_URL = (
    "https://data.cityofnewyork.us"
    f"/resource/{DATASET_ID}.json"
)

SAMPLE_SIZE = 1_000

REQUEST_TIMEOUT_SECONDS = 60

MAX_MANUAL_ATTEMPTS = 3


# ------------------------------------------------------------
# API query
# ------------------------------------------------------------

SELECTED_COLUMNS = (
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
)

QUERY_PARAMETERS = {
    "$select": SELECTED_COLUMNS,
    "$order": "created_date DESC",
    "$limit": SAMPLE_SIZE,
}


# ------------------------------------------------------------
# Required output columns
# ------------------------------------------------------------

REQUIRED_COLUMNS = {
    "unique_key",
    "created_date",
    "agency",
    "complaint_type",
    "borough",
    "status",
    "latitude",
    "longitude",
}


# ------------------------------------------------------------
# HTTP session
# ------------------------------------------------------------

def create_session() -> requests.Session:
    """
    Create a requests session with automatic retry handling.

    Retries are attempted for temporary rate-limit and server errors:
        429: Too Many Requests
        500: Internal Server Error
        502: Bad Gateway
        503: Service Unavailable
        504: Gateway Timeout

    Returns
    -------
    requests.Session
        Configured HTTP session.
    """

    retry_strategy = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=2,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy
    )

    session = requests.Session()

    session.mount(
        "https://",
        adapter,
    )

    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": (
                "nyc311-data-pipeline/1.0 "
                "(educational data-analysis project)"
            ),
        }
    )

    # An application token is optional for small sample requests.
    # If NYC311_APP_TOKEN exists as an environment variable,
    # it will be included automatically.
    app_token = os.getenv("NYC311_APP_TOKEN")

    if app_token:
        session.headers.update(
            {
                "X-App-Token": app_token,
            }
        )

        print("Using NYC Open Data application token.")
    else:
        print(
            "No NYC Open Data application token detected. "
            "Continuing with public API access."
        )

    return session


# ------------------------------------------------------------
# API download
# ------------------------------------------------------------

def request_records(
    session: requests.Session,
) -> list[dict[str, Any]]:
    """
    Request recent NYC 311 records from the API.

    Parameters
    ----------
    session
        Configured requests session.

    Returns
    -------
    list of dict
        API records returned as JSON objects.

    Raises
    ------
    RuntimeError
        If all download attempts fail.
    ValueError
        If the API response is not a JSON list.
    """

    last_error: Exception | None = None

    for attempt in range(
        1,
        MAX_MANUAL_ATTEMPTS + 1,
    ):
        try:
            print(
                f"API request attempt "
                f"{attempt}/{MAX_MANUAL_ATTEMPTS}..."
            )

            response = session.get(
                API_URL,
                params=QUERY_PARAMETERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                retry_after = response.headers.get(
                    "Retry-After",
                    "10",
                )

                try:
                    wait_seconds = max(
                        int(retry_after),
                        1,
                    )
                except ValueError:
                    wait_seconds = 10

                print(
                    "The API rate limit was reached. "
                    f"Waiting {wait_seconds} seconds."
                )

                time.sleep(wait_seconds)
                continue

            response.raise_for_status()

            try:
                records = response.json()
            except requests.JSONDecodeError as error:
                response_preview = response.text[:500]

                raise ValueError(
                    "The NYC API did not return valid JSON.\n"
                    f"Response preview:\n{response_preview}"
                ) from error

            if not isinstance(records, list):
                raise ValueError(
                    "Unexpected NYC API response format. "
                    "A list of service-request records "
                    "was expected."
                )

            if not records:
                raise ValueError(
                    "The NYC API returned no service requests."
                )

            return records

        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError,
            ValueError,
        ) as error:
            last_error = error

            print(
                f"Attempt {attempt} failed: {error}"
            )

            if attempt < MAX_MANUAL_ATTEMPTS:
                wait_seconds = attempt * 5

                print(
                    f"Waiting {wait_seconds} seconds "
                    "before trying again..."
                )

                time.sleep(wait_seconds)

    raise RuntimeError(
        "The NYC 311 sample could not be downloaded "
        f"after {MAX_MANUAL_ATTEMPTS} attempts."
    ) from last_error


# ------------------------------------------------------------
# Data preparation
# ------------------------------------------------------------

def prepare_dataframe(
    records: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Convert downloaded JSON records into a cleaned DataFrame.

    Parameters
    ----------
    records
        JSON records returned by the API.

    Returns
    -------
    pandas.DataFrame
        Prepared NYC 311 sample data.
    """

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError(
            "The downloaded NYC 311 dataset is empty."
        )

    missing_columns = REQUIRED_COLUMNS.difference(
        df.columns
    )

    if missing_columns:
        raise ValueError(
            "The API response is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # Convert date columns from text into pandas datetimes.
    for column in [
        "created_date",
        "closed_date",
    ]:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

  