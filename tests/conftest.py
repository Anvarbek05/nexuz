"""Settings shared by all tests. This file runs before the tests import the app."""
import os
import tempfile

# Tests must NEVER touch a real database: use a throw-away SQLite file.
_folder = tempfile.mkdtemp(prefix="nexuz-test-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_folder, "test.db").replace("\\", "/")

import pytest  # noqa: E402

from app import config, db  # noqa: E402
from app.services import limits  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    db.reset_for_tests()
    limits.speed.clear()
    # The older tests make many requests as one guest, so by default guests have no daily limit here.
    # Tests about limits set their own numbers.
    monkeypatch.setitem(config.PLANS["guest"], "per_day", None)
    yield
