"""
Shared fixtures for all test modules.

Strategy: set app.config['DB_PATH'] to a fresh temp file before each test,
then call init_db() so tables exist. No monkeypatching needed — get_db()
reads from app.config at call time, so the override takes effect for every
route handler called through the test client.
"""
import sqlite3

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
    """Flask test client wired to the isolated test DB, pre-authenticated as user 1.

    Deliberately not opened via `with flask_app.test_client() as c:` — that
    form preserves the request context after each response, which corrupts
    Werkzeug's context stack when two such clients (see `other_client`) make
    interleaved requests within the same test.
    """
    flask_app.config["TESTING"] = True
    c = flask_app.test_client()
    with c.session_transaction() as sess:
        sess['user_id'] = 1
    yield c


@pytest.fixture()
def other_client(test_db):
    """A second authenticated client (user 2) sharing the same test_db as `client`."""
    flask_app.config["TESTING"] = True
    c = flask_app.test_client()
    conn = sqlite3.connect(test_db)
    conn.execute("INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (2, 'user2', '')")
    conn.commit()
    conn.close()
    with c.session_transaction() as sess:
        sess['user_id'] = 2
    yield c


@pytest.fixture()
def unauthenticated_client(test_db):
    """A client with no session at all, for testing the login-required gate."""
    flask_app.config["TESTING"] = True
    yield flask_app.test_client()


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
