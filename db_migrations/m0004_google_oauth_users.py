"""Adds Google OAuth identity columns to the existing users table so users
can be looked up by their Google account instead of the unused
username/password_hash columns.
"""
VERSION = 4


def up(conn):
    cols = {r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if 'google_sub' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub "
            "ON users(google_sub) WHERE google_sub IS NOT NULL"
        )
    if 'email' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if 'name' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN name TEXT")
    if 'picture' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN picture TEXT")
