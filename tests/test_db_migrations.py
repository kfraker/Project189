"""Migration runner tests — db_migrations/."""
import sqlite3
import app as app_module
from db_migrations import run_migrations


def test_fresh_db_records_all_migration_versions(test_db):
    conn = sqlite3.connect(test_db)
    versions = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    conn.close()
    assert versions == {1, 2, 3, 4}


def test_running_twice_is_idempotent(test_db):
    conn = sqlite3.connect(test_db)
    before_versions = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    before_weights = conn.execute("SELECT COUNT(*) FROM weights").fetchone()[0]
    before_settings = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]

    run_migrations(conn)  # second run against the same connection

    after_versions = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    after_weights = conn.execute("SELECT COUNT(*) FROM weights").fetchone()[0]
    after_settings = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    conn.close()

    assert after_versions == before_versions
    assert after_weights == before_weights
    assert after_settings == before_settings


def test_init_db_twice_is_idempotent(test_db):
    """Calling the public init_db() entrypoint twice must not raise."""
    app_module.init_db()  # already called once via fixture; call again
    conn = sqlite3.connect(test_db)
    versions = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    conn.close()
    assert versions == {1, 2, 3, 4}


def test_weight_columns_are_nullable(test_db):
    conn = sqlite3.connect(test_db)
    pragma = conn.execute("PRAGMA table_info(weights)").fetchall()
    conn.close()
    wt_col = next(r for r in pragma if r[1] == "weight_lbs")
    assert wt_col[3] == 0  # notnull flag


def test_weights_has_notes_column(test_db):
    conn = sqlite3.connect(test_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(weights)").fetchall()}
    conn.close()
    assert "notes" in cols


def test_note_only_row_can_be_inserted_without_weight(test_db):
    """Regression guard for the nullable-weight migration's whole purpose."""
    conn = sqlite3.connect(test_db)
    conn.execute("INSERT INTO weights (date, notes) VALUES ('2026-01-01', 'no weigh-in today')")
    conn.commit()
    row = conn.execute("SELECT weight_lbs, notes FROM weights WHERE date = '2026-01-01'").fetchone()
    conn.close()
    assert row == (None, "no weigh-in today")


def test_settings_pk_is_composite_user_id_and_key(test_db):
    conn = sqlite3.connect(test_db)
    pragma = conn.execute("PRAGMA table_info(settings)").fetchall()
    conn.close()
    pk_cols = [r[1] for r in sorted((row for row in pragma if row[5] > 0), key=lambda r: r[5])]
    assert pk_cols == ["user_id", "key"]


def test_two_users_can_have_the_same_setting_key(test_db):
    """Regression guard: this used to raise IntegrityError before the composite PK fix."""
    conn = sqlite3.connect(test_db)
    conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (1, 'start', 200.0, 90.7)")
    conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (2, 'start', 180.0, 81.6)")
    conn.commit()
    rows = conn.execute("SELECT user_id, value_lbs FROM settings WHERE key = 'start' ORDER BY user_id").fetchall()
    conn.close()
    assert rows == [(1, 200.0), (2, 180.0)]


def test_settings_data_preserved_across_rebuild(test_db):
    conn = sqlite3.connect(test_db)
    conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (1, 'goal', 175.0, 79.4)")
    conn.commit()
    run_migrations(conn)  # re-run; m0003 must not re-fire or touch existing rows
    row = conn.execute("SELECT value_lbs, value_kg FROM settings WHERE key = 'goal'").fetchone()
    conn.close()
    assert row == (175.0, 79.4)
