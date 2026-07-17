from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg
from psycopg.rows import dict_row
import os
import re
from datetime import date, timedelta
from functools import wraps
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

from db_migrations import run_migrations

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']
DATABASE_URL = os.environ['DATABASE_URL']

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
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    schema = app.config.get('DB_SCHEMA', 'public')
    conn.execute(f"SET search_path TO {schema}")
    return conn


def init_db():
    conn = get_db()
    run_migrations(conn)
    conn.close()


init_db()


def current_user_id():
    return session['user_id']


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"error": "authentication required"}), 401
            return redirect(url_for('login_page', next=request.path))
        return view(*args, **kwargs)
    return wrapped


oauth = OAuth(app)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.environ['GOOGLE_CLIENT_ID'],
    client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
    client_kwargs={'scope': 'openid email profile'},
)
ALLOWED_EMAILS = {e.strip().lower() for e in os.environ.get('ALLOWED_EMAILS', '').split(',') if e.strip()}


@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html')


@app.route('/auth/google')
def auth_google():
    return oauth.google.authorize_redirect(url_for('auth_google_callback', _external=True))


@app.route('/auth/google/callback')
def auth_google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token['userinfo']
    sub, email = userinfo['sub'], (userinfo.get('email') or '').lower()
    name, picture = userinfo.get('name'), userinfo.get('picture')

    if email not in ALLOWED_EMAILS:
        return render_template('access_denied.html', owner_email=os.environ.get('OWNER_EMAIL', '')), 403

    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE google_sub = %s", (sub,)).fetchone()
        if row:
            user_id = row['id']
            conn.execute(
                "UPDATE users SET email=%s, name=%s, picture=%s WHERE id=%s",
                (email, name, picture, user_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, google_sub, email, name, picture) "
                "VALUES (%s, '', %s, %s, %s, %s) RETURNING id",
                (email or sub, sub, email, name, picture),
            )
            user_id = cur.fetchone()['id']
        conn.commit()
    finally:
        conn.close()

    session['user_id'] = user_id
    session.permanent = True
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route("/")
def home():
    if 'user_id' not in session:
        return render_template("login.html")
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = %s", (current_user_id(),)
        ).fetchall()
        prefs = {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()
    return render_template("index.html", prefs=prefs)


@app.route("/workouts")
@login_required
def workouts_page():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = %s", (current_user_id(),)
        ).fetchall()
        prefs = {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()
    return render_template("workouts.html", prefs=prefs)


@app.route("/weights")
@login_required
def weights_page():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = %s", (current_user_id(),)
        ).fetchall()
        prefs = {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()
    return render_template("weights.html", prefs=prefs)


@app.route("/api/weight", methods=["POST"])
@login_required
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
            "SELECT id, weight_lbs FROM weights WHERE user_id = %s AND date = %s",
            (current_user_id(), entry_date),
        ).fetchone()

        note_only = existing and existing['weight_lbs'] is None
        if existing and not note_only and not overwrite:
            return jsonify({"conflict": True, "date": entry_date})

        if existing:
            conn.execute(
                "UPDATE weights SET weight_lbs = %s, weight_kg = %s WHERE user_id = %s AND date = %s",
                (weight_lbs, weight_kg, current_user_id(), entry_date),
            )
        else:
            conn.execute(
                "INSERT INTO weights (user_id, date, weight_lbs, weight_kg, notes) VALUES (%s, %s, %s, %s, %s)",
                (current_user_id(), entry_date, weight_lbs, weight_kg, notes),
            )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/weights")
@login_required
def get_weights():
    range_param = request.args.get("range", "all")
    custom_days = request.args.get("days", type=int)

    conn = get_db()
    try:
        if range_param == "all":
            rows = conn.execute(
                "SELECT date, weight_lbs, weight_kg, notes FROM weights WHERE user_id = %s ORDER BY date",
                (current_user_id(),),
            ).fetchall()
        else:
            if   range_param == "7d":  days = 7
            elif range_param == "30d": days = 30
            elif range_param == "90d": days = 90
            elif range_param == "1y":  days = 365
            else:                      days = min(custom_days or 30, 1095)

            latest = conn.execute(
                "SELECT MAX(date) as d FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL",
                (current_user_id(),),
            ).fetchone()["d"]
            anchor = date.fromisoformat(latest) if latest else date.today()
            start = (anchor - timedelta(days=days - 1)).isoformat()
            rows = conn.execute(
                "SELECT date, weight_lbs, weight_kg, notes FROM weights "
                "WHERE user_id = %s AND date >= %s ORDER BY date",
                (current_user_id(), start),
            ).fetchall()

        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/latest-weight")
@login_required
def latest_weight():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL ORDER BY date DESC LIMIT 1",
            (current_user_id(),),
        ).fetchone()
        oldest = conn.execute(
            "SELECT MIN(date) as d FROM weights WHERE user_id = %s", (current_user_id(),)
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
@login_required
def weight_stats():
    conn = get_db()
    try:
        today = date.today()

        seven_days_ago = (today - timedelta(days=6)).isoformat()
        week_rows = conn.execute(
            "SELECT weight_lbs FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL AND date >= %s AND date <= %s ORDER BY date ASC",
            (current_user_id(), seven_days_ago, today.isoformat()),
        ).fetchall()
        week_change = round(week_rows[-1]["weight_lbs"] - week_rows[0]["weight_lbs"], 1) if len(week_rows) >= 2 else None

        avg_row = conn.execute(
            "SELECT AVG(weight_lbs) as a FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL AND date >= %s AND date <= %s",
            (current_user_id(), seven_days_ago, today.isoformat()),
        ).fetchone()
        avg_7d = round(avg_row["a"], 1) if avg_row["a"] is not None else None

        # Streak: count consecutive days backwards from today with weight logged
        logged_dates = set(
            r["date"] for r in conn.execute(
                "SELECT date FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL ORDER BY date DESC",
                (current_user_id(),),
            ).fetchall()
        )
        streak = 0
        check = today
        while check.isoformat() in logged_dates:
            streak += 1
            check -= timedelta(days=1)

        return jsonify({"week_change": week_change, "avg_7d": avg_7d, "streak": streak})
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>", methods=["DELETE"])
@login_required
def delete_weight(entry_date):
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM weights WHERE user_id = %s AND date = %s", (current_user_id(), entry_date)
        )
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "No entry found for that date"}), 404
        row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = %s ORDER BY date DESC LIMIT 1",
            (current_user_id(),),
        ).fetchone()
        latest = {"weight_lbs": row["weight_lbs"], "weight_kg": row["weight_kg"]} if row else {}
        return jsonify({"success": True, "latest": latest})
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>/weight", methods=["DELETE"])
@login_required
def clear_weight(entry_date):
    if not _valid_date(entry_date):
        return jsonify({"error": "date must be a valid ISO date (YYYY-MM-DD)"}), 400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT notes FROM weights WHERE user_id = %s AND date = %s",
            (current_user_id(), entry_date),
        ).fetchone()
        if not row:
            return jsonify({"error": "No entry found for that date"}), 404
        if row["notes"]:
            conn.execute(
                "UPDATE weights SET weight_lbs = NULL, weight_kg = NULL WHERE user_id = %s AND date = %s",
                (current_user_id(), entry_date),
            )
        else:
            conn.execute(
                "DELETE FROM weights WHERE user_id = %s AND date = %s",
                (current_user_id(), entry_date),
            )
        conn.commit()
        latest_row = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL ORDER BY date DESC LIMIT 1",
            (current_user_id(),),
        ).fetchone()
        latest = {"weight_lbs": latest_row["weight_lbs"], "weight_kg": latest_row["weight_kg"]} if latest_row else {}
        return jsonify({"success": True, "latest": latest})
    finally:
        conn.close()


@app.route("/api/weight/<string:entry_date>/note", methods=["PATCH"])
@login_required
def save_note(entry_date):
    if not _valid_date(entry_date):
        return jsonify({"error": "date must be a valid ISO date (YYYY-MM-DD)"}), 400
    data  = request.get_json(silent=True) or {}
    notes = str(data.get("notes", "")).strip()[:500]
    conn  = get_db()
    try:
        cursor = conn.execute(
            "UPDATE weights SET notes = %s WHERE user_id = %s AND date = %s",
            (notes, current_user_id(), entry_date),
        )
        conn.commit()
        if cursor.rowcount == 0:
            if notes:
                conn.execute(
                    "INSERT INTO weights (user_id, date, weight_lbs, weight_kg, notes) "
                    "VALUES (%s, %s, NULL, NULL, %s)",
                    (current_user_id(), entry_date, notes),
                )
                conn.commit()
            return jsonify({"success": True})
        if not notes:
            conn.execute(
                "DELETE FROM weights WHERE user_id = %s AND date = %s AND weight_lbs IS NULL",
                (current_user_id(), entry_date),
            )
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/settings")
@login_required
def get_settings():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value_lbs, value_kg FROM settings WHERE user_id = %s", (current_user_id(),)
        ).fetchall()
        return jsonify({r["key"]: {"value_lbs": r["value_lbs"], "value_kg": r["value_kg"]} for r in rows})
    finally:
        conn.close()


@app.route("/api/setting", methods=["POST"])
@login_required
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
            "SELECT key FROM settings WHERE user_id = %s AND key = %s", (current_user_id(), key)
        ).fetchone()

        if existing and not overwrite:
            return jsonify({"conflict": True, "key": key})

        if existing:
            conn.execute(
                "UPDATE settings SET value_lbs = %s, value_kg = %s WHERE user_id = %s AND key = %s",
                (value_lbs, value_kg, current_user_id(), key),
            )
        else:
            conn.execute(
                "INSERT INTO settings (user_id, key, value_lbs, value_kg) VALUES (%s, %s, %s, %s)",
                (current_user_id(), key, value_lbs, value_kg),
            )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/preferences")
@login_required
def get_preferences():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = %s", (current_user_id(),)
        ).fetchall()
        return jsonify({r["key"]: r["value"] for r in rows})
    finally:
        conn.close()


@app.route("/api/preference", methods=["POST"])
@login_required
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
            "INSERT INTO preferences (user_id, key, value) VALUES (%s, %s, %s) "
            "ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value",
            (current_user_id(), key, value),
        )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/home-stats")
@login_required
def home_stats():
    conn = get_db()
    try:
        today = date.today()

        # Active streak: union of weight-logged and workout dates
        weight_dates = {r["date"] for r in conn.execute(
            "SELECT DISTINCT date FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL",
            (current_user_id(),)
        ).fetchall()}
        workout_dates = {r["date"] for r in conn.execute(
            "SELECT DISTINCT date FROM workouts WHERE user_id = %s",
            (current_user_id(),)
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
            "SELECT COALESCE(SUM(kcal), 0) as total FROM workouts WHERE user_id = %s AND date >= %s",
            (current_user_id(), week_ago)
        ).fetchone()["total"]

        # 7-day weight trend (avg last 7 days vs avg prior 7 days)
        d7  = (today - timedelta(days=7)).isoformat()
        d14 = (today - timedelta(days=14)).isoformat()
        last7 = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL AND date > %s",
            (current_user_id(), d7)
        ).fetchall()
        prev7 = conn.execute(
            "SELECT weight_lbs, weight_kg FROM weights WHERE user_id = %s AND weight_lbs IS NOT NULL AND date > %s AND date <= %s",
            (current_user_id(), d14, d7)
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
@login_required
def get_workouts():
    date_filter = request.args.get("date", "").strip()
    conn = get_db()
    try:
        if date_filter and _valid_date(date_filter):
            rows = conn.execute(
                "SELECT id, date, type, duration_min, kcal, note FROM workouts "
                "WHERE user_id = %s AND date = %s ORDER BY id DESC",
                (current_user_id(), date_filter)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, date, type, duration_min, kcal, note FROM workouts "
                "WHERE user_id = %s ORDER BY date DESC, id DESC",
                (current_user_id(),)
            ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/workout", methods=["POST"])
@login_required
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
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (current_user_id(), date_val, workout_type, duration, kcal, note)
        )
        new_id = cur.fetchone()["id"]
        conn.commit()
        return jsonify({"success": True, "id": new_id})
    finally:
        conn.close()


@app.route("/api/workout/<int:workout_id>", methods=["DELETE"])
@login_required
def delete_workout(workout_id):
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM workouts WHERE id = %s AND user_id = %s",
            (workout_id, current_user_id())
        )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/workout-day-note")
@login_required
def get_workout_day_note():
    date_str = request.args.get("date", "").strip()
    if not date_str or not _valid_date(date_str):
        return jsonify({"error": "invalid date"}), 400
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT note FROM workout_day_notes WHERE user_id = %s AND date = %s",
            (current_user_id(), date_str)
        ).fetchone()
        return jsonify({"note": row["note"] if row else ""})
    finally:
        conn.close()


@app.route("/api/workout-day-note", methods=["POST"])
@login_required
def save_workout_day_note():
    data = request.get_json(silent=True) or {}
    date_str = data.get("date", "").strip()
    note = str(data.get("note", "")).strip()[:500]
    if not date_str or not _valid_date(date_str):
        return jsonify({"error": "invalid date"}), 400
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO workout_day_notes (user_id, date, note) VALUES (%s, %s, %s) "
            "ON CONFLICT (user_id, date) DO UPDATE SET note = EXCLUDED.note",
            (current_user_id(), date_str, note)
        )
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route("/api/workout-day-notes")
@login_required
def get_workout_day_notes():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, note FROM workout_day_notes WHERE user_id = %s AND note != ''",
            (current_user_id(),)
        ).fetchall()
        return jsonify({r["date"]: r["note"] for r in rows})
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
