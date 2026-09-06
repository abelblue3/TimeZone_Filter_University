"""
Encodes the "expected outcomes" table from the README as real, automated
checks, plus the edge cases that table didn't cover: case sensitivity,
empty results, combined filters, pagination, and bad/boundary input to
/timezone. Run with:

    pytest

from the project root (needs `pip install -r requirements-dev.txt` first).
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET / -- root health/info check
# ---------------------------------------------------------------------------

def test_root_reports_ok_status_and_school_count():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["schools_indexed"] == 10
    assert body["name"] == "University Timezone API"
    assert "College Scorecard" in body["data_sources"][0]


def test_cors_allows_any_origin_on_a_normal_get():
    # A "simple" cross-origin GET (no preflight needed) should come back
    # with the wildcard CORS header -- proves the middleware is actually
    # wired up, not just present in the import list.
    resp = client.get("/schools", headers={"Origin": "https://example.com"})
    assert resp.headers.get("access-control-allow-origin") == "*"


def test_cors_preflight_allows_get():
    # A real browser sends this OPTIONS request before a cross-origin GET
    # whenever the request has custom headers -- confirms GET is allowed
    # from any origin.
    resp = client.options(
        "/schools",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"


# ---------------------------------------------------------------------------
# GET /schools -- happy paths from the README table
# ---------------------------------------------------------------------------

def test_list_all_schools_returns_all_ten():
    resp = client.get("/schools")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 10
    assert len(body["results"]) == 10


def test_filter_by_state_arizona():
    resp = client.get("/schools", params={"state": "AZ"})
    body = resp.json()
    assert body["total"] == 1
    assert body["results"][0]["name"] == "University of Arizona"
    assert body["results"][0]["timezone"] == "America/Phoenix"


def test_filter_by_state_hawaii():
    resp = client.get("/schools", params={"state": "HI"})
    body = resp.json()
    assert body["total"] == 1
    assert body["results"][0]["timezone"] == "Pacific/Honolulu"


def test_search_substring_matches_seven():
    resp = client.get("/schools", params={"q": "university of"})
    assert resp.json()["total"] == 7


# ---------------------------------------------------------------------------
# Edge cases the README table didn't cover
# ---------------------------------------------------------------------------

def test_state_filter_is_case_insensitive():
    upper = client.get("/schools", params={"state": "AZ"}).json()
    lower = client.get("/schools", params={"state": "az"}).json()
    assert upper["results"] == lower["results"]


def test_no_matches_returns_empty_list_not_an_error():
    resp = client.get("/schools", params={"state": "ZZ"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["results"] == []


def test_combined_state_and_query_filters():
    # Both Stanford and UCLA are in CA -- q= should narrow it to just Stanford
    resp = client.get("/schools", params={"state": "CA", "q": "stanford"})
    body = resp.json()
    assert body["total"] == 1
    assert body["results"][0]["name"] == "Stanford University"


def test_pagination_limit_caps_page_size_but_not_total():
    resp = client.get("/schools", params={"limit": 3})
    body = resp.json()
    assert body["total"] == 10       # total reflects ALL matches
    assert len(body["results"]) == 3  # but this page only has 3


def test_pagination_offset_returns_a_different_page():
    first_page = client.get("/schools", params={"limit": 3, "offset": 0}).json()
    second_page = client.get("/schools", params={"limit": 3, "offset": 3}).json()
    first_ids = {s["id"] for s in first_page["results"]}
    second_ids = {s["id"] for s in second_page["results"]}
    assert first_ids.isdisjoint(second_ids)


# ---------------------------------------------------------------------------
# GET /schools/{id}
# ---------------------------------------------------------------------------

def test_get_school_by_id():
    resp = client.get("/schools/sample-02")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "University of Arizona"
    assert body["timezone"] == "America/Phoenix"


def test_get_unknown_school_id_returns_404():
    resp = client.get("/schools/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "School not found"


# ---------------------------------------------------------------------------
# GET /schools/{id}/timezone -- the convenience slice
# ---------------------------------------------------------------------------

def test_school_timezone_shortcut_matches_full_record():
    full = client.get("/schools/sample-02").json()
    shortcut = client.get("/schools/sample-02/timezone").json()
    assert shortcut["timezone"] == full["timezone"] == "America/Phoenix"
    assert shortcut["id"] == "sample-02"


def test_school_timezone_shortcut_unknown_id_returns_404():
    resp = client.get("/schools/does-not-exist/timezone")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "School not found"


# ---------------------------------------------------------------------------
# GET /timezone
# ---------------------------------------------------------------------------

def test_timezone_lookup_at_a_known_school():
    # University of Alaska Fairbanks' own coordinates
    resp = client.get("/timezone", params={"lat": 64.8569, "lng": -147.8028})
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "America/Anchorage"


def test_timezone_lookup_works_for_points_not_in_the_dataset():
    # Miami isn't one of the 10 seeded schools -- proves this endpoint
    # resolves ANY coordinate, not just a lookup against seeded schools.
    resp = client.get("/timezone", params={"lat": 25.7617, "lng": -80.1918})
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "America/New_York"


def test_timezone_rejects_out_of_range_latitude():
    resp = client.get("/timezone", params={"lat": 999, "lng": 0})
    assert resp.status_code == 422  # validation error, not a 500 or a guess


def test_timezone_rejects_missing_params():
    resp = client.get("/timezone")
    assert resp.status_code == 422


def test_timezone_rejects_non_numeric_input():
    resp = client.get("/timezone", params={"lat": "not-a-number", "lng": 0})
    assert resp.status_code == 422


def test_timezone_accepts_boundary_coordinates():
    # lat=90/lng=180 are the extreme legal values -- they must pass
    # validation even if the geographic answer at the poles is "no zone"
    resp = client.get("/timezone", params={"lat": 90, "lng": 180})
    assert resp.status_code != 422
