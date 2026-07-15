"""Baseline schema: the six core tables plus the seeded default user."""
VERSION = 1


def up(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL DEFAULT ''
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS weights (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
            date        TEXT    NOT NULL,
            weight_lbs  REAL,
            weight_kg   REAL,
            UNIQUE(user_id, date)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            user_id   INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
            key       TEXT    NOT NULL,
            value_lbs REAL    NOT NULL,
            value_kg  REAL    NOT NULL,
            PRIMARY KEY (user_id, key)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
            key     TEXT    NOT NULL,
            value   TEXT    NOT NULL,
            PRIMARY KEY (user_id, key)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
            date         TEXT    NOT NULL,
            type         TEXT    NOT NULL,
            duration_min INTEGER NOT NULL,
            kcal         INTEGER NOT NULL,
            note         TEXT    NOT NULL DEFAULT ''
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS workout_day_notes (
            user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
            date    TEXT    NOT NULL,
            note    TEXT    NOT NULL DEFAULT '',
            PRIMARY KEY (user_id, date)
        )
    ''')

    conn.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (1, 'default', '')"
    )
