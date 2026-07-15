"""Backfills user_id on pre-multi-user tables, adds weights.notes, and makes
weight_lbs/weight_kg nullable so note-only entries can be stored without a
weigh-in.
"""
VERSION = 2


def up(conn):
    for table in ('weights', 'settings'):
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if 'user_id' not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"
            )

    cols = {row[1] for row in conn.execute("PRAGMA table_info(weights)")}
    if 'notes' not in cols:
        conn.execute("ALTER TABLE weights ADD COLUMN notes TEXT NOT NULL DEFAULT ''")

    pragma = conn.execute("PRAGMA table_info(weights)").fetchall()
    wt_col = next((r for r in pragma if r['name'] == 'weight_lbs'), None)
    if wt_col and wt_col['notnull'] == 1:
        conn.execute("DROP TABLE IF EXISTS weights_v1")
        conn.execute("ALTER TABLE weights RENAME TO weights_v1")
        conn.execute('''
            CREATE TABLE weights (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
                date        TEXT    NOT NULL,
                weight_lbs  REAL,
                weight_kg   REAL,
                notes       TEXT    NOT NULL DEFAULT '',
                UNIQUE(user_id, date)
            )
        ''')
        conn.execute("""
            INSERT INTO weights (id, user_id, date, weight_lbs, weight_kg, notes)
            SELECT id, user_id, date, weight_lbs, weight_kg, COALESCE(notes, '')
            FROM weights_v1
        """)
        conn.execute("DROP TABLE weights_v1")
