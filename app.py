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
        CREATE TABLE IF NOT EXISTS weights (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    UNIQUE NOT NULL,
            weight_lbs  REAL    NOT NULL,
            weight_kg   REAL    NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value_lbs  REAL NOT NULL,
            value_kg   REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("index.html")


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

    overwrite  = data.get("overwrite", False)
    weight_kg  = round(weight_lbs / 2.2046, 1)

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM weights WHERE date = ?", (entry_date,)
        ).fetchone()

        if existing and not overwrite:
            return jsonify({"conflict": True, "date": entry_date})

        if existing:
            conn.execute(
                "UPDATE weights SET weight_lbs = ?, weight_kg = ? WHERE date = ?",
                (weight_lbs, weight_kg, entry_date),
            )
        else:
            conn.execute(
                "INSERT INTO weights (date, weight_lbs, weight_kg) VALUES (?, ?, ?)",
                (entry_date, weight_lbs, weight_kg),
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
                "SELECT date, weight_lbs, weight_kg FROM weights ORDER BY date"
            ).fetchall()
        else:
            if   range_param == "7d":  days = 7
            elif range_param == "30d": days = 30
            elif range_param == "90d": days = 90
            elif range_param == "1y":  days = 365
            else:                      days = min(custom_days or 30, 1095)

            start = (date.today() - timedelta(days=days - 1)).isoformat()
            rows = conn.execute(
                "SELECT date, weight_lbs, weight_kg FROM weights WHERE date >= ? ORDER BY date",
                (start,),
            ).fetchall()

        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/latest-weight")
def latest_weight():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights ORDER BY date DESC LIMIT 1"
        ).fetchone()
        oldest = conn.execute("SELECT MIN(date) as d FROM weights").fetchone()["d"]
        if row:
            return jsonify({"weight_lbs": row["weight_lbs"], "weight_kg": row["weight_kg"], "oldest_date": oldest})
        return jsonify({})
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>", methods=["DELETE"])
def delete_weight(entry_date):
    conn = get_db()
    try:
        cursor = conn.execute("DELETE FROM weights WHERE date = ?", (entry_date,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "No entry found for that date"}), 404
        row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights ORDER BY date DESC LIMIT 1"
        ).fetchone()
        latest = {"weight_lbs": row["weight_lbs"], "weight_kg": row["weight_kg"]} if row else {}
        return jsonify({"success": True, "latest": latest})
    finally:
        conn.close()


@app.route("/api/settings")
def get_settings():
    conn = get_db()
    try:
        rows = conn.execute("SELECT key, value_lbs, value_kg FROM settings").fetchall()
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
            "SELECT key FROM settings WHERE key = ?", (key,)
        ).fetchone()

        if existing and not overwrite:
            return jsonify({"conflict": True, "key": key})

        if existing:
            conn.execute(
                "UPDATE settings SET value_lbs = ?, value_kg = ? WHERE key = ?",
                (value_lbs, value_kg, key),
            )
        else:
            conn.execute(
                "INSERT INTO settings (key, value_lbs, value_kg) VALUES (?, ?, ?)",
                (key, value_lbs, value_kg),
            )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
