"""Baseline schema for Postgres: users (Google OAuth identity), weights
(nullable weight columns + notes, for note-only days), settings and
preferences (composite user_id+key primary keys), workouts, and
workout_day_notes.
"""
VERSION = 1


def up(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL DEFAULT '',
            google_sub    TEXT,
            email         TEXT,
            name          TEXT,
            picture       TEXT
        )
    ''')
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub "
        "ON users(google_sub) WHERE google_sub IS NOT NULL"
    )

    conn.execute('''
        CREATE TABLE IF NOT EXISTS weights (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            date        TEXT NOT NULL,
            weight_lbs  REAL,
            weight_kg   REAL,
            notes       TEXT NOT NULL DEFAULT '',
            UNIQUE(user_id, date)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            user_id   INTEGER NOT NULL REFERENCES users(id),
            key       TEXT NOT NULL,
            value_lbs REAL NOT NULL,
            value_kg  REAL NOT NULL,
            PRIMARY KEY (user_id, key)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            user_id INTEGER NOT NULL REFERENCES users(id),
            key     TEXT NOT NULL,
            value   TEXT NOT NULL,
            PRIMARY KEY (user_id, key)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER NOT NULL REFERENCES users(id),
            date         TEXT NOT NULL,
            type         TEXT NOT NULL,
            duration_min INTEGER NOT NULL,
            kcal         INTEGER NOT NULL,
            note         TEXT NOT NULL DEFAULT ''
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS workout_day_notes (
            user_id INTEGER NOT NULL REFERENCES users(id),
            date    TEXT NOT NULL,
            note    TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (user_id, date)
        )
    ''')
