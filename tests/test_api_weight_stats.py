"""GET /api/weight/stats — rolling 7-day change, 7-day average, day streak."""
from datetime import date, timedelta
from tests.conftest import seed_weight


def _date_offset(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# ── Empty database ────────────────────────────────────────────────────────────

def test_empty_db_returns_nulls_and_zero_streak(client):
    body = client.get("/api/weight/stats").get_json()
    assert body["week_change"] is None
    assert body["avg_7d"] is None
    assert body["streak"] == 0


# ── week_change: rolling 7-day delta, not ISO calendar week ────────────────────

def test_single_entry_in_window_gives_no_change(client):
    """A lone entry has nothing to diff against."""
    seed_weight(client, _date_offset(0), 200.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["week_change"] is None


def test_week_change_is_latest_minus_earliest_in_window(client):
    seed_weight(client, _date_offset(6), 200.0)
    seed_weight(client, _date_offset(0), 195.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["week_change"] == -5.0


def test_week_change_can_be_positive(client):
    seed_weight(client, _date_offset(6), 180.0)
    seed_weight(client, _date_offset(0), 184.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["week_change"] == 4.0


def test_week_change_zero_when_flat(client):
    seed_weight(client, _date_offset(6), 190.0)
    seed_weight(client, _date_offset(0), 190.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["week_change"] == 0.0


def test_entries_older_than_seven_days_excluded(client):
    """Regression: previously this stat reset on Monday (ISO week); it must
    now be a true rolling 7-day window regardless of what day it is."""
    seed_weight(client, _date_offset(10), 210.0)  # outside window
    seed_weight(client, _date_offset(6), 200.0)   # oldest in window
    seed_weight(client, _date_offset(0), 195.0)   # latest in window
    body = client.get("/api/weight/stats").get_json()
    assert body["week_change"] == -5.0


def test_entry_exactly_eight_days_ago_excluded(client):
    seed_weight(client, _date_offset(8), 300.0)
    seed_weight(client, _date_offset(0), 195.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["week_change"] is None


# ── avg_7d ───────────────────────────────────────────────────────────────────

def test_avg_7d_averages_only_entries_in_window(client):
    seed_weight(client, _date_offset(10), 999.0)  # excluded
    seed_weight(client, _date_offset(6), 200.0)
    seed_weight(client, _date_offset(0), 190.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["avg_7d"] == 195.0


def test_avg_7d_none_when_no_entries_in_window(client):
    seed_weight(client, _date_offset(30), 200.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["avg_7d"] is None


# ── streak ───────────────────────────────────────────────────────────────────

def test_streak_zero_when_today_not_logged(client):
    seed_weight(client, _date_offset(1), 200.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["streak"] == 0


def test_streak_counts_consecutive_days_ending_today(client):
    for d in range(3):
        seed_weight(client, _date_offset(d), 200.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["streak"] == 3


def test_streak_stops_at_gap(client):
    seed_weight(client, _date_offset(0), 200.0)
    seed_weight(client, _date_offset(1), 199.0)
    # gap at day 2
    seed_weight(client, _date_offset(3), 198.0)
    body = client.get("/api/weight/stats").get_json()
    assert body["streak"] == 2
