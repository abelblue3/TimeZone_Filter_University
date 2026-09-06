from typing import Optional

from pydantic import BaseModel


class School(BaseModel):
    id: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    latitude: float
    longitude: float
    timezone: Optional[str] = None  # e.g. "America/Los_Angeles" -- null means
    # this school HAS coordinates but they didn't resolve to a timezone (see
    # build_dataset.py's "unresolved" count). Missing coordinates entirely
    # means the school was skipped and won't appear here at all.


class SchoolList(BaseModel):
    total: int      # total matches, before limit/offset are applied
    limit: int
    offset: int
    results: list[School]
