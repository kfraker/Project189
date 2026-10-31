"""GET /api/home-stats — Home header: active streak, weekly kcal burn, 7-day weight trend."""
from datetime import date, timedelta
from tests.conftest import seed_weight


def _date_offset(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


TODAY = _date_offset(0)


def seed_workout(client, entry_date, kcal=300):
    return client.post(
        "/api/workout",
        json={"date": entry_date, "type": "Running (6 mph)", "duration_min": 30,
              "kcal": kcal, "note": ""},
        content_type="application/json",
    )


def _stats(client):
    r = client.get("/api/home-stats")
    assert r.status_code == 200
    return r.get_json()


# ── Empty account ────────────────────────────────────────────────────────────

def test_empty_account_has_zero_stats(client):
    assert _stats(client) == {"streak": 0, "kcal_week": 0, "trend_lbs": None, "trend_kg": None}


# ── Active streak ────────────────────────────────────────────────────────────

def test_weigh_in_today_starts_streak(client):
    seed_weight(client, TODAY, 200.0)
    assert _stats(client)["streak"] == 1


def test_consecutive_days_extend_streak(client):
    for i in range(3):
        seed_weight(client, _date_offset(i), 200.0)
    assert _stats(client)["streak"] == 3


def test_streak_survives_until_today_is_logged(client):
    """Nothing logged yet today still counts yesterday's run of days."""
    seed_weight(client, _date_offset(1), 200.0)
    seed_weight(client, _date_offset(2), 200.0)
    assert _stats(client)["streak"] == 2


def test_gap_breaks_streak(client):
    seed_weight(client, TODAY, 200.0)
    seed_weight(client, _date_offset(2), 200.0)
    assert _stats(client)["streak"] == 1


def test_streak_older_than_yesterday_is_zero(client):
    seed_weight(client, _date_offset(2), 200.0)
    assert _stats(client)["streak"] == 0


def test_workouts_count_toward_streak(client):
    seed_workout(client, TODAY)
    seed_workout(client, _date_offset(1))
    assert _stats(client)["streak"] == 2


def test_weigh_ins_and_workouts_chain_together(client):
    seed_weight(client, TODAY, 200.0)
    seed_workout(client, _date_offset(1))
    seed_weight(client, _date_offset(2), 200.0)
    assert _stats(client)["streak"] == 3


def test_note_only_day_does_not_count(client):
    """A day whose weight was cleared but whose note was kept isn't an active day."""
    client.post("/api/weight", json={"date": TODAY, "weight_lbs": 200.0, "notes": "rest day"},
                content_type="application/json")
    client.delete(f"/api/weight/{TODAY}/weight")
    assert _stats(client)["streak"] == 0


# ── Weekly kcal burn (today + previous 6 days) ───────────────────────────────

def test_kcal_week_sums_last_seven_days(client):
    seed_workout(client, TODAY, kcal=300)
    seed_workout(client, _date_offset(6), kcal=200)
    assert _stats(client)["kcal_week"] == 500


def test_kcal_week_excludes_older_workouts(client):
    seed_workout(client, _date_offset(7), kcal=400)
    assert _stats(client)["kcal_week"] == 0


# ── 7-day weight trend (avg of last 7 days minus avg of the 7 before) ────────

def test_trend_compares_weekly_averages(client):
    seed_weight(client, _date_offset(1), 198.0)
    seed_weight(client, _date_offset(2), 196.0)   # last-7 avg 197
    seed_weight(client, _date_offset(8), 200.0)
    seed_weight(client, _date_offset(9), 202.0)   # prior-7 avg 201
    stats = _stats(client)
    assert stats["trend_lbs"] == -4.0
    assert stats["trend_kg"] is not None and stats["trend_kg"] < 0


def test_trend_is_none_without_prior_week(client):
    seed_weight(client, TODAY, 200.0)
    stats = _stats(client)
    assert stats["trend_lbs"] is None
    assert stats["trend_kg"] is None


def test_trend_is_none_without_recent_week(client):
    seed_weight(client, _date_offset(10), 200.0)
    assert _stats(client)["trend_lbs"] is None


# ── Isolation & auth ─────────────────────────────────────────────────────────

def test_other_users_data_not_counted(client, other_client):
    seed_weight(other_client, TODAY, 200.0)
    seed_workout(other_client, TODAY, kcal=500)
    stats = _stats(client)
    assert stats["streak"] == 0
    assert stats["kcal_week"] == 0


def test_requires_login(unauthenticated_client):
    r = unauthenticated_client.get("/api/home-stats")
    assert r.status_code == 401
