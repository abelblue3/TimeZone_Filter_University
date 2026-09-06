"""
Read-only access to data/schools.json.

This is deliberately just a JSON file read behind one small module -- there's
no write path in this version at all. (Admin add/edit/delete, and swapping
this for a real database, are later, separate additions -- not needed to
prove the core idea: given a university, what's its timezone.)
"""

import json
import os
from pathlib import Path
from typing import Optional

_DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "schools.json"
# Overridable so the test suite can point at a throwaway file instead of
# this one -- otherwise running tests would overwrite real, pulled data.
DATA_PATH = Path(os.environ.get("SCHOOLS_DATA_PATH", _DEFAULT_DATA_PATH))


def _load() -> dict:
    if not DATA_PATH.exists():
        return {}
    return json.loads(DATA_PATH.read_text())


def list_schools(state: Optional[str] = None, q: Optional[str] = None) -> list[dict]:
    data = _load()
    results = list(data.values())

    if state:
        results = [s for s in results if (s.get("state") or "").lower() == state.lower()]
    if q:
        q_lower = q.lower()
        results = [s for s in results if q_lower in (s.get("name") or "").lower()]

    return results


def get_school(school_id: str) -> Optional[dict]:
    return _load().get(school_id)
