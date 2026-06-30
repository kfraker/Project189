"""
Shared fixtures for all test modules.

Strategy: set app.config['DB_PATH'] to a fresh temp file before each test,
then call init_db() so tables exist. No monkeypatching needed — get_db()
reads from app.config at call time, so the override takes effect for every
route handler called through the test client.
"""
import pytest
import app as app_module
from app import app as flask_app


@pytest.fixture()
def test_db(tmp_path):
    """Isolated SQLite database for one test."""
    db_file = tmp_path / "test_weights.db"
    flask_app.config['DB_PATH'] = str(db_file)
    app_module.init_db()
    yield str(db_file)
    flask_app.config['DB_PATH'] = app_module.DB_PATH  # restore after test


@pytest.fixture()
def client(test_db):
    """Flask test client wired to the isolated test DB."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ── Seed helpers ─────────────────────────────────────────────────────────────

def seed_weight(client, entry_date: str, weight_lbs: float, overwrite: bool = False):
    return client.post(
        "/api/weight",
        json={"date": entry_date, "weight_lbs": weight_lbs, "overwrite": overwrite},
        content_type="application/json",
    )


def seed_setting(client, key: str, value_lbs: float, overwrite: bool = False):
    return client.post(
        "/api/setting",
        json={"key": key, "value_lbs": value_lbs, "overwrite": overwrite},
        content_type="application/json",
    )
