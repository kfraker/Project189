"""Lightweight, forward-only Postgres migration runner.

Each sibling module named `m####_description.py` exposes a module-level
`VERSION` (int) and an `up(conn)` function. run_migrations() applies any
migration whose VERSION isn't yet recorded in the `schema_migrations`
table, in VERSION order, committing after each one. Runs against whatever
schema is active on the connection's search_path.
"""
import importlib
import pkgutil
from datetime import datetime, timezone

import psycopg


def _discover():
    modules = []
    for _, name, _ in pkgutil.iter_modules(__path__):
        if name.startswith('m') and name[1:5].isdigit():
            modules.append(importlib.import_module(f'{__name__}.{name}'))
    return modules


def run_migrations(conn: psycopg.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    ''')
    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}

    for mod in sorted(_discover(), key=lambda m: m.VERSION):
        if mod.VERSION in applied:
            continue
        mod.up(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, %s)",
            (mod.VERSION, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
