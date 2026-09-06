# University Timezone API (testable core)

Given a US university, returns its location and timezone. This is the
core slice only: location + timezone lookup, read-only. (Admin edits,
free hosting, and the "current local time" feature are later additions
-- see the project roadmap.)

## Test it right now -- no API key needed

A small bundled sample (`data/schools_sample_raw.json`, 10 real
universities picked to span different US timezones -- including Arizona
and Hawaii, which don't observe DST) lets you run the whole pipeline
immediately.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows (PowerShell): .venv\Scripts\Activate.ps1
                                  # Windows (cmd.exe):    .venv\Scripts\activate.bat
python -m pip install -r requirements.txt

python scripts/build_dataset.py  # reads the bundled sample by default
python -m uvicorn api.main:app --reload
```

`python -m pip` / `python -m uvicorn` (instead of bare `pip` / `uvicorn`)
sidesteps the most common Windows headache: a command that installs fine
but isn't on PATH afterwards. If even `python` isn't recognized, try `py`
in its place (the Windows launcher) -- e.g. `py -m uvicorn api.main:app --reload`.

Open **http://127.0.0.1:8000/docs** -- an interactive page where you can
try every endpoint by clicking, no separate HTTP client needed.

Or from another terminal:

```bash
curl "http://127.0.0.1:8000/"
curl "http://127.0.0.1:8000/schools?state=AZ"
curl "http://127.0.0.1:8000/schools/sample-02"
curl "http://127.0.0.1:8000/schools/sample-02/timezone"
curl "http://127.0.0.1:8000/timezone?lat=64.8569&lng=-147.8028"
```

Note: `GET /schools` returns a paginated envelope, not a bare array --
`{"total": ..., "limit": ..., "offset": ..., "results": [...]}` -- so the
list itself is under `results`. That's so an unfiltered call against the
real (thousands-of-rows) dataset later doesn't dump everything in one
response; use `?limit=` and `?offset=` to page through matches.

### What you should see

| School | State | Expected timezone |
|---|---|---|
| Stanford University | CA | `America/Los_Angeles` |
| University of Arizona | AZ | `America/Phoenix` (no DST) |
| University of Michigan-Ann Arbor | MI | `America/Detroit` |
| University of Hawaii at Manoa | HI | `Pacific/Honolulu` (no DST) |
| University of Alaska Fairbanks | AK | `America/Anchorage` |
| University of Texas at Austin | TX | `America/Chicago` |
| Purdue University-Main Campus | IN | `America/Indiana/Indianapolis` |
| Colorado State University-Fort Collins | CO | `America/Denver` |
| University of Florida | FL | `America/New_York` |
| University of California-Los Angeles | CA | `America/Los_Angeles` |

Arizona and Colorado are both "Mountain," but only one observes DST --
that contrast existing in the same 10-row sample is the whole reason
this project is worth building instead of developers guessing.

## A note on data quality at real scale

With 10 hand-picked schools, every coordinate resolves cleanly. With the
full College Scorecard dataset, two things can legitimately happen that
this sample won't show you: a record with no coordinates at all (skipped
entirely, never appears in `schools.json`), and a record that HAS
coordinates but where `timezonefinder` can't resolve them to a zone
(kept, but with `"timezone": null`). `build_dataset.py` now prints both
counts separately -- if you ever see a non-zero "unresolved" count after
pulling real data, that's a short, specific list of school IDs worth
spot-checking, not a silent gap.

## Once this works: pull the real, full dataset

```bash
cp .env.example .env
# edit .env: add a free key from https://api.data.gov/signup/

python scripts/fetch_schools.py            # -> data/schools_raw.json (real US schools)
python scripts/build_dataset.py --input data/schools_raw.json
```

Restart `python -m uvicorn api.main:app --reload` and the same three
endpoints now serve the real dataset instead of the 10-school sample.

## Endpoints

- `GET /` -- health/info: status, how many schools are currently indexed,
  and a data source attribution
- `GET /schools?state=CA&q=stanford&limit=50&offset=0` -- list/search,
  paginated (`limit` max 500, default 50)
- `GET /schools/{id}` -- one school, including its timezone
- `GET /schools/{id}/timezone` -- just that school's timezone, for callers
  who don't need the rest of the record
- `GET /timezone?lat=&lng=` -- raw coordinate lookup, works for any point
  on Earth, not tied to a school ID at all

All of the above allow requests from any origin (CORS is open for GET) --
there's no login on this API and nothing cross-origin could misuse, so
any frontend can call it directly from the browser without a proxy.

### Finding a school's ID in the first place

Nobody starts out knowing a federal ID number. `/schools/{id}` and
`/schools/{id}/timezone` are for when you already have one -- search is
how you get it:

```bash
curl "http://127.0.0.1:8000/schools?q=arizona"
# -> {"total": 1, ..., "results": [{"id": "sample-02", "name": "University of Arizona", ...}]}

curl "http://127.0.0.1:8000/schools/sample-02/timezone"
# -> {"id": "sample-02", "timezone": "America/Phoenix"}
```

Search once to find the ID, then use that ID directly for repeat
lookups. (On the real dataset, that first call would return the
school's actual IPEDS UnitID -- e.g. `110635` for Berkeley -- instead of
a `sample-##` placeholder.)

## Automated tests

Manually pasting URLs proves the happy path works; it doesn't cover case
sensitivity, empty results, bad input, or pagination edges. Those are
now a real test suite instead:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

`tests/conftest.py` rebuilds `data/schools.json` from the bundled sample
before the run, so tests are reproducible regardless of what you were
poking at manually beforehand. Run this after any change, especially
once you start on the search-matching improvements or the real dataset.

## Deliberately not in this version

- **No admin write endpoints** (add/edit/delete a school). That's a
  separate, security-sensitive piece -- see the project roadmap for why
  it's kept apart and reviewed separately before it touches any real
  credential.
- **No "current local time" feature yet** -- just the timezone name for
  now, current time comes next once this core is confirmed working.
- **No free-hosting deployment** (CDN, edge function, GitHub Actions).
  Everything above runs on your own machine; where it eventually lives
  is a separate decision that doesn't block testing the functionality.
