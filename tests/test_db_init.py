"""Database schema and initialisation tests."""
import psycopg

import app as app_module
from tests.conftest import connect, table_names, columns, seed_user


def test_init_db_creates_weights_table(test_db):
    conn = connect()
    tables = table_names(conn)
    conn.close()
    assert "weights" in tables


def test_init_db_creates_settings_table(test_db):
    conn = connect()
    tables = table_names(conn)
    conn.close()
    assert "settings" in tables


def test_weights_table_has_correct_columns(test_db):
    conn = connect()
    cols = set(columns(conn, "weights"))
    conn.close()
    assert {"id", "date", "weight_lbs", "weight_kg"} <= cols


def test_settings_table_has_correct_columns(test_db):
    conn = connect()
    cols = set(columns(conn, "settings"))
    conn.close()
    assert {"key", "value_lbs", "value_kg"} <= cols


def test_weights_date_is_unique(test_db):
    conn = connect()
    seed_user(conn)
    conn.commit()
    # Insert the same (user_id, date) twice — should raise a unique violation
    conn.execute("INSERT INTO weights (user_id, date, weight_lbs, weight_kg) VALUES (1, '2026-01-01', 200.0, 90.7)")
    conn.commit()
    raised = False
    try:
        conn.execute("INSERT INTO weights (user_id, date, weight_lbs, weight_kg) VALUES (1, '2026-01-01', 205.0, 93.0)")
        conn.commit()
    except psycopg.errors.UniqueViolation:
        raised = True
        conn.rollback()
    conn.close()
    assert raised, "Duplicate date should violate UNIQUE constraint"


def test_settings_key_is_primary_key(test_db):
    conn = connect()
    seed_user(conn)
    conn.commit()
    conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (1, 'start', 220.0, 99.8)")
    conn.commit()
    raised = False
    try:
        conn.execute("INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (1, 'start', 215.0, 97.5)")
        conn.commit()
    except psycopg.errors.UniqueViolation:
        raised = True
        conn.rollback()
    conn.close()
    assert raised, "Duplicate key should violate PRIMARY KEY constraint"


def test_init_db_is_idempotent(test_db):
    """Calling init_db() a second time must not raise or corrupt data."""
    app_module.init_db()  # already called once via fixture; call again
    conn = connect()
    tables = table_names(conn)
    conn.close()
    assert "weights" in tables
    assert "settings" in tables
