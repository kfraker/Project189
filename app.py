from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import re
from datetime import date, timedelta

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights.db')
app.config['DB_PATH'] = DB_PATH

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _valid_date(s: str) -> bool:
    if not isinstance(s, str) or not _DATE_RE.match(s):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def get_db():
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

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

    # Seed default user
    conn.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (1, 'default', '')"
    )

    # Migrate existing tables that predate user_id
    _migrate(conn)

    conn.commit()
    conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns to pre-existing tables that were created without them."""
    for table in ('weights', 'settings'):
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if 'user_id' not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"
            )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(weights)")}
    if 'notes' not in cols:
        conn.execute("ALTER TABLE weights ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
    # Make weight columns nullable so note-only entries (no weigh-in) can be stored
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


init_db()

# Current user — hardcoded until auth is added
_USER_ID = 1


@app.route("/")
def home():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = ?", (_USER_ID,)
        ).fetchall()
        prefs = {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()
    return render_template("index.html", prefs=prefs)


@app.route("/workouts")
def workouts_page():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = ?", (_USER_ID,)
        ).fetchall()
        prefs = {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()
    return render_template("workouts.html", prefs=prefs)


@app.route("/weights")
def weights_page():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = ?", (_USER_ID,)
        ).fetchall()
        prefs = {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()
    return render_template("weights.html", prefs=prefs)


@app.route("/api/weight", methods=["POST"])
def save_weight():
    data = request.get_json(silent=True) or {}

    if "weight_lbs" not in data or "date" not in data:
        return jsonify({"error": "Missing required fields: weight_lbs, date"}), 400

    try:
        weight_lbs = float(data["weight_lbs"])
    except (TypeError, ValueError):
        return jsonify({"error": "weight_lbs must be a number"}), 400

    if weight_lbs <= 0:
        return jsonify({"error": "weight_lbs must be greater than zero"}), 400

    entry_date = data["date"]
    if not _valid_date(entry_date):
        return jsonify({"error": "date must be a valid ISO date (YYYY-MM-DD)"}), 400

    overwrite = data.get("overwrite", False)
    notes     = str(data.get("notes", "")).strip()[:500]
    weight_kg = round(weight_lbs / 2.2046, 1)

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id, weight_lbs FROM weights WHERE user_id = ? AND date = ?",
            (_USER_ID, entry_date),
        ).fetchone()

        note_only = existing and existing['weight_lbs'] is None
        if existing and not note_only and not overwrite:
            return jsonify({"conflict": True, "date": entry_date})

        if existing:
            conn.execute(
                "UPDATE weights SET weight_lbs = ?, weight_kg = ? WHERE user_id = ? AND date = ?",
                (weight_lbs, weight_kg, _USER_ID, entry_date),
            )
        else:
            conn.execute(
                "INSERT INTO weights (user_id, date, weight_lbs, weight_kg, notes) VALUES (?, ?, ?, ?, ?)",
                (_USER_ID, entry_date, weight_lbs, weight_kg, notes),
            )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/weights")
def get_weights():
    range_param = request.args.get("range", "all")
    custom_days = request.args.get("days", type=int)

    conn = get_db()
    try:
        if range_param == "all":
            rows = conn.execute(
                "SELECT date, weight_lbs, weight_kg, notes FROM weights WHERE user_id = ? ORDER BY date",
                (_USER_ID,),
            ).fetchall()
        else:
            if   range_param == "7d":  days = 7
            elif range_param == "30d": days = 30
            elif range_param == "90d": days = 90
            elif range_param == "1y":  days = 365
            else:                      days = min(custom_days or 30, 1095)

            latest = conn.execute(
                "SELECT MAX(date) as d FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL",
                (_USER_ID,),
            ).fetchone()["d"]
            anchor = date.fromisoformat(latest) if latest else date.today()
            start = (anchor - timedelta(days=days - 1)).isoformat()
            rows = conn.execute(
                "SELECT date, weight_lbs, weight_kg, notes FROM weights "
                "WHERE user_id = ? AND date >= ? ORDER BY date",
                (_USER_ID, start),
            ).fetchall()

        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/latest-weight")
def latest_weight():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL ORDER BY date DESC LIMIT 1",
            (_USER_ID,),
        ).fetchone()
        oldest = conn.execute(
            "SELECT MIN(date) as d FROM weights WHERE user_id = ?", (_USER_ID,)
        ).fetchone()["d"]
        if row:
            return jsonify({
                "weight_lbs": row["weight_lbs"],
                "weight_kg":  row["weight_kg"],
                "oldest_date": oldest,
            })
        return jsonify({})
    finally:
        conn.close()


@app.route("/api/weight/stats")
def weight_stats():
    conn = get_db()
    try:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()  # Monday
        week_end   = today.isoformat()

        logged_this_week = conn.execute(
            "SELECT COUNT(*) as c FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL AND date >= ? AND date <= ?",
            (_USER_ID, week_start, week_end),
        ).fetchone()["c"]

        seven_days_ago = (today - timedelta(days=6)).isoformat()
        avg_row = conn.execute(
            "SELECT AVG(weight_lbs) as a FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL AND date >= ? AND date <= ?",
            (_USER_ID, seven_days_ago, today.isoformat()),
        ).fetchone()
        avg_7d = round(avg_row["a"], 1) if avg_row["a"] is not None else None

        # Streak: count consecutive days backwards from today with weight logged
        logged_dates = set(
            r["date"] for r in conn.execute(
                "SELECT date FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL ORDER BY date DESC",
                (_USER_ID,),
            ).fetchall()
        )
        streak = 0
        check = today
        while check.isoformat() in logged_dates:
            streak += 1
            check -= timedelta(days=1)

        return jsonify({"logged_this_week": logged_this_week, "avg_7d": avg_7d, "streak": streak})
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>", methods=["DELETE"])
def delete_weight(entry_date):
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM weights WHERE user_id = ? AND date = ?", (_USER_ID, entry_date)
        )
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "No entry found for that date"}), 404
        row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = ? ORDER BY date DESC LIMIT 1",
            (_USER_ID,),
        ).fetchone()
        latest = {"weight_lbs": row["weight_lbs"], "weight_kg": row["weight_kg"]} if row else {}
        return jsonify({"success": True, "latest": latest})
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>/weight", methods=["DELETE"])
def clear_weight(entry_date):
    if not _valid_date(entry_date):
        return jsonify({"error": "date must be a valid ISO date (YYYY-MM-DD)"}), 400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT notes FROM weights WHERE user_id = ? AND date = ?",
            (_USER_ID, entry_date),
        ).fetchone()
        if not row:
            return jsonify({"error": "No entry found for that date"}), 404
        if row["notes"]:
            conn.execute(
                "UPDATE weights SET weight_lbs = NULL, weight_kg = NULL WHERE user_id = ? AND date = ?",
                (_USER_ID, entry_date),
            )
        else:
            conn.execute(
                "DELETE FROM weights WHERE user_id = ? AND date = ?",
                (_USER_ID, entry_date),
            )
        conn.commit()
        latest_row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL ORDER BY date DESC LIMIT 1",
            (_USER_ID,),
        ).fetchone()
        latest = {"weight_lbs": latest_row["weight_lbs"], "weight_kg": latest_row["weight_kg"]} if latest_row else {}
        return jsonify({"success": True, "latest": latest})
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>/note", methods=["PATCH"])
def save_note(entry_date):
    if not _valid_date(entry_date):
        return jsonify({"error": "date must be a valid ISO date (YYYY-MM-DD)"}), 400
    data  = request.get_json(silent=True) or {}
    notes = str(data.get("notes", "")).strip()[:500]
    conn  = get_db()
    try:
        cursor = conn.execute(
            "UPDATE weights SET notes = ? WHERE user_id = ? AND date = ?",
            (notes, _USER_ID, entry_date),
        )
        conn.commit()
        if cursor.rowcount == 0:
            if notes:
                conn.execute(
                    "INSERT INTO weights (user_id, date, weight_lbs, weight_kg, notes) "
                    "VALUES (?, ?, NULL, NULL, ?)",
                    (_USER_ID, entry_date, notes),
                )
                conn.commit()
            return jsonify({"success": True})
        if not notes:
            conn.execute(
                "DELETE FROM weights WHERE user_id = ? AND date = ? AND weight_lbs IS NULL",
                (_USER_ID, entry_date),
            )
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/settings")
def get_settings():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value_lbs, value_kg FROM settings WHERE user_id = ?", (_USER_ID,)
        ).fetchall()
        return jsonify({r["key"]: {"value_lbs": r["value_lbs"], "value_kg": r["value_kg"]} for r in rows})
    finally:
        conn.close()


@app.route("/api/setting", methods=["POST"])
def save_setting():
    data = request.get_json(silent=True) or {}

    if "key" not in data or "value_lbs" not in data:
        return jsonify({"error": "Missing required fields: key, value_lbs"}), 400

    try:
        value_lbs = float(data["value_lbs"])
    except (TypeError, ValueError):
        return jsonify({"error": "value_lbs must be a number"}), 400

    if value_lbs <= 0:
        return jsonify({"error": "value_lbs must be greater than zero"}), 400

    key       = data["key"]
    overwrite = data.get("overwrite", False)
    value_kg  = round(value_lbs / 2.2046, 1)

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT key FROM settings WHERE user_id = ? AND key = ?", (_USER_ID, key)
        ).fetchone()

        if existing and not overwrite:
            return jsonify({"conflict": True, "key": key})

        if existing:
            conn.execute(
                "UPDATE settings SET value_lbs = ?, value_kg = ? WHERE user_id = ? AND key = ?",
                (value_lbs, value_kg, _USER_ID, key),
            )
        else:
            conn.execute(
                "INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (?, ?, ?, ?)",
                (_USER_ID, key, value_lbs, value_kg),
            )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/preferences")
def get_preferences():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = ?", (_USER_ID,)
        ).fetchall()
        return jsonify({r["key"]: r["value"] for r in rows})
    finally:
        conn.close()


@app.route("/api/preference", methods=["POST"])
def save_preference():
    data = request.get_json(silent=True) or {}

    if "key" not in data or "value" not in data:
        return jsonify({"error": "Missing required fields: key, value"}), 400

    key   = str(data["key"]).strip()
    value = str(data["value"])

    if not key:
        return jsonify({"error": "key must not be empty"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO preferences (user_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value",
            (_USER_ID, key, value),
        )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/home-stats")
def home_stats():
    conn = get_db()
    try:
        today = date.today()

        # Active streak: union of weight-logged and workout dates
        weight_dates = {r["date"] for r in conn.execute(
            "SELECT DISTINCT date FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL",
            (_USER_ID,)
        ).fetchall()}
        workout_dates = {r["date"] for r in conn.execute(
            "SELECT DISTINCT date FROM workouts WHERE user_id = ?",
            (_USER_ID,)
        ).fetchall()}
        active_dates = weight_dates | workout_dates
        streak = 0
        d = today
        if d.isoformat() not in active_dates:
            d -= timedelta(days=1)
        while d.isoformat() in active_dates:
            streak += 1
            d -= timedelta(days=1)

        # Kcal this week (last 7 calendar days)
        week_ago = (today - timedelta(days=6)).isoformat()
        kcal_week = conn.execute(
            "SELECT COALESCE(SUM(kcal), 0) as total FROM workouts WHERE user_id = ? AND date >= ?",
            (_USER_ID, week_ago)
        ).fetchone()["total"]

        # 7-day weight trend (avg last 7 days vs avg prior 7 days)
        d7  = (today - timedelta(days=7)).isoformat()
        d14 = (today - timedelta(days=14)).isoformat()
        last7 = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL AND date > ?",
            (_USER_ID, d7)
        ).fetchall()
        prev7 = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = ? AND weight_lbs IS NOT NULL AND date > ? AND date <= ?",
            (_USER_ID, d14, d7)
        ).fetchall()
        trend_lbs = trend_kg = None
        if last7 and prev7:
            trend_lbs = round(sum(r["weight_lbs"] for r in last7) / len(last7)
                              - sum(r["weight_lbs"] for r in prev7) / len(prev7), 1)
            trend_kg  = round(sum(r["weight_kg"]  for r in last7) / len(last7)
                              - sum(r["weight_kg"]  for r in prev7) / len(prev7), 1)

        return jsonify({"streak": streak, "kcal_week": kcal_week,
                        "trend_lbs": trend_lbs, "trend_kg": trend_kg})
    finally:
        conn.close()


@app.route("/api/workouts")
def get_workouts():
    date_filter = request.args.get("date", "").strip()
    conn = get_db()
    try:
        if date_filter and _valid_date(date_filter):
            rows = conn.execute(
                "SELECT id, date, type, duration_min, kcal, note FROM workouts "
                "WHERE user_id = ? AND date = ? ORDER BY id DESC",
                (_USER_ID, date_filter)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, date, type, duration_min, kcal, note FROM workouts "
                "WHERE user_id = ? ORDER BY date DESC, id DESC",
                (_USER_ID,)
            ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/workout", methods=["POST"])
def save_workout():
    data = request.get_json(silent=True) or {}
    date_val     = data.get("date", "")
    workout_type = str(data.get("type", "")).strip()[:100]
    duration     = data.get("duration_min")
    kcal         = data.get("kcal")
    note         = str(data.get("note", "")).strip()

    if not _valid_date(date_val):
        return jsonify({"error": "Invalid date"}), 400
    if not workout_type:
        return jsonify({"error": "Invalid workout type"}), 400
    if not isinstance(duration, int) or duration < 1 or duration > 600:
        return jsonify({"error": "Invalid duration"}), 400
    if not isinstance(kcal, int) or kcal < 0:
        return jsonify({"error": "Invalid kcal"}), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO workouts (user_id, date, type, duration_min, kcal, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (_USER_ID, date_val, workout_type, duration, kcal, note)
        )
        conn.commit()
        return jsonify({"success": True, "id": cur.lastrowid})
    finally:
        conn.close()


@app.route("/api/workout/<int:workout_id>", methods=["DELETE"])
def delete_workout(workout_id):
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM workouts WHERE id = ? AND user_id = ?",
            (workout_id, _USER_ID)
        )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/workout-day-note")
def get_workout_day_note():
    date_str = request.args.get("date", "").strip()
    if not date_str or not _valid_date(date_str):
        return jsonify({"error": "invalid date"}), 400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT note FROM workout_day_notes WHERE user_id = ? AND date = ?",
            (_USER_ID, date_str)
        ).fetchone()
        return jsonify({"note": row["note"] if row else ""})
    finally:
        conn.close()


@app.route("/api/workout-day-note", methods=["POST"])
def save_workout_day_note():
    data = request.get_json(silent=True) or {}
    date_str = data.get("date", "").strip()
    note = str(data.get("note", "")).strip()[:500]
    if not date_str or not _valid_date(date_str):
        return jsonify({"error": "invalid date"}), 400
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO workout_day_notes (user_id, date, note) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, date) DO UPDATE SET note = excluded.note",
            (_USER_ID, date_str, note)
        )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/workout-day-notes")
def get_workout_day_notes():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, note FROM workout_day_notes WHERE user_id = ? AND note != ''",
            (_USER_ID,)
        ).fetchall()
        return jsonify({r["date"]: r["note"] for r in rows})
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
