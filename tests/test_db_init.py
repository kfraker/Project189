"""Database schema and initialisation tests."""
import sqlite3
import app as app_module


def test_init_db_creates_weights_table(test_db):
    conn = sqlite3.connect(test_db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "weights" in tables


def test_init_db_creates_settings_table(test_db):
    conn = sqlite3.connect(test_db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "settings" in tables


def test_weights_table_has_correct_columns(test_db):
    conn = sqlite3.connect(test_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(weights)").fetchall()}
    conn.close()
    assert {"id", "date", "weight_lbs", "weight_kg"} <= cols


def test_settings_table_has_correct_columns(test_db):
    conn = sqlite3.connect(test_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(settings)").fetchall()}
    conn.close()
    assert {"key", "value_lbs", "value_kg"} <= cols


def test_weights_date_is_unique(test_db):
    conn = sqlite3.connect(test_db)
    # Insert the same date twice — should raise IntegrityError
    conn.execute("INSERT INTO weights (date, weight_lbs, weight_kg) VALUES ('2026-01-01', 200.0, 90.7)")
    conn.commit()
    raised = False
    try:
        conn.execute("INSERT INTO weights (date, weight_lbs, weight_kg) VALUES ('2026-01-01', 205.0, 93.0)")
        conn.commit()
    except sqlite3.IntegrityError:
        raised = True
    conn.close()
    assert raised, "Duplicate date should violate UNIQUE constraint"


def test_settings_key_is_primary_key(test_db):
    conn = sqlite3.connect(test_db)
    conn.execute("INSERT INTO settings (key, value_lbs, value_kg) VALUES ('start', 220.0, 99.8)")
    conn.commit()
    raised = False
    try:
        conn.execute("INSERT INTO settings (key, value_lbs, value_kg) VALUES ('start', 215.0, 97.5)")
        conn.commit()
    except sqlite3.IntegrityError:
        raised = True
    conn.close()
    assert raised, "Duplicate key should violate PRIMARY KEY constraint"


def test_init_db_is_idempotent(test_db):
    """Calling init_db() a second time must not raise or corrupt data."""
    app_module.init_db()  # already called once via fixture; call again
    conn = sqlite3.connect(test_db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "weights" in tables
    assert "settings" in tables
