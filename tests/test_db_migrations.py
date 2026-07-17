"""Migration runner tests — db_migrations/."""
import app as app_module
from db_migrations import run_migrations
from tests.conftest import connect, columns, pk_columns, seed_user


def test_fresh_db_records_migration_version(test_db):
    conn = connect()
    versions = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    conn.close()
    assert versions == {1}


def test_running_twice_is_idempotent(test_db):
    conn = connect()
    before_versions = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    before_weights = conn.execute("SELECT COUNT(*) AS c FROM weights").fetchone()["c"]
    before_settings = conn.execute("SELECT COUNT(*) AS c FROM settings").fetchone()["c"]

    run_migrations(conn)  # second run against the same connection

    after_versions = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    after_weights = conn.execute("SELECT COUNT(*) AS c FROM weights").fetchone()["c"]
    after_settings = conn.execute("SELECT COUNT(*) AS c FROM settings").fetchone()["c"]
    conn.close()

    assert after_versions == before_versions
    assert after_weights == before_weights
    assert after_settings == before_settings


def test_init_db_twice_is_idempotent(test_db):
    """Calling the public init_db() entrypoint twice must not raise."""
    app_module.init_db()
    conn = connect()
    versions = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    conn.close()
    assert versions == {1}


def test_weight_columns_are_nullable(test_db):
    conn = connect()
    cols = columns(conn, "weights")
    conn.close()
    assert cols["weight_lbs"] == "YES"


def test_weights_has_notes_column(test_db):
    conn = connect()
    cols = columns(conn, "weights")
    conn.close()
    assert "notes" in cols


def test_note_only_row_can_be_inserted_without_weight(test_db):
    """Regression guard for the nullable-weight schema's whole purpose."""
    conn = connect()
    seed_user(conn)
    conn.execute(
        "INSERT INTO weights (user_id, date, notes) VALUES (1, '2026-01-01', 'no weigh-in today')"
    )
    conn.commit()
    row = conn.execute("SELECT weight_lbs, notes FROM weights WHERE date = '2026-01-01'").fetchone()
    conn.close()
    assert row["weight_lbs"] is None
    assert row["notes"] == "no weigh-in today"


def test_settings_pk_is_composite_user_id_and_key(test_db):
    conn = connect()
    pk_cols = pk_columns(conn, "settings")
    conn.close()
    assert pk_cols == ["user_id", "key"]


def test_two_users_can_have_the_same_setting_key(test_db):
    """Regression guard: composite PK lets each user have their own 'start' key."""
    conn = connect()
    seed_user(conn, 1, "u1")
    seed_user(conn, 2, "u2")
    conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (1, 'start', 200.0, 90.7)")
    conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (2, 'start', 180.0, 81.6)")
    conn.commit()
    rows = conn.execute("SELECT user_id, value_lbs FROM settings WHERE key = 'start' ORDER BY user_id").fetchall()
    conn.close()
    assert [(r["user_id"], r["value_lbs"]) for r in rows] == [(1, 200.0), (2, 180.0)]


def test_settings_data_preserved_across_rerun(test_db):
    conn = connect()
    seed_user(conn)
    conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (1, 'goal', 175.0, 79.4)")
    conn.commit()
    run_migrations(conn)  # re-run; must not touch existing rows
    row = conn.execute("SELECT value_lbs, value_kg FROM settings WHERE key = 'goal'").fetchone()
    conn.close()
    assert (row["value_lbs"], row["value_kg"]) == (175.0, 79.4)
