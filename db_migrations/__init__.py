"""Lightweight, forward-only SQLite migration runner.

Each sibling module named `m####_description.py` exposes a module-level
`VERSION` (int) and an `up(conn)` function. run_migrations() applies any
migration whose VERSION isn't yet recorded in the `schema_migrations`
table, in VERSION order, committing after each one.
"""
import importlib
import pkgutil
import sqlite3
from datetime import datetime, timezone


def _discover():
    modules = []
    for _, name, _ in pkgutil.iter_modules(__path__):
        if name.startswith('m') and name[1:5].isdigit():
            modules.append(importlib.import_module(f'{__name__}.{name}'))
    return modules


def run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    ''')
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}

    for mod in sorted(_discover(), key=lambda m: m.VERSION):
        if mod.VERSION in applied:
            continue
        mod.up(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (mod.VERSION, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
