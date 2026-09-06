"""
Pulls raw school records (name, city, state, zip, latitude, longitude) from
the College Scorecard API and saves them locally.

You do NOT need to run this to test the project -- a small bundled sample
(data/schools_sample_raw.json, 10 real universities) already lets you run
the full pipeline with zero setup. Come back to this script once you're
ready to pull the real, full US dataset.

Get a free API key first: https://api.data.gov/signup/
Then either export it as an env var or put it in a .env file:
    COLLEGE_SCORECARD_API_KEY=your_key_here

Usage:
    python scripts/fetch_schools.py
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
API_KEY = os.environ.get("COLLEGE_SCORECARD_API_KEY")

# NOTE: the College Scorecard API occasionally renames/adjusts fields.
# Double check these against the current docs if a field comes back empty:
# https://collegescorecard.ed.gov/data/api-documentation/
FIELDS = ",".join(
    [
        "id",
        "school.name",
        "school.city",
        "school.state",
        "school.zip",
        "location.lat",
        "location.lon",
    ]
)

PER_PAGE = 100  # API max per request
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "schools_raw.json"


def fetch_all_schools() -> list[dict]:
    if not API_KEY:
        raise SystemExit(
            "Missing COLLEGE_SCORECARD_API_KEY. Copy .env.example to .env "
            "and fill in a key from https://api.data.gov/signup/\n"
            "(Or skip this entirely and test with data/schools_sample_raw.json instead.)"
        )

    all_results: list[dict] = []
    page = 0

    while True:
        params = {
            "api_key": API_KEY,
            "fields": FIELDS,
            "per_page": PER_PAGE,
            "page": page,
        }
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        results = payload.get("results", [])
        if not results:
            break

        all_results.extend(results)
        total = payload.get("metadata", {}).get("total", 0)
        print(f"  page {page}: got {len(results)} (total so far: {len(all_results)}/{total})")

        page += 1
        if len(all_results) >= total:
            break

        time.sleep(0.2)  # be polite to the API

    return all_results


def main() -> None:
    print("Fetching schools from College Scorecard API...")
    schools = fetch_all_schools()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(schools, indent=2))
    print(f"Saved {len(schools)} raw school records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
