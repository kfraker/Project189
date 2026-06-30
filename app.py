from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import date, timedelta

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
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
    data       = request.get_json()
    weight_lbs = float(data["weight_lbs"])
    weight_kg  = round(weight_lbs / 2.2046, 1)
    entry_date = data["date"]          # ISO string from client, e.g. "2026-06-29"
    overwrite  = data.get("overwrite", False)

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
            else:                      days = custom_days or 30

            start = (date.today() - timedelta(days=days - 1)).isoformat()
            rows = conn.execute(
                "SELECT date, weight_lbs, weight_kg FROM weights WHERE date >= ? ORDER BY date",
                (start,),
            ).fetchall()

        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>", methods=["DELETE"])
def delete_weight(entry_date):
    conn = get_db()
    try:
        conn.execute("DELETE FROM weights WHERE date = ?", (entry_date,))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/setting", methods=["POST"])
def save_setting():
    data      = request.get_json()
    key       = data["key"]
    value_lbs = float(data["value_lbs"])
    value_kg  = round(value_lbs / 2.2046, 1)
    overwrite = data.get("overwrite", False)

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
