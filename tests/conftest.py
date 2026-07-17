"""
Shared fixtures for all test modules.

Strategy: tests run against the same Neon Postgres database as production,
but inside an isolated "test" schema (via app.config['DB_SCHEMA']) that's
truncated before every test. get_db() reads DB_SCHEMA from app.config at
call time, so the override takes effect for every route handler called
through the test client.
"""
import psycopg
from psycopg.rows import dict_row

import pytest
import app as app_module
from app import app as flask_app
from db_migrations import run_migrations

TEST_SCHEMA = "test"

_TABLES = ("workout_day_notes", "workouts", "preferences", "settings", "weights", "users")


def connect(schema=TEST_SCHEMA):
    """Open a direct connection scoped to the test schema, for setup/verification."""
    conn = psycopg.connect(app_module.DATABASE_URL, row_factory=dict_row)
    conn.execute(f"SET search_path TO {schema}")
    return conn


def table_names(conn, schema=TEST_SCHEMA):
    rows = conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = %s", (schema,)
    ).fetchall()
    return {r["tablename"] for r in rows}


def columns(conn, table, schema=TEST_SCHEMA):
    rows = conn.execute(
        "SELECT column_name, is_nullable FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, table),
    ).fetchall()
    return {r["column_name"]: r["is_nullable"] for r in rows}


def pk_columns(conn, table, schema=TEST_SCHEMA):
    rows = conn.execute(
        "SELECT kcu.column_name FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema "
        "WHERE tc.table_schema = %s AND tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY' "
        "ORDER BY kcu.ordinal_position",
        (schema, table),
    ).fetchall()
    return [r["column_name"] for r in rows]


def seed_user(conn, user_id=1, username="default"):
    conn.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, '') "
        "ON CONFLICT (id) DO NOTHING",
        (user_id, username),
    )


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    """Create a clean 'test' schema once per test session and migrate it."""
    admin = psycopg.connect(app_module.DATABASE_URL, autocommit=True)
    admin.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
    admin.execute(f"CREATE SCHEMA {TEST_SCHEMA}")
    admin.close()

    conn = connect()
    run_migrations(conn)
    conn.close()


@pytest.fixture()
def test_db():
    """Wipe all rows in the test schema and point the app at it for one test."""
    conn = connect()
    conn.execute("TRUNCATE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE")
    conn.commit()
    conn.close()

    flask_app.config['DB_SCHEMA'] = TEST_SCHEMA
    yield
    flask_app.config['DB_SCHEMA'] = 'public'


@pytest.fixture()
def client(test_db):
    """Flask test client wired to the isolated test schema, pre-authenticated as user 1.

    Deliberately not opened via `with flask_app.test_client() as c:` — that
    form preserves the request context after each response, which corrupts
    Werkzeug's context stack when two such clients (see `other_client`) make
    interleaved requests within the same test.
    """
    conn = connect()
    conn.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (1, 'default', '') "
        "ON CONFLICT (id) DO NOTHING"
    )
    conn.commit()
    conn.close()

    flask_app.config["TESTING"] = True
    c = flask_app.test_client()
    with c.session_transaction() as sess:
        sess['user_id'] = 1
    yield c


@pytest.fixture()
def other_client(test_db):
    """A second authenticated client (user 2) sharing the same test schema as `client`."""
    conn = connect()
    conn.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (2, 'user2', '') "
        "ON CONFLICT (id) DO NOTHING"
    )
    conn.commit()
    conn.close()

    flask_app.config["TESTING"] = True
    c = flask_app.test_client()
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