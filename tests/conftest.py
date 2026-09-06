"""
Rebuilds an ISOLATED copy of schools.json from the bundled 10-school
sample before the test session runs, so tests always exercise a known,
reproducible dataset -- without ever touching the real data/schools.json
the live server (and your real, pulled-from-College-Scorecard data) uses.

The env var must be set before `api.main` / `api.store` get imported
anywhere, since they read it once at module load time -- that's why this
happens at module level here, above the `scripts.build_dataset` import,
rather than inside the fixture function.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_TEST_DATA_PATH = Path(tempfile.gettempdir()) / "university-timezone-api-test-schools.json"
os.environ["SCHOOLS_DATA_PATH"] = str(_TEST_DATA_PATH)

from scripts.build_dataset import DEFAULT_INPUT, build  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def build_sample_dataset():
    build(DEFAULT_INPUT)
    yield
    _TEST_DATA_PATH.unlink(missing_ok=True)
