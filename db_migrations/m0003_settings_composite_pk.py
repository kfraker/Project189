"""Rebuilds settings with a composite PRIMARY KEY (user_id, key) so multiple
users can each have their own 'start'/'goal' settings without colliding.
The original table only ever got a bolted-on user_id column via ALTER TABLE,
which can't change a PRIMARY KEY — this finishes that upgrade properly.
"""
VERSION = 3


def up(conn):
    pk_cols = [r['name'] for r in conn.execute("PRAGMA table_info(settings)").fetchall() if r['pk'] > 0]
    if pk_cols == ['key']:  # only rebuild if still on the old single-column PK
        conn.execute("DROP TABLE IF EXISTS settings_v1")
        conn.execute("ALTER TABLE settings RENAME TO settings_v1")
        conn.execute('''
            CREATE TABLE settings (
                user_id   INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
                key       TEXT    NOT NULL,
                value_lbs REAL    NOT NULL,
                value_kg  REAL    NOT NULL,
                PRIMARY KEY (user_id, key)
            )
        ''')
        conn.execute("INSERT INTO settings SELECT user_id, key, value_lbs, value_kg FROM settings_v1")
        conn.execute("DROP TABLE settings_v1")
