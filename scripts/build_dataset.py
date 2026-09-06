"""
Resolves each school's timezone locally using `timezonefinder` -- no
external API calls, no rate limits, no network dependency at all. This is
the step that actually creates the thing this project is for: a dataset
that has timezone baked in.

By default this reads the small bundled sample (10 real universities) so
you can test the whole pipeline with zero setup:

    python scripts/build_dataset.py

Once you've run fetch_schools.py with a real API key, point this at the
full dataset instead:

    python scripts/build_dataset.py --input data/schools_raw.json
"""

import argparse
import json
import os
from pathlib import Path

from timezonefinder import TimezoneFinder

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_INPUT = DATA_DIR / "schools_sample_raw.json"
# Same override as api/store.py, and for the same reason: lets the test
# suite build into a throwaway file instead of overwriting real data.
OUTPUT_PATH = Path(os.environ.get("SCHOOLS_DATA_PATH", DATA_DIR / "schools.json"))


def build(input_path: Path) -> None:
    if not input_path.exists():
        raise SystemExit(f"{input_path} not found.")

    raw = json.loads(input_path.read_text())
    tf = TimezoneFinder(in_memory=True)  # loads boundary data once, reused per lookup

    dataset = {}
    skipped = 0       # no coordinates at all -- not in the dataset
    unresolved = []   # HAD coordinates, but timezonefinder returned nothing --
                      # kept in the dataset (timezone: null) but worth a look

    for record in raw:
        school_id = str(record.get("id"))
        lat = record.get("location.lat")
        lon = record.get("location.lon")

        if lat is None or lon is None:
            skipped += 1
            continue

        timezone = tf.timezone_at(lat=lat, lng=lon)
        if timezone is None:
            unresolved.append(school_id)

        dataset[school_id] = {
            "id": school_id,
            "name": record.get("school.name"),
            "city": record.get("school.city"),
            "state": record.get("school.state"),
            "zip": record.get("school.zip"),
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,  # e.g. "America/Los_Angeles"
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2))

    print(f"Read {input_path.name}")
    print(f"Resolved timezones for {len(dataset)} schools")
    print(f"  {skipped} skipped entirely (no coordinates)")
    if unresolved:
        print(f"  {len(unresolved)} had coordinates but NO timezone resolved -- worth checking: {unresolved}")
    print(f"Saved final dataset to {OUTPUT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Raw school records to resolve (default: bundled 10-school sample)",
    )
    args = parser.parse_args()
    build(args.input)


if __name__ == "__main__":
    main()
