"""
The API: four read-only endpoints over data/schools.json, plus a root
health/info check. No auth, no writes -- that's intentionally out of
scope for this version (see the project roadmap for where that comes
back in later).

Run it with:
    python -m uvicorn api.main:app --reload

(the -m form avoids a common Windows issue where a pip-installed command
isn't on PATH even though the package installed fine)

Then open http://127.0.0.1:8000/docs for an interactive UI to try every
endpoint from the browser -- FastAPI builds that for free from the type
hints below, no separate client needed.

Endpoints:
    GET /                               health/info -- status, dataset
                                         size, and data source attribution
    GET /schools                        list/search (?state=CA&q=stanford), paginated
    GET /schools/{school_id}            one school, including its timezone
    GET /schools/{school_id}/timezone   just that school's timezone -- a
                                         thin convenience slice of the line
                                         above, for callers who don't need
                                         the rest of the record (city, zip,
                                         lat/lon)
    GET /timezone?lat=&lng=             raw lat/lon -> timezone lookup
                                         (works for ANY coordinate, not
                                         tied to a school ID at all)

Note on /schools: the real College Scorecard dataset has thousands of
rows, not 10 -- an unfiltered call with no limit would dump all of them
in one response. So this returns a paginated envelope, not a bare array:
    {"total": <matches before paging>, "limit": ..., "offset": ..., "results": [...]}

CORS is wide open (any origin, GET only). Every endpoint here is public
and unauthenticated, so there's no session or credential a cross-origin
browser request could misuse -- if that changes (the write path in the
roadmap will need auth), give that its own, narrower CORS policy rather
than loosening this one.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from timezonefinder import TimezoneFinder

from . import store
from .models import School, SchoolList

app = FastAPI(
    title="University Timezone API",
    description="Look up US school location and timezone by name, state, or coordinates.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

tf = TimezoneFinder(in_memory=True)


@app.get("/")
def health():
    """
    Not "health" in the load-balancer sense -- there's no database or
    network dependency to check, so this can't detect much beyond "the
    process is up." It exists so a browser hitting the bare URL, or a
    script doing a quick sanity check before calling the real endpoints,
    gets something informative back instead of FastAPI's default 404.
    """
    return {
        "name": app.title,
        "version": app.version,
        "status": "ok",
        "schools_indexed": len(store.list_schools()),
        "data_sources": [
            "U.S. Dept. of Education College Scorecard -- school location data",
            "timezone-boundary-builder (OpenStreetMap + IANA tz database) -- timezone resolution",
        ],
    }


@app.get("/schools", response_model=SchoolList)
def list_schools(
    state: str | None = Query(default=None, description="Two-letter state code, e.g. CA"),
    q: str | None = Query(default=None, description="Substring match on school name"),
    limit: int = Query(default=50, ge=1, le=500, description="Max results per page"),
    offset: int = Query(default=0, ge=0, description="Number of matches to skip"),
):
    matches = store.list_schools(state=state, q=q)
    page = matches[offset : offset + limit]
    return {"total": len(matches), "limit": limit, "offset": offset, "results": page}


@app.get("/schools/{school_id}", response_model=School)
def get_school(school_id: str):
    school = store.get_school(school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@app.get("/schools/{school_id}/timezone")
def get_school_timezone(school_id: str):
    """
    Same lookup as GET /schools/{school_id}, sliced down to just the
    timezone -- for a caller who already has an ID and doesn't need the
    rest of the record. Reuses store.get_school() rather than its own
    logic, so there's one source of truth for "does this school exist."
    """
    school = store.get_school(school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    # school["timezone"] can legitimately be null (coordinates present but
    # unresolved -- see build_dataset.py) without that being a 404: the
    # school exists, it just doesn't have a resolved zone.
    return {"id": school["id"], "timezone": school["timezone"]}


@app.get("/timezone")
def lookup_timezone(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    """Direct coordinate -> timezone lookup, independent of the school dataset."""
    timezone = tf.timezone_at(lat=lat, lng=lng)
    if timezone is None:
        raise HTTPException(status_code=404, detail="No timezone found for these coordinates")
    return {"latitude": lat, "longitude": lng, "timezone": timezone}
