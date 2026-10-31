"""Fill one sandbox account with realistic mock data, through the app's own API.

Usage (from the project folder):
    python tools/sandbox/seed_mock_data.py               # the OWNER_EMAIL account
    python tools/sandbox/seed_mock_data.py --user-id 2   # a specific account

It replaces that account's data, and refuses to run unless APP_ENV=sandbox. To undo it,
reset the Neon dev branch from its parent (see "Database sandbox" in the README).
"""
import argparse
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
TABLES = ("weights", "workouts", "workout_day_notes", "settings", "preferences")
HISTORY_DAYS = 120
STEADY_DAYS = 21                 # the last 3 weeks have no gaps, so the streak looks good

WEIGH_IN_NOTES = {
    9: "Weekend BBQ, felt bloated", 23: "Slept badly", 38: "New deadlift PR!",
    51: "Travel, hotel scale", 64: "Cheat day", 80: "Back on track", 97: "Sore from leg day",
    110: "Feeling lighter",
}
# (type label, MET, typical minutes)
WORKOUTS = [
    ("Running (6.0 mph)", 9.8, 30), ("Cycling (14.0 mph)", 8.0, 45), ("HIIT", 9.5, 25),
    ("Basketball", 6.5, 60), ("Yoga", 2.5, 40), ("Rowing Machine (moderate)", 7.0, 30),
    ("Hiking", 6.0, 90), ("Pickleball", 4.1, 60), ("Kettlebell Training", 9.8, 20),
]
DAY_NOTES = ["Leg day + cardio", "Long hike with friends", "Double session", "Felt strong", "Quick one before work"]


def refuse_unless_sandbox(env=os.environ):
    """Stop before touching any database unless this copy is marked as the sandbox."""
    if env.get("APP_ENV") != "sandbox" or env.get("VERCEL"):
        sys.exit("Refusing to run: this only works locally with APP_ENV=sandbox in .env.")


def plan_weigh_ins(today, days=HISTORY_DAYS, seed=189):
    """[{date, weight_lbs, notes?}] ending yesterday: today is left for you to log."""
    rng = random.Random(seed)
    start = today - timedelta(days=days)
    weight, rows = 231.4, []
    for n in range(days):
        weight += -0.22 if not 55 <= n <= 66 else 0.02      # a plateau in the middle
        steady = n >= days - STEADY_DAYS
        if not steady and (rng.random() < 0.15 or 40 <= n <= 42):   # missed days, and a 3-day gap
            continue
        row = {"date": (start + timedelta(days=n)).isoformat(), "weight_lbs": round(weight + rng.uniform(-1.2, 1.2), 1)}
        if n in WEIGH_IN_NOTES:
            row["notes"] = WEIGH_IN_NOTES[n]
        rows.append(row)
    return rows


def plan_workouts(today, days=HISTORY_DAYS, seed=189):
    """([workout, ...], [day note, ...]) ending yesterday."""
    rng = random.Random(seed + 1)
    start = today - timedelta(days=days)
    workouts, notes = [], []
    for n in range(days):
        if rng.random() > 0.55:
            continue
        day = (start + timedelta(days=n)).isoformat()
        for _ in range(2 if rng.random() < 0.12 else 1):
            label, met, minutes = rng.choice(WORKOUTS)
            minutes = max(10, minutes + rng.choice([-10, -5, 0, 5, 10]))
            kg = (231.4 - 0.2 * n) / 2.2046
            workouts.append({"date": day, "type": label, "duration_min": minutes,
                             "kcal": round(met * kg * minutes / 60), "note": ""})
        if rng.random() < 0.08:
            notes.append({"date": day, "note": rng.choice(DAY_NOTES)})
    return workouts, notes


def fill_account(client, today=None, days=HISTORY_DAYS):
    """Post the mock data through the API with a signed-in test client. Returns row counts."""
    today = today or date.today()

    def post(path, body):
        res = client.post(path, json=body)
        if res.status_code >= 400:
            raise RuntimeError(f"{path} failed with {res.status_code}: {res.get_data(as_text=True)}")

    post("/api/setting", {"key": "starting_weight", "value_lbs": 232.0})
    post("/api/setting", {"key": "goal_weight", "value_lbs": 189.0})
    post("/api/preference", {"key": "fight_name", "value": "The Comeback Kid"})
    post("/api/preference", {"key": "fight_goal_mode", "value": "lean"})

    weigh_ins = plan_weigh_ins(today, days)
    workouts, notes = plan_workouts(today, days)
    for row in weigh_ins:
        post("/api/weight", row)
    for row in workouts:
        post("/api/workout", row)
    for row in notes:
        post("/api/workout-day-note", row)
    return {"weigh_ins": len(weigh_ins), "workouts": len(workouts), "day_notes": len(notes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user-id", type=int, help="account to fill (default: the OWNER_EMAIL account)")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    refuse_unless_sandbox()

    sys.path.insert(0, str(ROOT))
    from app import app, get_db            # only imported once we know this is the sandbox

    conn = get_db()
    try:
        if args.user_id:
            row = conn.execute("SELECT id FROM users WHERE id = %s", (args.user_id,)).fetchone()
        else:
            row = conn.execute("SELECT id FROM users WHERE lower(email) = lower(%s)",
                               (os.environ.get("OWNER_EMAIL", ""),)).fetchone()
        if not row:
            sys.exit("No matching account in the sandbox: sign in once locally, or pass --user-id.")
        user_id = row["id"]
        for table in TABLES:
            conn.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
    counts = fill_account(client)
    print(f"Sandbox account {user_id} filled: {counts['weigh_ins']} weigh-ins, {counts['workouts']} workouts, "
          f"{counts['day_notes']} day notes. Start 232 lbs, goal 189 lbs. Today is left for you to log.")


if __name__ == "__main__":
    main()
